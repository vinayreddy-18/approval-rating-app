from flask import Blueprint, render_template, request, jsonify
from .database import get_db_connection

main = Blueprint('main', __name__)


def calculate_percentages(cur, politician_id):
    cur.execute(
        """
        SELECT vote_type, COUNT(*) AS count
        FROM votes
        WHERE politician_id = %s
        GROUP BY vote_type
        """,
        (politician_id,)
    )

    results = cur.fetchall()

    total = sum(row['count'] for row in results) if results else 0

    stats = {
        "approve": 0,
        "neutral": 0,
        "disapprove": 0
    }

    for row in results:
        vote_type = row['vote_type']
        count = row['count']

        if total > 0:
            stats[vote_type] = round((count / total) * 100)

    return stats



def build_comparison(politicians_with_stats):
    """Build the current leader and lead difference from approval statistics."""
    if not politicians_with_stats:
        return {
            'ratings': [],
            'leader_name': 'N/A',
            'lead_display': '+0',
        }

    sorted_by_approval = sorted(politicians_with_stats, key=lambda item: item['approval'], reverse=True)
    leader = sorted_by_approval[0]
    second_approval = sorted_by_approval[1]['approval'] if len(sorted_by_approval) > 1 else 0
    lead = leader['approval'] - second_approval

    return {
        'ratings': [
            {'name': p['name'], 'approval': p['approval']} for p in politicians_with_stats
        ],
        'leader_name': leader['name'],
        'lead_display': f"{lead:+d}",
    }


def get_platform_stats(cur):
    """Return overall platform vote metrics and last vote timestamp."""
    cur.execute(
        """
        SELECT COUNT(*) AS total_votes, MAX(timestamp) AS last_vote_time
        FROM votes
        """
    )
    summary = cur.fetchone()
    total_votes = summary['total_votes'] or 0
    last_vote_time = summary['last_vote_time'] or 'No votes yet'

    cur.execute(
        """
        SELECT p.name, COUNT(v.id) AS vote_count
        FROM politicians p
        LEFT JOIN votes v ON p.id = v.politician_id
        GROUP BY p.id
        ORDER BY p.id
        """
    )
    politicians = cur.fetchall()
    vote_counts = [
        {'name': row['name'], 'vote_count': row['vote_count']} for row in politicians
    ]

    return {
        'total_votes_cast': total_votes,
        'last_vote_time': last_vote_time,
        'vote_counts': vote_counts,
    }


def get_all_politician_stats(cur):
    """Get all politician stats including approval percentages and vote counts."""
    cur.execute('SELECT id, name, party FROM politicians ORDER BY id')
    politicians = cur.fetchall()

    return [
        {
            'id': politician['id'],
            'name': politician['name'],
            'party': politician['party'],
            **calculate_percentages(cur, politician['id'])
        }
        for politician in politicians
    ]


@main.route('/')
def home():
    """Fetch all politicians from the database and render the homepage."""
    conn = get_db_connection()
    cur = conn.cursor()

    uid = (request.args.get('uid') or '').strip()
    user_id = None

    if uid:
        # User vote lookup: resolve the Firebase UID to a local account before checking prior votes.
        cur.execute('SELECT id FROM users WHERE firebase_uid = %s', (uid,))
        user_row = cur.fetchone()
        if user_row is not None:
            user_id = user_row['id']

    cur.execute('SELECT id, name, party FROM politicians ORDER BY id')
    politicians = cur.fetchall()

    politicians_with_stats = []
    for politician in politicians:
        stats = calculate_percentages(cur, politician['id'])
        user_vote = None

        if user_id is not None:
            # User vote lookup: check whether this signed-in user already voted for this politician.
            cur.execute(
                'SELECT vote_type FROM votes WHERE user_id = %s AND politician_id = %s',
                (user_id, politician['id'])
            )
            vote_row = cur.fetchone()
            if vote_row is not None:
                user_vote = vote_row['vote_type']

        politicians_with_stats.append({
            'id': politician['id'],
            'name': politician['name'],
            'party': politician['party'],
            'approval': stats['approval'],
            'neutral': stats['neutral'],
            'disapproval': stats['disapproval'],
            'approve_count': stats['approve_count'],
            'neutral_count': stats['neutral_count'],
            'disapprove_count': stats['disapprove_count'],
            'total_votes': stats['total_votes'],
            'net_approval': stats['net_approval'],
            'user_vote': user_vote,
        })

    top_comparison = build_comparison(politicians_with_stats)
    platform_stats = get_platform_stats(cur)

    conn.close()

    if request.args.get('format') == 'json' or 'application/json' in request.headers.get('Accept', ''):
        return jsonify({
            'politicians': politicians_with_stats,
            'comparison': top_comparison,
            'platform_stats': platform_stats,
        })

    return render_template(
        'index.html',
        politicians=politicians_with_stats,
        top_comparison=top_comparison,
        platform_stats=platform_stats,
    )


