from app import app, db, User, StudentProfile, FacultyProfile, Project, Attendance, Event, Announcement
from werkzeug.security import generate_password_hash
from datetime import datetime

def seed_db():
    print("Starting database seeding...")
    with app.app_context():
        # Clear existing tables
        db.drop_all()
        db.create_all()
        
        # 1. Create Admin Users
        admin_pass = generate_password_hash("admin123")
        admin_user = User(
            username="admin",
            email="admin@campusconnect.com",
            password_hash=admin_pass,
            role="admin"
        )
        db.session.add(admin_user)

        vaibhavi_pass = generate_password_hash("vaibhavi123")
        vaibhavi_user = User(
            username="Vaibhavi Gosavi",
            email="vaibhavi@campusconnect.com",
            password_hash=vaibhavi_pass,
            role="admin"
        )
        db.session.add(vaibhavi_user)
        
        # 2. Create Faculty User
        faculty_pass = generate_password_hash("faculty123")
        faculty_user = User(
            username="faculty1",
            email="faculty1@campusconnect.com",
            password_hash=faculty_pass,
            role="faculty"
        )
        db.session.add(faculty_user)
        db.session.commit() # Save users to get IDs
        
        # Create Faculty Profile
        faculty_profile = FacultyProfile(
            user_id=faculty_user.id,
            name="Dr. Rajesh Patil",
            emp_id="FAC-0101",
            department="Computer Science",
            designation="Associate Professor",
            contact="9876543210"
        )
        db.session.add(faculty_profile)
        
        # 3. Create Student User
        student_pass = generate_password_hash("student123")
        student_user = User(
            username="student1",
            email="student1@campusconnect.com",
            password_hash=student_pass,
            role="student"
        )
        db.session.add(student_user)
        db.session.commit()
        
        # Create Student Profile
        student_profile = StudentProfile(
            user_id=student_user.id,
            name="Rohan Sharma",
            roll_no="STU-0010",
            department="Computer Science",
            semester=4,
            gpa=8.75,
            skills="Python, Flask, JavaScript, HTML, CSS, SQL",
            certificates="Google Cloud Certified Associate Cloud Engineer, FreeCodeCamp Responsive Web Design",
            bio="Pre-final year CS undergraduate student. Passionate about Fullstack development and Machine Learning implementations.",
            github_url="https://github.com/rohansharma",
            contact="8765432109"
        )
        db.session.add(student_profile)
        db.session.commit()
        
        # 4. Add Student Projects
        proj1 = Project(
            student_id=student_profile.id,
            title="E-Commerce Backend API",
            description="RESTful APIs built using Flask-SQLAlchemy with fully tested endpoints, token authentication, and stripe payment processing simulation.",
            github_url="https://github.com/rohansharma/flask-ecommerce-api",
            live_url="",
            status="Completed"
        )
        proj2 = Project(
            student_id=student_profile.id,
            title="AI Voice Assistant Dashboard",
            description="A premium glassmorphic single-page web dashboard that interfaces with NLP services, featuring speech recognition and synthesizers.",
            github_url="https://github.com/rohansharma/speech-nlp-dashboard",
            live_url="",
            status="Active"
        )
        db.session.add_all([proj1, proj2])
        
        # 5. Add Attendance Records
        att1 = Attendance(student_id=student_profile.id, date="2026-06-15", status="Present", marked_by="Dr. Rajesh Patil")
        att2 = Attendance(student_id=student_profile.id, date="2026-06-16", status="Present", marked_by="Dr. Rajesh Patil")
        att3 = Attendance(student_id=student_profile.id, date="2026-06-17", status="Present", marked_by="Dr. Rajesh Patil")
        att4 = Attendance(student_id=student_profile.id, date="2026-06-18", status="Present", marked_by="Dr. Rajesh Patil")
        att5 = Attendance(student_id=student_profile.id, date="2026-06-19", status="Absent", marked_by="Dr. Rajesh Patil")
        db.session.add_all([att1, att2, att3, att4, att5])
        
        # 6. Add Announcements
        ann1 = Announcement(
            title="End Semester Exams Timetable Out",
            content="The End Semester Examinations for academic year 2025-26 will commence from July 5th, 2026. Students can download timetables and room allocations from the download section. Maintain 75% attendance to qualify.",
            target_role="all"
        )
        ann2 = Announcement(
            title="Smart India Hackathon Registrations Open",
            content="National level Hackathon registration is open until June 25th, 2026. Teams should prepare abstract proposals and submit them to the department coordinator Dr. Rajesh Patil.",
            target_role="student"
        )
        ann3 = Announcement(
            title="Faculty Meeting regarding Syllabus Reviews",
            content="A departmental meeting will be held on Monday at 3:00 PM in Seminar Hall 1 to review course deliverables and semester schedules.",
            target_role="faculty"
        )
        db.session.add_all([ann1, ann2, ann3])
        
        # 7. Add Events
        ev1 = Event(
            title="Global Tech Summit 2026",
            description="Annual campus summit containing keynote speeches from industry lead architects from Google and Microsoft talking about NextGen Web Architectures.",
            date="2026-06-28 10:00 AM",
            type="Placement",
            created_by="Admin"
        )
        ev2 = Event(
            title="Web Dev Hack-Session",
            description="Hands-on coding workshop on building APIs with micro-frameworks like Flask and FastAPI.",
            date="2026-06-22 02:00 PM",
            type="Academic",
            created_by="Dr. Rajesh Patil"
        )
        db.session.add_all([ev1, ev2])
        
        db.session.commit()
        print("Database seeded successfully with test records!")

if __name__ == "__main__":
    seed_db()
