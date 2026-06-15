import csv
import io
import os

from flask import Blueprint, Response, redirect, render_template, request

from ..database import get_db_connection

admin_bp = Blueprint('admin', __name__)
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'vinayreddysathi2007@gmail.com')


def _is_admin(email):
    return bool(email) and email.lower() == ADMIN_EMAIL.lower()


@admin_bp.route('/admin')
def admin_dashboard():
    user_email = (request.args.get('email') or '').strip()
    if not _is_admin(user_email):
        return 'Access Denied'

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT id, email, created_at FROM users ORDER BY id')
    users = cur.fetchall()

    cur.execute(
        '''
        SELECT votes.id, users.email AS user_email, politicians.name AS politician_name, votes.vote_type, votes.timestamp
        FROM votes
        JOIN users ON votes.user_id = users.id
        JOIN politicians ON votes.politician_id = politicians.id
        ORDER BY votes.timestamp DESC
        '''
    )
    votes = cur.fetchall()

    cur.execute('SELECT id, name, party FROM politicians ORDER BY id')
    politicians = cur.fetchall()

    conn.close()

    return render_template(
        'admin.html',
        user_email=user_email,
        users=users,
        votes=votes,
        politicians=politicians,
        admin_email=ADMIN_EMAIL,
    )


@admin_bp.route('/admin/delete-vote', methods=['POST'])
def delete_vote():
    user_email = (request.args.get('email') or '').strip()
    if not _is_admin(user_email):
        return 'Access Denied'

    vote_id = request.form.get('vote_id', '').strip()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM votes WHERE id = ?', (vote_id,))
    conn.commit()
    conn.close()

    return redirect(f'/admin?email={user_email}')


@admin_bp.route('/admin/add-politician', methods=['POST'])
def add_politician():
    user_email = (request.args.get('email') or '').strip()
    if not _is_admin(user_email):
        return 'Access Denied'

    name = (request.form.get('name') or '').strip()
    party = (request.form.get('party') or '').strip()

    if not name or not party:
        return redirect(f'/admin?email={user_email}')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO politicians (name, party) VALUES (?, ?)', (name, party))
    conn.commit()
    conn.close()

    return redirect(f'/admin?email={user_email}')


@admin_bp.route('/admin/export')
def export_votes():
    user_email = (request.args.get('email') or '').strip()
    if not _is_admin(user_email):
        return 'Access Denied'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT users.email, politicians.name, votes.vote_type, votes.timestamp
        FROM votes
        JOIN users ON votes.user_id = users.id
        JOIN politicians ON votes.politician_id = politicians.id
        ORDER BY votes.timestamp DESC
        '''
    )
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['user', 'politician', 'vote_type', 'timestamp'])
    for row in rows:
        writer.writerow([row['email'], row['name'], row['vote_type'], row['timestamp']])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=vote_export.csv'
    return response