@main.route("/results")
def get_results():
    """Return vote counts and percentages for each politician."""
    conn = get_db_connection()
    cur = conn.cursor()

    results = get_all_politician_stats(cur)
    top_comparison = build_comparison(results)
    platform_stats = get_platform_stats(cur)

    conn.close()
    return jsonify({
        'politicians': results,
        'comparison': top_comparison,
        'platform_stats': platform_stats,
    })


@main.route('/login', methods=['POST'])
def login():
    """Create or look up a user from the Firebase UID."""
    data = request.get_json() or {}
    uid = data.get('uid')
    email = data.get('email')

    if not uid:
        return jsonify({'error': 'Firebase uid is required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    # User lookup: resolve the Firebase UID to a local database user record.
    cur.execute('SELECT id FROM users WHERE firebase_uid = %s', (uid,))
    user_row = cur.fetchone()

    if user_row is None:
        cur.execute('INSERT INTO users (firebase_uid, email) VALUES (%s, %s)', (uid, email))
        conn.commit()
        user_id = cur.lastrowid
    else:
        user_id = user_row['id']
        cur.execute('UPDATE users SET email = %s WHERE id = %s', (email, user_id))
        conn.commit()

    conn.close()
    return jsonify({'success': True, 'user_id': user_id})


# Allowed vote types
ALLOWED_VOTES = {'approve', 'neutral', 'disapprove'}


@main.route('/vote', methods=['POST'])
def vote():
    """Record or update a vote for a politician tied to a logged-in user."""
    data = request.get_json() or {}
    politician_id = data.get('politician_id')
    vote_type = data.get('vote_type')
    user_uid = data.get('user_uid')

    if not isinstance(politician_id, int) or vote_type not in ALLOWED_VOTES:
        return jsonify({'error': 'Invalid payload'}), 400

    if not isinstance(user_uid, str) or not user_uid.strip():
        return jsonify({'error': 'Authentication required'}), 401

    conn = get_db_connection()
    cur = conn.cursor()

    # Ensure the politician exists
    cur.execute('SELECT id FROM politicians WHERE id = %s', (politician_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': 'Politician not found'}), 404

    # User lookup: resolve the authenticated Google account to a local user id.
    cur.execute('SELECT id FROM users WHERE firebase_uid = %s', (user_uid,))
    user_row = cur.fetchone()
    if user_row is None:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    user_id = user_row['id']

    # Vote update logic: replace a prior vote for the same user and politician instead of creating duplicates.
    cur.execute(
        'SELECT id, vote_type FROM votes WHERE user_id = %s AND politician_id = %s',
        (user_id, politician_id)
    )
    existing_vote = cur.fetchone()

    if existing_vote is None:
        cur.execute(
            'INSERT INTO votes (user_id, politician_id, vote_type) VALUES (%s, %s, %s)',
            (user_id, politician_id, vote_type)
        )
        vote_id = cur.lastrowid
        message = 'Vote recorded'
    else:
        cur.execute(
            'UPDATE votes SET vote_type = %s WHERE user_id = %s AND politician_id = %s',
            (vote_type, user_id, politician_id)
        )
        vote_id = existing_vote['id']
        message = 'Vote updated'

    conn.commit()

    results = get_all_politician_stats(cur)
    platform_stats = get_platform_stats(cur)
    comparison = build_comparison(results)
    stats = next((item for item in results if item['id'] == politician_id), None)
    conn.close()

    response = {
        'success': True,
        'message': message,
        'vote_id': vote_id,
        'comparison': comparison,
        'platform_stats': platform_stats,
        'user_vote': vote_type,
    }

    if stats:
        response.update({
            'approval': stats['approval'],
            'neutral': stats['neutral'],
            'disapproval': stats['disapproval'],
            'approve_count': stats['approve_count'],
            'neutral_count': stats['neutral_count'],
            'disapprove_count': stats['disapprove_count'],
            'total_votes': stats['total_votes'],
            'net_approval': stats['net_approval'],
        })

    return jsonify(response), 201
