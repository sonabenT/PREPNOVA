import unittest
import io
from app import app, db, User

class AIPlacementCoachTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # 1. Test Home/Dashboard Route
    def test_dashboard_route(self):
        response = self.client.get('/dashboard')
        # Expecting 200 or 302 if redirecting to login
        self.assertIn(response.status_code, [200, 302])

    # 2. Test User Creation
    def test_user_creation(self):
        with app.app_context():
            user = User(username="testuser", password="password123")
            db.session.add(user)
            db.session.commit()
            
            retrieved = User.query.filter_by(username="testuser").first()
            self.assertIsNotNone(retrieved)

if __name__ == '__main__':
    unittest.main()