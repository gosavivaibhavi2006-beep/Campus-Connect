import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_dev_night_key'

# Database Configuration
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'resources')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'ppt', 'txt', 'zip', 'png', 'jpg', 'jpeg'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ----------------- Database Models -----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'faculty', 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    faculty_profile = db.relationship('FacultyProfile', backref='user', uselist=False, cascade="all, delete-orphan")

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), default="Computer Science")
    semester = db.Column(db.Integer, default=1)
    gpa = db.Column(db.Float, default=0.0)
    skills = db.Column(db.String(255), default="HTML,CSS,JavaScript")  # Comma-separated
    certificates = db.Column(db.Text, default="")  # Comma-separated or list description
    bio = db.Column(db.Text, default="Passionate developer in training.")
    github_url = db.Column(db.String(200), default="")
    contact = db.Column(db.String(20), default="")

    projects = db.relationship('Project', backref='student', cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='student', cascade="all, delete-orphan")
    feedbacks = db.relationship('Feedback', backref='student', cascade="all, delete-orphan")

class FacultyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), default="Computer Science")
    designation = db.Column(db.String(100), default="Assistant Professor")
    contact = db.Column(db.String(20), default="")

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    github_url = db.Column(db.String(200), default="")
    live_url = db.Column(db.String(200), default="")
    status = db.Column(db.String(50), default="Completed")  # 'Active', 'Completed', 'Pending'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    status = db.Column(db.String(10), nullable=False)  # 'Present', 'Absent'
    marked_by = db.Column(db.String(100), default="System")

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), default="Academic")  # 'Academic', 'Extracurricular', 'Placement'
    created_by = db.Column(db.String(100), default="Admin")

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    target_role = db.Column(db.String(20), default="all")  # 'all', 'faculty', 'student'

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    filename = db.Column(db.String(200), nullable=False)
    uploaded_by = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), default="Computer Science")
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profile.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    reply = db.Column(db.Text, default=None)

