from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request

from ..database import get_db_connection

approval_bp = Blueprint('approval', __name__)


ALLOWED_VOTES = {'approve', 'neutral', 'disapprove'}


def calculate_percentages(cur, politician_id):
    cur.execute(
        """
        SELECT vote_type, COUNT(*) AS count
        FROM votes
        WHERE politician_id = ?
        GROUP BY vote_type
        """,
        (politician_id,),
    )
    vote_rows = cur.fetchall()

    counts = {'approve': 0, 'neutral': 0, 'disapprove': 0}
    for vote_row in vote_rows:
        counts[vote_row['vote_type']] = vote_row['count']

    approve = counts['approve']
    neutral = counts['neutral']
    disapprove = counts['disapprove']
    total_votes = approve + neutral + disapprove

    if total_votes == 0:
        return {
            'approval': 0,
            'neutral': 0,
            'disapproval': 0,
            'approve_count': 0,
            'neutral_count': 0,
            'disapprove_count': 0,
            'total_votes': 0,
            'net_approval': 0,
        }

    approval_percentage = round((approve / total_votes) * 100)
    neutral_percentage = round((neutral / total_votes) * 100)
    disapproval_percentage = round((disapprove / total_votes) * 100)
    net_approval = approval_percentage - disapproval_percentage

    return {
        'approval': approval_percentage,
        'neutral': neutral_percentage,
        'disapproval': disapproval_percentage,
        'approve_count': approve,
        'neutral_count': neutral,
        'disapprove_count': disapprove,
        'total_votes': total_votes,
        'net_approval': net_approval,
    }


def build_comparison(politicians_with_stats):
    if not politicians_with_stats:
        return {'ratings': [], 'leader_name': 'N/A', 'lead_display': '+0'}

    sorted_by_approval = sorted(politicians_with_stats, key=lambda item: item['approval'], reverse=True)
    leader = sorted_by_approval[0]
    second_approval = sorted_by_approval[1]['approval'] if len(sorted_by_approval) > 1 else 0
    lead = leader['approval'] - second_approval

    return {
        'ratings': [
            {'name': p['name'], 'approval': p['approval']} for p in politicians_with_stats
        ],
        'leader_name': leader['name'],
        'lead_display': f'{lead:+d}',
    }


def get_platform_stats(cur):
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


def get_politicians_with_context(cur, uid=None):
    user_id = None
    if uid:
        cur.execute('SELECT id FROM users WHERE firebase_uid = ?', (uid,))
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
            cur.execute(
                'SELECT vote_type FROM votes WHERE user_id = ? AND politician_id = ?',
                (user_id, politician['id']),
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

    return politicians_with_stats, top_comparison, platform_stats


@approval_bp.route('/approval')
def approval_page():
    conn = get_db_connection()
    cur = conn.cursor()

    uid = (request.args.get('uid') or '').strip()
    politicians_with_stats, top_comparison, platform_stats = get_politicians_with_context(cur, uid)
    conn.close()

    if request.args.get('format') == 'json' or 'application/json' in request.headers.get('Accept', ''):
        return jsonify({
            'politicians': politicians_with_stats,
            'comparison': top_comparison,
            'platform_stats': platform_stats,
        })

    user_email = request.args.get('email', '').strip()
    return render_template(
        'approval.html',
        politicians=politicians_with_stats,
        top_comparison=top_comparison,
        platform_stats=platform_stats,
        user_email=user_email,
    )


@approval_bp.route('/results')
def get_results():
    conn = get_db_connection()
    cur = conn.cursor()
    politicians_with_stats, top_comparison, platform_stats = get_politicians_with_context(cur)
    conn.close()

    return jsonify({
        'politicians': politicians_with_stats,
        'comparison': top_comparison,
        'platform_stats': platform_stats,
    })


@approval_bp.route('/vote', methods=['POST'])
def vote():
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

    cur.execute('SELECT id FROM politicians WHERE id = ?', (politician_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': 'Politician not found'}), 404

    cur.execute('SELECT id FROM users WHERE firebase_uid = ?', (user_uid,))
    user_row = cur.fetchone()
    if user_row is None:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    user_id = user_row['id']

    cur.execute(
        'SELECT id, vote_type FROM votes WHERE user_id = ? AND politician_id = ?',
        (user_id, politician_id),
    )
    existing_vote = cur.fetchone()

    if existing_vote is None:
        cur.execute(
            'INSERT INTO votes (user_id, politician_id, vote_type) VALUES (?, ?, ?)',
            (user_id, politician_id, vote_type),
        )
        vote_id = cur.lastrowid
        message = 'Vote recorded'
    else:
        cur.execute(
            'UPDATE votes SET vote_type = ? WHERE user_id = ? AND politician_id = ?',
            (vote_type, user_id, politician_id),
        )
        vote_id = existing_vote['id']
        message = 'Vote updated'

    conn.commit()

    results = get_politicians_with_context(cur, user_uid)[0]
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
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
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
