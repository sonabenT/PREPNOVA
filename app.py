from flask import Flask, render_template,request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import PyPDF2
import re
import os
import io
from werkzeug.security import generate_password_hash


app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_coach.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(120))
    target_role = db.Column(db.String(120))

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer)
    taken_at = db.Column(db.DateTime, server_default=db.func.now())

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback = db.Column(db.Text)
    taken_at = db.Column(db.DateTime, server_default=db.func.now())


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        db.session.add(User(username='admin', password=hashed_pw))
        db.session.commit()
        print("Default admin user created!")

@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/assessment')
def assessment():
    return render_template('assessment.html')

import random

QUESTIONS = {
    'easy': [
        {'q': 'What does HTML stand for?', 'options': ['Hyper Text Markup Language', 'High Tech Modern Language', 'Home Tool Markup Language'], 'answer': 'Hyper Text Markup Language'},
        {'q': 'What is a variable used for?', 'options': ['Storing data', 'Styling a page', 'Connecting to the internet'], 'answer': 'Storing data'},
    ],
    'medium': [
        {'q': 'What is the time complexity of binary search?', 'options': ['O(n)', 'O(log n)', 'O(n^2)'], 'answer': 'O(log n)'},
        {'q': 'What does SQL stand for?', 'options': ['Structured Query Language', 'Simple Query Language', 'Sequential Query Language'], 'answer': 'Structured Query Language'},
    ],
    'hard': [
        {'q': 'What is the main difference between a process and a thread?', 'options': ['A process has its own memory, a thread shares memory', 'They are exactly the same', 'A thread is always slower'], 'answer': 'A process has its own memory, a thread shares memory'},
        {'q': 'The CAP theorem says a distributed system can only guarantee 2 of these 3:', 'options': ['Consistency, Availability, Partition tolerance', 'Cost, Accuracy, Performance', 'Cache, API, Protocol'], 'answer': 'Consistency, Availability, Partition tolerance'},
    ]
}

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if 'difficulty' not in session:
        session['difficulty'] = 'medium'
        session['score'] = 0
        session['asked'] = 0

    feedback = None

    if request.method == 'POST':
        selected = request.form.get('answer')
        correct = request.form.get('correct_answer')
        session['asked'] += 1
        if selected == correct:
            session['score'] += 1
            feedback = "Correct! Difficulty increasing."
            if session['difficulty'] == 'easy':
                session['difficulty'] = 'medium'
            elif session['difficulty'] == 'medium':
                session['difficulty'] = 'hard'
        else:
            feedback = f"Incorrect. The right answer was: {correct}"
            if session['difficulty'] == 'hard':
                session['difficulty'] = 'medium'
            elif session['difficulty'] == 'medium':
                session['difficulty'] = 'easy'
               

    # PASTE THIS BLOCK HERE ↓
    MAX_QUESTIONS = 10
    if session['asked'] >= MAX_QUESTIONS:
        final_score = session['score']
        total = session['asked']
        session.pop('difficulty', None)
        session.pop('score', None)
        session.pop('asked', None)
        return render_template('interview_result.html', score=final_score, total=total)
    # PASTE ENDS HERE ↑

    question = random.choice(QUESTIONS[session['difficulty']])
    ...

    question = random.choice(QUESTIONS[session['difficulty']])

    return render_template('interview.html',
                            question=question,
                            difficulty=session['difficulty'],
                            score=session['score'],
                            asked=session['asked'],
                            feedback=feedback)

@app.route('/interview/reset')
def interview_reset():
    session.pop('difficulty', None)
    session.pop('score', None)
    session.pop('asked', None)
    return redirect(url_for('interview'))

@app.route('/resume', methods=['GET', 'POST'])
def resume():
    if request.method == 'POST':
        file = request.files.get('resume_file')
        if not file or file.filename == '':
            return render_template('resume.html', error="No file selected")

        if not file.filename.endswith('.pdf'):
            return render_template('resume.html', error="Please upload a PDF file")

        filepath = os.path.join('uploads', file.filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(filepath)

        text = extract_text(filepath)
        results = analyze_resume(text)

        return render_template('resume.html', results=results)

    return render_template('resume.html')


def extract_text(filepath):
    text = ""
    with open(filepath, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def analyze_resume(text):
    text_lower = text.lower()
    results = {"score": 0, "max_score": 100, "feedback": []}

    sections = ['experience', 'education', 'skills', 'projects']
    for s in sections:
        if s in text_lower:
            results["score"] += 10
            results["feedback"].append(f"✓ Found '{s.title()}' section")
        else:
            results["feedback"].append(f"✗ Missing '{s.title()}' section — consider adding it")

    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
    has_phone = bool(re.search(r'\b\d{10}\b|\(\d{3}\)\s?\d{3}-\d{4}', text))
    if has_email:
        results["score"] += 10
        results["feedback"].append("✓ Email found")
    else:
        results["feedback"].append("✗ No email detected")
    if has_phone:
        results["score"] += 10
        results["feedback"].append("✓ Phone number found")
    else:
        results["feedback"].append("✗ No phone number detected")

    action_verbs = ['developed', 'led', 'managed', 'built', 'created', 'designed', 'implemented', 'improved']
    verb_count = sum(1 for v in action_verbs if v in text_lower)
    results["score"] += min(verb_count * 5, 20)
    results["feedback"].append(f"Found {verb_count} strong action verbs")

    word_count = len(text.split())
    if 300 <= word_count <= 800:
        results["score"] += 10
        results["feedback"].append(f"✓ Good length ({word_count} words)")
    else:
        results["feedback"].append(f"⚠ Resume is {word_count} words — aim for 300–800")

    results["score"] = min(results["score"], 100)
    return results

# --- Helper Data & Dynamic Functions ---
import random

QUESTIONS = {
    "easy": [{"q": "What keyword defines a function in Python?", "options": ["func", "def", "function"], "answer": "def"}],
    "medium": [{"q": "Which structure follows FIFO?", "options": ["Stack", "Queue", "Tree"], "answer": "Queue"}],
    "hard": [{"q": "What is the primary key used for in SQL?", "options": ["Uniquely identify rows", "Speed up joins"], "answer": "Uniquely identify rows"}]
}

def generate_roadmap(results):
    roadmap = []
    if results['score'] < 50:
        roadmap.append("Week 1: Add missing core sections to resume.")
        roadmap.append("Week 2: Review foundational Python and SQL concepts.")
    else:
        roadmap.append("Week 1: Polish existing project descriptions with metrics.")
        roadmap.append("Week 2: Practice technical mock interviews.")
    return roadmap



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)