# ----------------- Middlewares / Helpers -----------------

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(roles=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'error')
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('login'))
            if roles and user.role not in roles:
                flash('Unauthorized access.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Optional OpenAI ChatGPT helper for natural fallback responses
def query_openai(prompt):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None

    model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    endpoint = 'https://api.openai.com/v1/chat/completions'
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a friendly campus assistant for a student and faculty portal.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 250,
        'top_p': 1,
        'frequency_penalty': 0,
        'presence_penalty': 0
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        request_obj = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        with urllib.request.urlopen(request_obj, timeout=15) as response:
            response_text = response.read().decode('utf-8')
            result = json.loads(response_text)
            return result['choices'][0]['message']['content'].strip()
    except Exception:
        return None

# Context processor for templates
@app.context_processor
def inject_globals():
    user = get_current_user()
    now_hour = datetime.now().hour
    ticker_status = "System Active 🟢"
    if now_hour > 22 or now_hour < 6:
        ticker_status = "Dev Night Mode Active 🌙"
    elif now_hour >= 12 and now_hour <= 14:
        ticker_status = "High Traffic Load 🟠"
    
    return dict(
        current_user=user,
        system_ticker=ticker_status,
        now_year=datetime.now().year
    )

# ----------------- General Routes -----------------

@app.route('/')
def index():
    # Fetch general statistics for landing page
    student_count = StudentProfile.query.count()
    project_count = Project.query.count()
    event_count = Event.query.count()
    skills_list = ["Python", "Flask", "React", "NodeJS", "Tailwind CSS", "SQL", "Docker", "Machine Learning"]
    latest_announcements = Announcement.query.order_by(Announcement.date_posted.desc()).limit(3).all()
    
    return render_template(
        'index.html',
        student_count=student_count,
        project_count=project_count,
        event_count=event_count,
        skills_list=skills_list,
        latest_announcements=latest_announcements
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'faculty':
                return redirect(url_for('faculty_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # 'student' or 'faculty'
        name = request.form.get('name')
        
        # Admin registers directly in admin panel, default register is for Student/Faculty
        if role not in ['student', 'faculty']:
            role = 'student'
            
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('Username or Email already registered.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'student':
            roll_no = request.form.get('roll_no', f"STU-{new_user.id:04d}")
            profile = StudentProfile(user_id=new_user.id, name=name, roll_no=roll_no)
            db.session.add(profile)
        elif role == 'faculty':
            emp_id = request.form.get('emp_id', f"FAC-{new_user.id:04d}")
            profile = FacultyProfile(user_id=new_user.id, name=name, emp_id=emp_id)
            db.session.add(profile)
            
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# ----------------- Admin Routes -----------------

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def admin_dashboard():
    if request.method == 'POST':
        delete_user_id = request.form.get('delete_user_id')
        if delete_user_id:
            user_to_delete = User.query.get(delete_user_id)
            if user_to_delete and user_to_delete.role in ['student', 'faculty']:
                db.session.delete(user_to_delete)
                db.session.commit()
                flash(f'{user_to_delete.role.title()} account deleted successfully.', 'success')
            else:
                flash('Unable to delete selected account.', 'error')
        return redirect(url_for('admin_dashboard'))

    students = StudentProfile.query.all()
    faculties = FacultyProfile.query.all()
    projects = Project.query.all()
    events = Event.query.all()
    announcements = Announcement.query.all()
    
    # Compile skill distribution
    skill_counts = {}
    for stu in students:
        for sk in [s.strip() for s in stu.skills.split(',') if s.strip()]:
            skill_counts[sk] = skill_counts.get(sk, 0) + 1
            
    # Top skills sorted
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template(
        'admin/dashboard.html',
        students=students,
        faculties=faculties,
        projects=projects,
        events=events,
        announcements=announcements,
        top_skills=top_skills
    )

@app.route('/admin/manage_students', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def admin_manage_students():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password', 'student123')
            name = request.form.get('name')
            roll_no = request.form.get('roll_no')
            department = request.form.get('department')
            semester = int(request.form.get('semester', 1))
            gpa = float(request.form.get('gpa', 0.0))
            skills = request.form.get('skills', 'HTML,CSS')
            
            user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
            if user_exists:
                flash('Student registration failed. Username/Email exists.', 'error')
            else:
                hashed = generate_password_hash(password)
                u = User(username=username, email=email, password_hash=hashed, role='student')
                db.session.add(u)
                db.session.commit()
                
                profile = StudentProfile(
                    user_id=u.id, name=name, roll_no=roll_no,
                    department=department, semester=semester, gpa=gpa, skills=skills
                )
                db.session.add(profile)
                db.session.commit()
                flash(f'Student {name} added successfully!', 'success')
                
        elif action == 'edit':
            student_id = request.form.get('student_id')
            profile = StudentProfile.query.get(student_id)
            if profile:
                profile.name = request.form.get('name')
                profile.roll_no = request.form.get('roll_no')
                profile.department = request.form.get('department')
                profile.semester = int(request.form.get('semester', 1))
                profile.gpa = float(request.form.get('gpa', 0.0))
                profile.skills = request.form.get('skills')
                db.session.commit()
                flash('Student profile updated.', 'success')
                
        elif action == 'delete':
            student_id = request.form.get('student_id')
            profile = StudentProfile.query.get(student_id)
            if profile:
                user = User.query.get(profile.user_id)
                db.session.delete(user) # Cascades delete to student profile, projects, etc.
                db.session.commit()
                flash('Student account deleted.', 'success')
                
    students = StudentProfile.query.all()
    return render_template('admin/manage_students.html', students=students)

@app.route('/admin/manage_faculty', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def admin_manage_faculty():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password', 'faculty123')
            name = request.form.get('name')
            emp_id = request.form.get('emp_id')
            department = request.form.get('department')
            designation = request.form.get('designation')
            contact = request.form.get('contact')
            
            user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
            if user_exists:
                flash('Faculty registration failed. Username/Email exists.', 'error')
            else:
                hashed = generate_password_hash(password)
                u = User(username=username, email=email, password_hash=hashed, role='faculty')
                db.session.add(u)
                db.session.commit()
                
                profile = FacultyProfile(
                    user_id=u.id, name=name, emp_id=emp_id,
                    department=department, designation=designation, contact=contact
                )
                db.session.add(profile)
                db.session.commit()
                flash(f'Faculty {name} added successfully!', 'success')
                
        elif action == 'edit':
            faculty_id = request.form.get('faculty_id')
            profile = FacultyProfile.query.get(faculty_id)
            if profile:
                profile.name = request.form.get('name')
                profile.emp_id = request.form.get('emp_id')
                profile.department = request.form.get('department')
                profile.designation = request.form.get('designation')
                profile.contact = request.form.get('contact')
                db.session.commit()
                flash('Faculty profile updated.', 'success')
                
        elif action == 'delete':
            faculty_id = request.form.get('faculty_id')
            profile = FacultyProfile.query.get(faculty_id)
            if profile:
                user = User.query.get(profile.user_id)
                db.session.delete(user)
                db.session.commit()
                flash('Faculty account deleted.', 'success')
                
    faculties = FacultyProfile.query.all()
    return render_template('admin/manage_faculty.html', faculties=faculties)

@app.route('/admin/events', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def admin_events():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            title = request.form.get('title')
            description = request.form.get('description')
            date = request.form.get('date')
            type_ = request.form.get('type')
            
            ev = Event(title=title, description=description, date=date, type=type_, created_by="Admin")
            db.session.add(ev)
            db.session.commit()
            flash('Event created successfully!', 'success')
        elif action == 'delete':
            ev_id = request.form.get('event_id')
            ev = Event.query.get(ev_id)
            if ev:
                db.session.delete(ev)
                db.session.commit()
                flash('Event deleted.', 'success')
                
    events = Event.query.all()
    return render_template('admin/events.html', events=events)

@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required(roles=['admin'])
def admin_announcements():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            title = request.form.get('title')
            content = request.form.get('content')
            target_role = request.form.get('target_role', 'all')
            
            ann = Announcement(title=title, content=content, target_role=target_role)
            db.session.add(ann)
            db.session.commit()
            flash('Announcement published!', 'success')
        elif action == 'delete':
            ann_id = request.form.get('announcement_id')
            ann = Announcement.query.get(ann_id)
            if ann:
                db.session.delete(ann)
                db.session.commit()
                flash('Announcement deleted.', 'success')
                
    announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements)

# ----------------- Faculty Routes -----------------

@app.route('/faculty/dashboard', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_dashboard():
    user = get_current_user()
    fac_profile = user.faculty_profile

    if request.method == 'POST':
        feedback_id = request.form.get('feedback_id')
        reply_text = request.form.get('reply', '').strip()
        if feedback_id and reply_text:
            fb = Feedback.query.get(feedback_id)
            if fb and fb.student.department == fac_profile.department:
                fb.reply = reply_text
                db.session.commit()
                flash('Feedback response posted successfully.', 'success')
            else:
                flash('Unable to update this feedback ticket.', 'error')
        return redirect(url_for('faculty_dashboard'))

    student_count = StudentProfile.query.filter_by(department=fac_profile.department).count()
    events = Event.query.all()
    announcements = Announcement.query.filter(Announcement.target_role.in_(['all', 'faculty'])).order_by(Announcement.date_posted.desc()).limit(5).all()
    feedbacks = Feedback.query.join(StudentProfile, Feedback.student_id == StudentProfile.id)
    feedbacks = feedbacks.filter(StudentProfile.department == fac_profile.department).order_by(Feedback.date_submitted.desc()).all()

    return render_template(
        'faculty/dashboard.html',
        profile=fac_profile,
        student_count=student_count,
        events=events,
        announcements=announcements,
        feedbacks=feedbacks
    )

@app.route('/faculty/profile', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_profile():
    user = get_current_user()
    profile = user.faculty_profile
    
    if request.method == 'POST':
        profile.name = request.form.get('name')
        profile.department = request.form.get('department')
        profile.designation = request.form.get('designation')
        profile.contact = request.form.get('contact')
        
        # Optional password update
        new_password = request.form.get('password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    return render_template('faculty/profile.html', profile=profile)

@app.route('/faculty/attendance', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_attendance():
    user = get_current_user()
    fac_profile = user.faculty_profile
    students = StudentProfile.query.filter_by(department=fac_profile.department).all()
    
    if request.method == 'POST':
        date_str = request.form.get('date', datetime.today().strftime('%Y-%m-%d'))
        
        # Save attendance for each student in the list
        for stu in students:
            status = request.form.get(f'status_{stu.id}', 'Absent')
            
            # Check if record already exists for this day
            att = Attendance.query.filter_by(student_id=stu.id, date=date_str).first()
            if att:
                att.status = status
                att.marked_by = fac_profile.name
            else:
                att = Attendance(
                    student_id=stu.id,
                    date=date_str,
                    status=status,
                    marked_by=fac_profile.name
                )
                db.session.add(att)
                
        db.session.commit()
        flash(f'Attendance recorded for {date_str} successfully!', 'success')
        return redirect(url_for('faculty_attendance'))
        
    # Get attendance history for summary
    recent_attendance = Attendance.query.order_by(Attendance.date.desc()).limit(30).all()
    return render_template('faculty/attendance.html', students=students, recent_attendance=recent_attendance)

@app.route('/faculty/create_event', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_create_event():
    user = get_current_user()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        type_ = request.form.get('type')
        
        ev = Event(title=title, description=description, date=date, type=type_, created_by=user.faculty_profile.name)
        db.session.add(ev)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('faculty_dashboard'))
        
    return render_template('faculty/create_event.html')

@app.route('/faculty/announcements', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_announcements():
    user = get_current_user()
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        target_role = request.form.get('target_role', 'student')
        
        ann = Announcement(title=title, content=content, target_role=target_role)
        db.session.add(ann)
        db.session.commit()
        flash('Announcement published!', 'success')
        return redirect(url_for('faculty_announcements'))
        
    announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template('faculty/announcements.html', announcements=announcements)

@app.route('/faculty/resources', methods=['GET', 'POST'])
@login_required(roles=['faculty'])
def faculty_resources():
    user = get_current_user()
    profile = user.faculty_profile
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        file = request.files.get('file')

        if not title or not file or file.filename == '':
            flash('Please provide a title and upload a file.', 'error')
        elif not allowed_file(file.filename):
            flash('Unsupported file format. Use PDF, DOCX, PPTX, ZIP, TXT, PNG, JPG, or JPEG.', 'error')
        else:
            safe_name = secure_filename(file.filename)
            filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            resource = Resource(
                title=title,
                description=description,
                filename=filename,
                uploaded_by=profile.name,
                department=profile.department
            )
            db.session.add(resource)
            db.session.commit()
            flash('Resource uploaded successfully.', 'success')
            return redirect(url_for('faculty_resources'))

    resources = Resource.query.order_by(Resource.date_uploaded.desc()).all()
    return render_template('faculty/resources.html', resources=resources, profile=profile)

@app.route('/student/resume', methods=['GET', 'POST'])
@login_required(roles=['student'])
def student_resume():
    user = get_current_user()
    profile = user.student_profile
    if request.method == 'POST':
        file = request.files.get('resume_file')
        if not file or file.filename == '':
            flash('Please choose a resume file to upload.', 'error')
            return redirect(url_for('student_resume'))
        if not allowed_file(file.filename):
            flash('Unsupported file format. Use PDF, DOCX, PPTX, TXT, or ZIP.', 'error')
            return redirect(url_for('student_resume'))

        safe_name = secure_filename(file.filename)
        filename = f"resume_{user.username}_{int(datetime.utcnow().timestamp())}_{safe_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        resume_resource = Resource(
            title='Resume',
            description='Student resume upload',
            filename=filename,
            uploaded_by=user.username,
            department=profile.department
        )
        db.session.add(resume_resource)
        db.session.commit()
        flash('Resume uploaded successfully.', 'success')
        return redirect(url_for('student_resume'))

    projects = Project.query.filter_by(student_id=profile.id).all()
    resume = Resource.query.filter_by(title='Resume', uploaded_by=user.username).order_by(Resource.date_uploaded.desc()).first()
    return render_template('student/resume.html', profile=profile, projects=projects, viewer='student', resume=resume)

@app.route('/faculty/student_resumes')
@login_required(roles=['faculty'])
def faculty_student_resumes():
    user = get_current_user()
    profile = user.faculty_profile
    students = StudentProfile.query.filter_by(department=profile.department).all()
    return render_template('faculty/student_resumes.html', students=students)

@app.route('/view_resume/<int:student_id>')
@login_required(roles=['admin','faculty'])
def view_resume(student_id):
    user = get_current_user()
    student = StudentProfile.query.get_or_404(student_id)
    if user.role == 'faculty' and student.department != user.faculty_profile.department:
        flash('You can only view resumes for students in your department.', 'error')
        return redirect(url_for('faculty_dashboard'))
    projects = Project.query.filter_by(student_id=student.id).all()
    resume = Resource.query.filter_by(title='Resume', uploaded_by=student.user.username).order_by(Resource.date_uploaded.desc()).first()
    return render_template('student/resume.html', profile=student, projects=projects, viewer=user.role, resume=resume)

# ----------------- Student Routes -----------------

@app.route('/student/dashboard')
@login_required(roles=['student'])
def student_dashboard():
    user = get_current_user()
    profile = user.student_profile
    
    # Build list of skills for the spice meter / level indicators
    # We parse the comma-separated string and map each skill to a "fire" level
    skills_raw = [s.strip() for s in profile.skills.split(',') if s.strip()]
    skills_with_level = []
    
    # We simulate a "proficiency level" by hash values or lengths to render 🔥 emojis
    for idx, skill in enumerate(skills_raw):
        level = (len(skill) % 3) + 1  # Outputs 1, 2, or 3
        skills_with_level.append({'name': skill, 'level': level})
        
    projects = Project.query.filter_by(student_id=profile.id).all()
    
    # Fetch events & announcements targetted at students
    events = Event.query.all()
    announcements = Announcement.query.filter(Announcement.target_role.in_(['all', 'student'])).order_by(Announcement.date_posted.desc()).limit(5).all()
    
    # Attendance summary
    attendances = Attendance.query.filter_by(student_id=profile.id).all()
    p_count = sum(1 for a in attendances if a.status == 'Present')
    total_att = len(attendances)
    att_percent = int((p_count / total_att) * 100) if total_att > 0 else 100
    
    return render_template(
        'student/dashboard.html',
        profile=profile,
        skills=skills_with_level,
        projects=projects,
        events=events,
        announcements=announcements,
        attendance_percentage=att_percent
    )

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required(roles=['student'])
def student_profile():
    user = get_current_user()
    profile = user.student_profile
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            profile.name = request.form.get('name')
            profile.department = request.form.get('department')
            profile.semester = int(request.form.get('semester', 1))
            profile.gpa = float(request.form.get('gpa', profile.gpa or 0.0))
            profile.bio = request.form.get('bio')
            profile.github_url = request.form.get('github_url')
            profile.contact = request.form.get('contact')
            profile.skills = request.form.get('skills')
            profile.certificates = request.form.get('certificates')
            
            # Optional password change
            new_password = request.form.get('password')
            if new_password:
                user.password_hash = generate_password_hash(new_password)
                
            db.session.commit()
            flash('Profile details updated!', 'success')
            
        elif action == 'add_project':
            title = request.form.get('title')
            description = request.form.get('description')
            github_url = request.form.get('github_url')
            live_url = request.form.get('live_url')
            status = request.form.get('status', 'Completed')
            
            p = Project(
                student_id=profile.id, title=title, description=description,
                github_url=github_url, live_url=live_url, status=status
            )
            db.session.add(p)
            db.session.commit()
            flash('New project added to your portfolio!', 'success')
            
        elif action == 'delete_project':
            project_id = request.form.get('project_id')
            p = Project.query.get(project_id)
            if p and p.student_id == profile.id:
                db.session.delete(p)
                db.session.commit()
                flash('Project removed from portfolio.', 'success')
                
        return redirect(url_for('student_profile'))
        
    projects = Project.query.filter_by(student_id=profile.id).all()
    return render_template('student/profile.html', profile=profile, projects=projects)

@app.route('/student/events')
@login_required(roles=['student'])
def student_events():
    events = Event.query.order_by(Event.date.asc()).all()
    return render_template('student/events.html', events=events)

@app.route('/student/attendance')
@login_required(roles=['student'])
def student_attendance_view():
    user = get_current_user()
    profile = user.student_profile
    attendances = Attendance.query.filter_by(student_id=profile.id).order_by(Attendance.date.desc()).all()
    
    p_count = sum(1 for a in attendances if a.status == 'Present')
    total = len(attendances)
    rate = int((p_count / total) * 100) if total > 0 else 100
    
    return render_template('student/attendance.html', attendances=attendances, attendance_percentage=rate)

@app.route('/student/feedback', methods=['GET', 'POST'])
@login_required(roles=['student'])
def student_feedback():
    user = get_current_user()
    profile = user.student_profile
    
    if request.method == 'POST':
        content = request.form.get('content')
        fb = Feedback(student_id=profile.id, content=content)
        db.session.add(fb)
        db.session.commit()
        flash('Feedback submitted successfully. Thank you!', 'success')
        return redirect(url_for('student_feedback'))
        
    feedbacks = Feedback.query.filter_by(student_id=profile.id).order_by(Feedback.date_submitted.desc()).all()
    return render_template('student/feedback.html', feedbacks=feedbacks)

@app.route('/student/resources')
@login_required(roles=['student'])
def student_resources():
    resources = Resource.query.order_by(Resource.date_uploaded.desc()).all()
    return render_template('student/resources.html', resources=resources)

@app.route('/student/announcements')
@login_required(roles=['student'])
def student_announcements():
    announcements = Announcement.query.filter(Announcement.target_role.in_(['all', 'student'])).order_by(Announcement.date_posted.desc()).all()
    return render_template('student/announcements.html', announcements=announcements)

# ----------------- NLP Chatbot Logic -----------------

@app.route('/chatbot/ask', methods=['POST'])
def chatbot_ask():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    lower_message = message.lower()
    
    if not lower_message:
        return jsonify({"reply": "I am listening. Please ask me anything about your grades, projects, attendance, or the campus system!"})

    user = get_current_user()
    role = user.role if user else 'guest'
    name = user.username if user else 'Visitor'

    def contains(*terms):
        return any(term in lower_message for term in terms)

    general_knowledge = {
        'admission': 'Admission details depend on your institution. Check the portal and announcements for deadlines, required documents, and eligibility criteria.',
        'application': 'Applications are usually submitted online with your academic records, identity proof, and any required recommendation letters.',
        'attendance': 'Attendance is tracked per student and displayed on your dashboard. Students can check their attendance rate, while faculty can mark attendance from the portal.',
        'authorisation': 'User authorisation controls who can access student, faculty, and admin features. This portal uses login roles to protect data.',
        'btech': 'BTech is an engineering degree. It normally includes core engineering courses, lab work, projects, and campus placements.',
        'campus': 'Campus services include announcements, events, student profiles, faculty resources, attendance tracking, and placement support.',
        'certificate': 'Certificates may be issued after completing a course, training, or workshop. Check with the portal admin or your institute office for details.',
        'chatbot': 'This chatbot can answer campus-related questions and provide guidance on studies, projects, attendance, announcements, and general career topics.',
        'class': 'Class details such as schedule, room, and instructor are usually managed by your institution. Check the timetable or ask your faculty for exact information.',
        'course': 'Your course details are managed in the portal. If you need help with a subject, check your faculty announcements or contact your instructor.',
        'credit': 'Credits are the units assigned to classes. Your semester GPA and degree progress are calculated using credit values and grades.',
        'deadline': 'Deadlines are important. Keep track of assignment due dates, exam registration dates, and project submission timelines in your calendar.',
        'degree': 'A degree is the qualification you earn after completing your program. A strong academic record and projects help you stand out in the job market.',
        'department': 'Departments host courses and faculty for specific subjects such as computer science, business, or arts. They coordinate exams, assignments, and student guidance.',
        'doubt': 'If you have a doubt, ask your faculty or use study groups to clarify it. Clear doubts early so you can move forward confidently in the subject.',
        'exam': 'Exam preparation is easier when you review notes, practice past questions, and ask your faculty if you need extra help.',
        'exam schedule': 'The exam schedule should be available in the portal or through faculty announcements. Check there for dates, times, and exam venues.',
        'faculty': 'Faculty are your teachers and mentors. They can help with subject questions, attendance, and academic guidance.',
        'feedback': 'Feedback helps improve the portal and classes. Share your experience, suggestions, and concerns through the feedback section.',
        'grade': 'Your grade is the letter or number you receive in a class. Grades are used to calculate your GPA and show academic performance.',
        'gpa': 'GPA stands for Grade Point Average. It reflects your academic performance and is visible on the student dashboard.',
        'hostel': 'Hostel information includes accommodation rules, mess timings, and facility support. Contact campus administration for details on hostel allocation.',
        'internship': 'Internships are a great way to gain real experience. Look for roles that use your skills and give you chances to learn from professionals.',
        'interview': 'Interview preparation is about practicing common questions, knowing your projects, and demonstrating problem-solving with confidence.',
        'job': 'Current job opportunities are strong in technology, business analytics, healthcare, and digital services. Focus on practical skills, communication, and learning tools used in the industry.',
        'library': 'The library provides books, digital resources, and research help. Use it for reference material, textbooks, and quiet study time.',
        'login': 'Login lets you access your student or faculty dashboard. Use the credentials provided during registration to sign in securely.',
        'logout': 'Logout ends your session and helps keep your account safe. Always log out when you finish using a shared computer.',
        'marks': 'Marks are the scores you earn on assignments, tests, and exams. They combine to determine your final grade in a course.',
        'mentor': 'A mentor guides you through academics and career planning. Reach out to faculty or senior students if the portal supports mentorship programs.',
        'notice': 'Notices are official updates posted for students and faculty. Check the announcements page regularly for the latest information.',
        'online classes': 'Online classes let you learn remotely using video lectures, recorded sessions, and chat tools. Stay organized and complete any online assignments on time.',
        'assignment': 'Assignments help you practice what you learn. Read instructions carefully, start early, and submit through the portal if required.',
        'project': 'A project can be anything you build to solve a problem or show a skill. Good examples are apps, websites, reports, or data analysis tools.',
        'portfolio': 'A portfolio is a showcase of your best work. Include project descriptions, tools used, and what you learned from each project.',
        'placement': 'Placements connect students to employers. Prepare with strong projects, resume practice, and interview readiness for campus placement drives.',
        'policy': 'Policies define how students and faculty should behave in the portal and on campus. Follow the rules shared by your institution to stay in good standing.',
        'profile': 'Your profile shows your name, year, skills, and academic details. Keep it updated so faculty and placement teams can see your strengths.',
        'recommendation': 'A recommendation is a letter from faculty or supervisors. Ask for one after demonstrating strong work and effort in your coursework or project.',
        'registration': 'Registration is the process of signing up for courses, classes, or exams. Complete it before deadlines to avoid missing important events.',
        'result': 'Results show your final grades and exam outcomes. Check the portal once results are posted to see how you performed.',
        'resume': 'A strong resume focuses on your projects, skills, achievements, and the tools you used. Keep it concise and highlight your most relevant work.',
        'scholarship': 'Scholarships provide financial support for students. Check eligibility rules, application requirements, and deadlines from your institution.',
        'semester': 'A semester is a fixed period of study, usually with classes, assignments, and exams. Track your progress and plan study time across the semester.',
        'skills': 'Focus on both technical skills and soft skills. Technical skills show your work, and communication and teamwork are important for every job.',
        'software': 'Software includes tools like office suites, programming IDEs, and course-specific applications. Learn the tools relevant to your classes and projects.',
        'study': 'Studying works best with a clear schedule, short focused sessions, and regular breaks. Use your dashboard to keep track of subjects and deadlines.',
        'syllabus': 'The syllabus lists the topics you need to study for a course. Use it to plan your study schedule and make sure you cover every subject area.',
        'timetable': 'The timetable shows your class schedule, lab hours, and exam timings. Review it regularly to avoid missing sessions or deadlines.',
        'training': 'Training programs can help you learn new tools and techniques. Look for workshops, faculty-led sessions, or online courses to build your skills.',
        'transport': 'Transport services include buses, parking, and campus shuttles. Check your institution’s notices for routes, timings, and pass details.',
        'vacation': 'Vacation periods give you time to rest, revise, and work on projects. Use them wisely to refresh your knowledge and prepare for the next semester.',
        'website': 'The portal website is your entry point for courses, announcements, and campus resources. Bookmark it and check it often for updates.',
        'workshop': 'Workshops teach practical skills through hands-on sessions. Attend them for extra learning and certificates that strengthen your portfolio.',
        'writing': 'Writing assignments need clear structure, good grammar, and strong ideas. Plan your response, use examples, and proofread before submission.',
        'python': 'Python is a high-level programming language used across campus for programming, scripting, and web apps. It is also one of the skills shown in student portfolios.',
        'flask': 'Flask is the Python web framework that powers this portal. It handles routing, templates, forms, and database requests.',
        'ai': 'This assistant uses simple keyword-based campus logic today. For a production AI chatbot, you can integrate an external NLP service or model.',
        'web development': 'Web development combines HTML, CSS, JavaScript, and backend frameworks like Flask to build modern campus applications.',
        'technology': 'Technology skills are useful for many jobs. Start with basics like Python, web development, or data tools and build from there.',
        'machine learning': 'Machine learning uses data and algorithms to teach computers how to recognize patterns and make predictions.',
        'data science': 'Data science focuses on collecting, cleaning, analyzing, and visualizing data to support better decisions.',
        'cybersecurity': 'Cybersecurity protects systems, networks, and data from unauthorized access and attacks.',
        'cloud': 'Cloud computing delivers IT services like storage, databases, and servers over the internet instead of local machines.',
        'soft skills': 'Soft skills include communication, teamwork, time management, and problem-solving. Employers value them as much as technical abilities.',
        'communication': 'Strong communication helps you explain ideas, work with others, and build good relationships in academics and the workplace.',
        'time management': 'Time management means planning your day so you finish tasks on time without overloading yourself. Use tools, lists, and priorities to stay organized.',
        'motivation': 'Motivation comes from setting clear goals, tracking progress, and remembering why your education matters for your future.',
        'mental health': 'Mental health is important. Take breaks, talk to friends or counselors, and balance study with rest and exercise.',
        'break': 'Breaks help your brain recharge. Take short pauses during study sessions and use longer breaks to relax or exercise.',
        'food': 'Food preferences vary widely; popular choices include local street food, traditional dishes, or comfort food favorites like pizza and curry.',
        'travel': 'Travel is a fun way to explore new cities and cultures. Think about the season, budget, and what activities you enjoy.',
        'holiday': 'Holidays are perfect for relaxing with family or visiting nearby attractions. Planning ahead makes them more enjoyable.',
        'mango': 'Mango is a tropical fruit with sweet, juicy flesh. It is often enjoyed fresh, in smoothies, or as a dessert topping.',
        'analysis': 'Analysis means examining information to understand patterns or make decisions. Data analysis is useful in many fields like business, science, and software.'
    }

    # Prefer learning intent when the question is about how to learn a topic
    if contains('learn', 'learning', 'study', 'which material', 'what material', 'best resource', 'how to learn', 'how do i learn', 'practice', 'tutorial', 'course', 'guide') and contains('python', 'programming', 'code', 'coding'):
        return jsonify({"reply": "To learn Python, start with beginner-friendly resources like Codecademy, W3Schools, or free Python tutorials. Focus on fundamentals such as variables, loops, functions, and lists, then build small projects like a calculator or simple game."})
    if contains('which notes', 'what notes', 'notes should', 'refer', 'reference material', 'which study', 'study material', 'material should i'):
        return jsonify({"reply": "For study material, focus on lecture notes, assignment instructions, and any faculty shared resources. Review your class topics and practice with examples from current chapters."})
    if contains('create', 'build', 'start', 'make', 'develop') and contains('project'):
        return jsonify({"reply": "To create a good project, choose a useful idea, break it into small tasks, and start building. Add it to your portfolio with a title, description, technologies, and what you learned."})
    if contains('which kind', 'which type', 'what kind', 'what type') and contains('project'):
        return jsonify({"reply": "Choose a project that matches your interests. Web apps, study organizers, data trackers, or small automation tools are excellent portfolio starters."})
    if contains('portfolio', 'create portfolio', 'build portfolio', 'portfolio?'):
        return jsonify({"reply": "A strong portfolio highlights your best work, the tools used, and the value it provides. Include a few polished projects with clear descriptions and outcomes."})
    if contains('campus task', 'campus tasks', 'campus task', 'campus work', 'task list'):
        return jsonify({"reply": "Campus tasks often include attendance, announcements, events, profile updates, and study planning. Use your dashboard and announcements page to stay updated."})
    if contains('attendance', 'attendence', 'present', 'absent', 'attendance rate', 'my attendance'):
        if user and user.role == 'student':
            profile = user.student_profile
            atts = Attendance.query.filter_by(student_id=profile.id).all()
            p_count = sum(1 for a in atts if a.status == 'Present')
            total = len(atts)
            percent = int((p_count / total) * 100) if total > 0 else 100
            return jsonify({"reply": f"Your attendance rate is **{percent}%** ({p_count}/{total} present). Keep your attendance strong!"})
        elif user and user.role == 'faculty':
            return jsonify({"reply": "Faculty can manage attendance from the attendance page. Use that tool to mark student presence and review records."})
        else:
            return jsonify({"reply": "Attendance is tracked in the portal. Please log in as a student or faculty member to view or update attendance."})
    if contains('career', 'job', 'jobs', 'scope', 'industry', 'market', 'opportunity'):
        return jsonify({"reply": "For career questions, focus on building practical skills, real projects, and good communication. Fields like software development, data analytics, cloud computing, cybersecurity, and digital marketing are in demand."})
    if contains('resume', 'cv', 'interview', 'internship', 'placement'):
        return jsonify({"reply": "Work on your resume and interview preparation by highlighting your projects, explaining what you built, and practicing clear responses to common questions."})

    for key, answer in general_knowledge.items():
        if key in lower_message:
            return jsonify({"reply": answer})

    # Handle common casual questions
    if contains('how are you', 'how is it going', 'what is up'):
        return jsonify({"reply": "I am your Campus AI Assistant. I can help answer questions about this portal, your studies, or simple everyday topics too."})
    if contains('tell me a joke', 'joke', 'funny'):
        return jsonify({"reply": "Why did the student bring a ladder to class? Because the course was on a whole new level!"})
    if contains('best places', 'where to go', 'good place'):
        return jsonify({"reply": "A nice place to visit is a local park, market, or museum. Choose somewhere close, safe, and interesting to you."})
    if contains('weather', 'rain', 'sunny', 'cloudy', 'temperature'):
        return jsonify({"reply": "I don't have live weather updates here, but generally check a weather app or local forecast for the latest conditions."})
    if contains('mango', 'fruit', 'fruits', 'sweet'):
        return jsonify({"reply": "Mango is a sweet tropical fruit. It is great fresh, in smoothies, and on hot days when you want something juicy."})
    if contains('study', 'exam', 'course', 'semester', 'subject', 'class', 'homework', 'assignment', 'syllabus', 'revision', 'notes', 'paper', 'chapter', 'question'):
        return jsonify({"reply": "For study queries, focus on your lecture notes, recent assignments, and any faculty guidance. Break tasks into smaller topics, revise regularly, and ask teachers if you need clarification."})
    if contains('faculty', 'teacher', 'instructor', 'mentor', 'professor', 'staff'):
        return jsonify({"reply": "Faculty are your instructors and mentors. If you need academic help, check the announcements or contact them through the portal if that option is available."})
    if contains('career', 'job', 'jobs', 'scope', 'industry', 'market', 'opportunity'):
        return jsonify({"reply": "For general career questions, focus on building useful skills and practical experience. Right now, fields like software development, data analytics, cloud computing, cybersecurity, and digital marketing continue to have strong opportunities."})

    # Campus-specific prompts
    if contains('hello', 'hi', 'hey'):
        reply = f"Hello, {name}! I am your Campus Portfolio Assistant. Ask me anything about your studies, faculty, campus tasks, or simple general questions."

    elif contains('admin', 'vaibhavi', 'gosavi'):
        reply = "Admin operations are managed by Vaibhavi Gosavi. She handles portal access, system configuration, and updates to the student and faculty roster."

    elif contains('gpa', 'grade', 'performance', 'score'):
        if user and user.role == 'student':
            profile = user.student_profile
            reply = f"Your current GPA is **{profile.gpa}** in Semester {profile.semester}. Keep up the good work!"
        elif user and user.role == 'faculty':
            reply = "As a faculty member, you can view student GPA summaries in your dashboard reports and faculty tools."
        else:
            reply = "You need to log in as a student to see GPA details. Please sign in to access your academic profile."

    elif contains('project', 'portfolio', 'projects'):
        if user and user.role == 'student':
            profile = user.student_profile
            p_list = Project.query.filter_by(student_id=profile.id).all()
            if p_list:
                p_names = ", ".join([f"*{p.title}* ({p.status})" for p in p_list])
                reply = f"You have **{len(p_list)}** projects registered: {p_names}. Add or update them in your profile page."
            else:
                reply = "You currently have no projects registered. Add one from your profile page to showcase your work."
        else:
            total_p = Project.query.count()
            reply = f"There are currently **{total_p}** projects recorded in the campus portfolio system."

    elif contains('skill', 'spice', 'ability'):
        if user and user.role == 'student':
            profile = user.student_profile
            reply = f"Your registered skills are: **{profile.skills}**. These appear as your portfolio skill tags on the dashboard."
        else:
            reply = "Students list their skills here, such as Python and Flask. Faculty can use these skills to assess student portfolios."

    elif contains('attendance', 'present', 'absent', 'attendance rate'):
        if user and user.role == 'student':
            profile = user.student_profile
            atts = Attendance.query.filter_by(student_id=profile.id).all()
            p_count = sum(1 for a in atts if a.status == 'Present')
            total = len(atts)
            percent = int((p_count / total) * 100) if total > 0 else 100
            reply = f"Your attendance rate is **{percent}%** ({p_count}/{total} present). Keep your attendance strong!"
        elif user and user.role == 'faculty':
            reply = "Faculty can manage attendance from the attendance page. You can mark students present or absent there."
        else:
            reply = "Attendance information is available after you sign in as a student or faculty user."

    elif contains('event', 'happenings', 'calendar'):
        evs = Event.query.order_by(Event.date.asc()).all()
        if evs:
            ev_list = ", ".join([f"*{e.title}* on {e.date}" for e in evs[:4]])
            reply = f"Upcoming campus events: {ev_list}. Visit the events page for full details."
        else:
            reply = "No upcoming campus events are scheduled right now."

    elif contains('announcement', 'notice', 'news'):
        role_filter = 'all'
        if user:
            role_filter = user.role
        anns = Announcement.query.filter(Announcement.target_role.in_(['all', role_filter])).order_by(Announcement.date_posted.desc()).limit(3).all()
        if anns:
            ann_titles = " | ".join([f"**{a.title}**" for a in anns])
            reply = f"Latest notices: {ann_titles}. Open announcements to read them all."
        else:
            reply = "There are currently no notices for your role. Check back later for updates."

    elif contains('help', 'what can you do', 'features', 'capabilities'):
        reply = "I can answer campus-related questions like GPA, attendance, projects, announcements, and events. Use the microphone icon for voice input or type your question directly."

    elif contains('voice', 'speak', 'microphone', 'listen'):
        reply = "Voice recognition is ready. Click the microphone button, allow browser permissions, and speak your question. I will listen and respond."

    else:
        openai_reply = query_openai(message)
        if openai_reply:
            return jsonify({"reply": openai_reply})
        reply = (
            "I am the Campus AI Assistant. Ask me about your dashboard: GPA, attendance, projects, skills, events, or announcements. "
            "For example, try: 'What is my GPA?', 'Show my attendance', or 'What events are coming up?'"
        )

    return jsonify({"reply": reply})

# ----------------- Database Initialization -----------------

def ensure_default_admin_accounts():
    default_admins = [
        {
            'username': 'admin',
            'email': 'admin@campusconnect.com',
            'password': 'admin123'
        },
        {
            'username': 'Vaibhavi Gosavi',
            'email': 'vaibhavi@campusconnect.com',
            'password': 'vaibhavi123'
        }
    ]

    for admin_data in default_admins:
        existing = User.query.filter(
            (User.username == admin_data['username']) | (User.email == admin_data['email'])
        ).first()
        if not existing:
            db.session.add(User(
                username=admin_data['username'],
                email=admin_data['email'],
                password_hash=generate_password_hash(admin_data['password']),
                role='admin'
            ))
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_default_admin_accounts()
    # Runs locally on port 5000
    app.run(debug=True, port=5000)
