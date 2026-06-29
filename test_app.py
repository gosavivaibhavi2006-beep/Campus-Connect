import unittest
from app import app, db, User, StudentProfile, Project
from werkzeug.security import generate_password_hash

class CampusConnectTestCase(unittest.TestCase):
    
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.db'
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.app = app.test_client()
        
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            # Setup dummy student user
            hashed = generate_password_hash("student123")
            u = User(username="student1", email="student1@campus.edu", password_hash=hashed, role="student")
            db.session.add(u)
            db.session.commit()
            
            profile = StudentProfile(user_id=u.id, name="Test Student", roll_no="STU-TEST", gpa=9.0, skills="Python,HTML")
            db.session.add(profile)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.rollback()
            db.drop_all()
            db.session.remove()
        import os
        if os.path.exists('test_database.db'):
            try:
                os.remove('test_database.db')
            except Exception:
                pass

    def test_landing_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CAMPUS CONNECT', response.data)

    def test_login_page_renders(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.data)

    def test_chatbot_fallback_reply(self):
        response = self.app.post('/chatbot/ask', json={"message": "invalid_command_here"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"]) > 0)

    def test_chatbot_admission_answer(self):
        response = self.app.post('/chatbot/ask', json={"message": "How does admission work?"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Admission details depend on your institution", data["reply"])

    def test_chatbot_gpa_query_without_session(self):
        response = self.app.post('/chatbot/ask', json={"message": "what is my GPA?"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Grade Point Average", data["reply"])

if __name__ == '__main__':
    unittest.main()
