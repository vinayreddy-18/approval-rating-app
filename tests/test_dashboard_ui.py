import unittest

from app import create_app


class DashboardUiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_landing_and_approval_pages_contain_expected_sections(self):
        landing_response = self.client.get('/')
        self.assertEqual(landing_response.status_code, 200)
        self.assertIn('Political Pulse India', landing_response.get_data(as_text=True))

        approval_response = self.client.get('/approval')
        self.assertEqual(approval_response.status_code, 200)
        self.assertIn("India's Real-Time Political Approval Dashboard", approval_response.get_data(as_text=True))
        self.assertIn("Comparison Snapshot", approval_response.get_data(as_text=True))
        self.assertIn("Platform Statistics", approval_response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
