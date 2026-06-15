import os
import tempfile
import unittest

import app.database as database
from app import create_app


class UserVoteFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_app.db")
        database.DATABASE = self.db_path
        database.init_db()

        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO politicians (name, party) VALUES (?, ?)", ("Test Politician", "Test Party"))
        conn.commit()
        conn.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_login_and_vote_update_for_same_user(self):
        login_response = self.client.post('/login', json={
            'uid': 'firebase-user-1',
            'email': 'user@example.com'
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json['success'])

        first_vote = self.client.post('/vote', json={
            'user_uid': 'firebase-user-1',
            'politician_id': 1,
            'vote_type': 'approve'
        })
        self.assertEqual(first_vote.status_code, 201)
        self.assertEqual(first_vote.json['message'], 'Vote recorded')

        updated_vote = self.client.post('/vote', json={
            'user_uid': 'firebase-user-1',
            'politician_id': 1,
            'vote_type': 'neutral'
        })
        self.assertEqual(updated_vote.status_code, 201)
        self.assertEqual(updated_vote.json['message'], 'Vote updated')
        self.assertEqual(updated_vote.json['neutral_count'], 1)
        self.assertEqual(updated_vote.json['approve_count'], 0)

    def test_approval_route_returns_user_vote_for_logged_in_user(self):
        self.client.post('/login', json={
            'uid': 'firebase-user-1',
            'email': 'user@example.com'
        })
        self.client.post('/vote', json={
            'user_uid': 'firebase-user-1',
            'politician_id': 1,
            'vote_type': 'approve'
        })

        response = self.client.get('/approval?uid=firebase-user-1&format=json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['politicians'][0]['user_vote'], 'approve')

    def test_vote_response_includes_timestamp_and_user_vote(self):
        self.client.post('/login', json={
            'uid': 'firebase-user-1',
            'email': 'user@example.com'
        })

        response = self.client.post('/vote', json={
            'user_uid': 'firebase-user-1',
            'politician_id': 1,
            'vote_type': 'approve'
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['user_vote'], 'approve')
        self.assertIn('timestamp', response.json)
        self.assertTrue(response.json['timestamp'])

    def test_admin_route_requires_admin_email(self):
        response = self.client.get('/admin?email=user@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Access Denied', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
