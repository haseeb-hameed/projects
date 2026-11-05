"""
SkillPath backend — Flask + SQLAlchemy REST API.

Provides:
  - User registration / login / logout (session-based)
  - Public skill + roadmap browsing
  - Per-user progress tracking and bookmarks
  - Admin-only CRUD for skills and modules (roadmap content)

Run locally:
    pip install -r requirements.txt
    python app.py

Default database is SQLite (skillpath.db, created automatically, zero setup).
To use MySQL instead, see the comment above SQLALCHEMY_DATABASE_URI below.
"""

import json
import math
import os
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------------
# APP + CONFIG
# --------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SKILLPATH_SECRET_KEY", "dev-secret-change-this")

# --- Database ---
# Default: SQLite, no setup required, good for local dev / the project review.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SKILLPATH_DATABASE_URL", "sqlite:///skillpath.db"
)
# To switch to MySQL later:
#   1. pip install pymysql
#   2. set SKILLPATH_DATABASE_URL to:
#      mysql+pymysql://<user>:<password>@localhost/skillpath
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Allow the React dev server (Vite, localhost:5173) to call this API with cookies.
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# --------------------------------------------------------------------------
# MODELS
# --------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)   # e.g. "python"
    name = db.Column(db.String(120), nullable=False)              # e.g. "Python Programming"
    tagline = db.Column(db.String(255), default="")
    modules = db.relationship(
        "Module", backref="skill", cascade="all, delete-orphan", order_by="Module.order_index"
    )
    certificates = db.relationship("Certificate", backref="skill", cascade="all, delete-orphan")

    def to_dict(self, include_modules=True):
        d = {"id": self.id, "key": self.key, "name": self.name, "tagline": self.tagline}
        if include_modules:
            d["modules"] = [m.to_dict() for m in self.modules]
        return d


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    title = db.Column(db.String(150), nullable=False)
    duration = db.Column(db.String(30), default="")
    description = db.Column(db.Text, default="")
    video_title = db.Column(db.String(200), default="")
    video_channel = db.Column(db.String(120), default="")
    video_url = db.Column(db.String(300), default="")
    cert_label = db.Column(db.String(120), default="")
    cert_url = db.Column(db.String(300), default="")
    subtopics = db.relationship(
        "Subtopic", backref="module", cascade="all, delete-orphan", order_by="Subtopic.order_index"
    )
    questions = db.relationship(
        "Question", backref="module", cascade="all, delete-orphan", order_by="Question.order_index"
    )
    attempts = db.relationship("Attempt", backref="module", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "order_index": self.order_index,
            "title": self.title,
            "duration": self.duration,
            "description": self.description,
            "videoTitle": self.video_title,
            "videoChannel": self.video_channel,
            "videoUrl": self.video_url,
            "certLabel": self.cert_label,
            "certUrl": self.cert_url,
            "subtopics": [s.to_dict() for s in self.subtopics],
            "questionCount": len(self.questions),
        }


class Subtopic(db.Model):
    """A smaller topic branching off a roadmap step (the side boxes in the roadmap graph)."""
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "module_id": self.module_id,
            "order_index": self.order_index,
            "title": self.title,
            "description": self.description,
        }


class Question(db.Model):
    """One question of a step's assessment: 'mcq' (4 options) or 'code' (a small program)."""
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    kind = db.Column(db.String(10), nullable=False, default="mcq")
    text = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, default="[]")      # mcq: the 4 options
    answer_index = db.Column(db.Integer, default=0)       # mcq: index of the correct option
    explanation = db.Column(db.Text, default="")
    language = db.Column(db.String(20), default="")       # code: python, sql, javascript, ...
    starter = db.Column(db.Text, default="")              # code: text pre-filled in the answer box
    solution = db.Column(db.Text, default="")             # code: model answer shown after submitting
    checks_json = db.Column(db.Text, default="[]")        # code: [{"label": ..., "pattern": regex}]

    @property
    def options(self):
        return json.loads(self.options_json or "[]")

    @property
    def checks(self):
        return json.loads(self.checks_json or "[]")

    def public_dict(self):
        """What the learner sees BEFORE submitting. Never includes answers or regex patterns."""
        d = {"id": self.id, "order_index": self.order_index, "kind": self.kind, "text": self.text}
        if self.kind == "mcq":
            d["options"] = self.options
        else:
            d["language"] = self.language
            d["starter"] = self.starter
            d["requirements"] = [c["label"] for c in self.checks]
        return d

    def admin_dict(self):
        return {
            "id": self.id, "module_id": self.module_id, "order_index": self.order_index,
            "kind": self.kind, "text": self.text, "options": self.options,
            "answer_index": self.answer_index, "explanation": self.explanation,
            "language": self.language, "starter": self.starter, "solution": self.solution,
            "checks": self.checks,
        }


class Attempt(db.Model):
    """One submitted assessment. A step counts as 'reached' once any attempt has passed."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    passed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Certificate(db.Model):
    """Issued once a user has passed the assessment of every step in a skill."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    average_percent = db.Column(db.Integer, default=0)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("user_id", "skill_id", name="uq_certificate"),)

    def to_dict(self):
        return {
            "code": self.code,
            "skillKey": self.skill.key,
            "skillName": self.skill.name,
            "holder": self.user.name,
            "issuedAt": self.issued_at.strftime("%Y-%m-%d"),
            "averagePercent": self.average_percent,
            "steps": len(self.skill.modules),
        }


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "module_id", name="uq_bookmark"),)


# --------------------------------------------------------------------------
# AUTH HELPERS
# --------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        user = User.query.get(session["user_id"])
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


# --------------------------------------------------------------------------
# AUTH ROUTES
# --------------------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or len(password) < 6:
        return jsonify({"error": "Name, email, and a password of 6+ characters are required."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists."}), 409

    user = User(name=name, email=email, role="user")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"user": user.to_dict()}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = user.id
    return jsonify({"user": user.to_dict()})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/api/me", methods=["GET"])
def me():
    user = current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": user.to_dict()})


# --------------------------------------------------------------------------
# PUBLIC SKILL / ROADMAP ROUTES
# --------------------------------------------------------------------------
@app.route("/api/skills", methods=["GET"])
def list_skills():
    skills = Skill.query.all()
    return jsonify([s.to_dict(include_modules=False) for s in skills])


@app.route("/api/skills/<key>", methods=["GET"])
def get_skill(key):
    skill = Skill.query.filter_by(key=key).first()
    if not skill:
        return jsonify({"error": "Skill not found."}), 404
    return jsonify(skill.to_dict())


# --------------------------------------------------------------------------
# PROGRESS + BOOKMARKS (logged-in users)
# --------------------------------------------------------------------------
PASS_RATIO = 0.7          # 7 correct out of 10 to pass
MAX_CODE_CHARS = 4000

_COMMENT_RULES = {
    "python": [r"#[^\n]*"],
    "bash": [r"#[^\n]*"],
    "sql": [r"--[^\n]*", r"/\*.*?\*/"],
    "javascript": [r"//[^\n]*", r"/\*.*?\*/"],
    "jsx": [r"//[^\n]*", r"/\*.*?\*/"],
    "css": [r"/\*.*?\*/"],
    "html": [r"<!--.*?-->"],
}


def pass_mark(total):
    return math.ceil(total * PASS_RATIO)


def strip_comments(code, language):
    """Comments are removed first so keywords typed inside a comment don't count."""
    for pattern in _COMMENT_RULES.get(language, []):
        code = re.sub(pattern, " ", code, flags=re.S)
    return code


def grade_question(q, answer):
    """Returns the per-question result shown to the learner after submitting."""
    if q.kind == "mcq":
        correct = isinstance(answer, int) and not isinstance(answer, bool) and answer == q.answer_index
        return {
            "id": q.id, "kind": "mcq", "correct": correct,
            "your_index": answer if isinstance(answer, int) else None,
            "correct_index": q.answer_index, "explanation": q.explanation,
        }
    code = str(answer or "")[:MAX_CODE_CHARS]
    cleaned = strip_comments(code, q.language)
    checks = []
    for c in q.checks:
        try:
            ok = re.search(c["pattern"], cleaned, re.I | re.M | re.S) is not None
        except re.error:
            ok = False
        checks.append({"label": c["label"], "ok": ok})
    correct = len(cleaned.strip()) >= 5 and bool(checks) and all(c["ok"] for c in checks)
    return {
        "id": q.id, "kind": "code", "correct": correct, "checks": checks,
        "solution": q.solution, "explanation": q.explanation, "language": q.language,
    }


def results_for(user_id):
    """{module_id: {best, total, passed, attempts}} for one user."""
    out = {}
    for a in Attempt.query.filter_by(user_id=user_id).order_by(Attempt.id).all():
        e = out.setdefault(a.module_id, {"best": 0, "total": a.total, "passed": False, "attempts": 0})
        e["attempts"] += 1
        if a.score >= e["best"]:
            e["best"], e["total"] = a.score, a.total
        e["passed"] = e["passed"] or bool(a.passed)
    return out


def maybe_issue_certificate(user, skill):
    """Issue a certificate if every assessable step of the skill is passed. -> (certificate|None, is_new)"""
    steps = [m for m in skill.modules if m.questions]
    if not steps:
        return None, False
    res = results_for(user.id)
    if not all(res.get(m.id, {}).get("passed") for m in steps):
        return None, False
    existing = Certificate.query.filter_by(user_id=user.id, skill_id=skill.id).first()
    if existing:
        return existing, False
    percents = [res[m.id]["best"] / res[m.id]["total"] * 100 for m in steps if res[m.id]["total"]]
    average = round(sum(percents) / len(percents)) if percents else 0
    while True:
        code = f"SP-{skill.key[:3].upper()}-{user.id:04d}-{secrets.token_hex(3).upper()}"
        if not Certificate.query.filter_by(code=code).first():
            break
    cert = Certificate(user_id=user.id, skill_id=skill.id, code=code, average_percent=average)
    db.session.add(cert)
    db.session.commit()
    return cert, True


# --------------------------------------------------------------------------
# ASSESSMENTS, RESULTS, CERTIFICATES (logged-in users)
# --------------------------------------------------------------------------
@app.route("/api/modules/<int:module_id>/assessment", methods=["GET"])
@login_required
def get_assessment(module_id):
    module = Module.query.get_or_404(module_id)
    if not module.questions:
        return jsonify({"error": "This step doesn't have an assessment yet."}), 404
    total = len(module.questions)
    return jsonify({
        "module": {"id": module.id, "title": module.title, "duration": module.duration, "skill": module.skill.name},
        "total": total,
        "pass_mark": pass_mark(total),
        "questions": [q.public_dict() for q in module.questions],
    })


@app.route("/api/modules/<int:module_id>/assessment", methods=["POST"])
@login_required
def submit_assessment(module_id):
    module = Module.query.get_or_404(module_id)
    questions = module.questions
    if not questions:
        return jsonify({"error": "This step doesn't have an assessment yet."}), 404
    data = request.get_json(force=True, silent=True) or {}
    answers = data.get("answers") or {}

    results = [grade_question(q, answers.get(str(q.id))) for q in questions]
    score = sum(1 for r in results if r["correct"])
    total = len(questions)
    passed = score >= pass_mark(total)

    user = current_user()
    db.session.add(Attempt(user_id=user.id, module_id=module.id, score=score, total=total, passed=passed))
    db.session.commit()

    cert, is_new = (None, False)
    if passed:
        cert, is_new = maybe_issue_certificate(user, module.skill)

    return jsonify({
        "score": score, "total": total, "pass_mark": pass_mark(total), "passed": passed,
        "results": results,
        "certificate": cert.to_dict() if cert else None,
        "certificate_is_new": is_new,
    })


@app.route("/api/results", methods=["GET"])
@login_required
def my_results():
    return jsonify(results_for(session["user_id"]))


@app.route("/api/progress", methods=["GET"])
@login_required
def get_progress():
    """Module ids the user has reached (= passed the assessment for)."""
    res = results_for(session["user_id"])
    return jsonify([mid for mid, e in res.items() if e["passed"]])


@app.route("/api/certificates", methods=["GET"])
@login_required
def my_certificates():
    rows = Certificate.query.filter_by(user_id=session["user_id"]).order_by(Certificate.issued_at).all()
    return jsonify([c.to_dict() for c in rows])


@app.route("/api/certificates/verify/<code>", methods=["GET"])
def verify_certificate(code):
    """Public: anyone holding a certificate ID can check it is genuine."""
    cert = Certificate.query.filter_by(code=code.strip().upper()).first()
    if not cert:
        return jsonify({"valid": False}), 404
    return jsonify({"valid": True, **cert.to_dict()})


@app.route("/api/bookmarks", methods=["GET"])
@login_required
def get_bookmarks():
    rows = Bookmark.query.filter_by(user_id=session["user_id"]).all()
    return jsonify([r.module_id for r in rows])


@app.route("/api/bookmarks/<int:module_id>", methods=["POST"])
@login_required
def toggle_bookmark(module_id):
    uid = session["user_id"]
    row = Bookmark.query.filter_by(user_id=uid, module_id=module_id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        return jsonify({"bookmarked": False})
    row = Bookmark(user_id=uid, module_id=module_id)
    db.session.add(row)
    db.session.commit()
    return jsonify({"bookmarked": True})


# --------------------------------------------------------------------------
# ADMIN ROUTES — manage skills & modules
# --------------------------------------------------------------------------
@app.route("/api/admin/skills", methods=["POST"])
@admin_required
def admin_create_skill():
    data = request.get_json(force=True)
    if not data.get("key") or not data.get("name"):
        return jsonify({"error": "key and name are required."}), 400
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,39}", data["key"]):
        return jsonify({"error": "The key must be 2-40 characters: lowercase letters, digits, - or _."}), 400
    if Skill.query.filter_by(key=data["key"]).first():
        return jsonify({"error": "A skill with that key already exists."}), 409
    skill = Skill(key=data["key"], name=data["name"], tagline=data.get("tagline", ""))
    db.session.add(skill)
    db.session.commit()
    return jsonify(skill.to_dict()), 201


@app.route("/api/admin/skills/<int:skill_id>", methods=["PUT"])
@admin_required
def admin_update_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    data = request.get_json(force=True)
    skill.name = data.get("name", skill.name)
    skill.tagline = data.get("tagline", skill.tagline)
    db.session.commit()
    return jsonify(skill.to_dict())


@app.route("/api/admin/skills/<int:skill_id>", methods=["DELETE"])
@admin_required
def admin_delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    db.session.delete(skill)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/modules", methods=["POST"])
@admin_required
def admin_create_module():
    data = request.get_json(force=True)
    if not data.get("skill_id") or not data.get("title"):
        return jsonify({"error": "skill_id and title are required."}), 400
    module = Module(
        skill_id=data["skill_id"],
        order_index=data.get("order_index", 0),
        title=data["title"],
        duration=data.get("duration", ""),
        description=data.get("description", ""),
        video_title=data.get("videoTitle", ""),
        video_channel=data.get("videoChannel", ""),
        video_url=data.get("videoUrl", ""),
        cert_label=data.get("certLabel", ""),
        cert_url=data.get("certUrl", ""),
    )
    db.session.add(module)
    db.session.commit()
    return jsonify(module.to_dict()), 201


@app.route("/api/admin/modules/<int:module_id>", methods=["PUT"])
@admin_required
def admin_update_module(module_id):
    module = Module.query.get_or_404(module_id)
    data = request.get_json(force=True)
    for field, attr in [
        ("title", "title"), ("duration", "duration"), ("description", "description"),
        ("videoTitle", "video_title"), ("videoChannel", "video_channel"), ("videoUrl", "video_url"),
        ("certLabel", "cert_label"), ("certUrl", "cert_url"), ("order_index", "order_index"),
    ]:
        if field in data:
            setattr(module, attr, data[field])
    db.session.commit()
    return jsonify(module.to_dict())


@app.route("/api/admin/modules/<int:module_id>", methods=["DELETE"])
@admin_required
def admin_delete_module(module_id):
    module = Module.query.get_or_404(module_id)
    db.session.delete(module)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/subtopics", methods=["POST"])
@admin_required
def admin_create_subtopic():
    data = request.get_json(force=True)
    if not data.get("module_id") or not data.get("title"):
        return jsonify({"error": "module_id and title are required."}), 400
    sub = Subtopic(
        module_id=data["module_id"],
        order_index=data.get("order_index", 0),
        title=data["title"],
        description=data.get("description", ""),
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify(sub.to_dict()), 201


@app.route("/api/admin/subtopics/<int:sub_id>", methods=["PUT"])
@admin_required
def admin_update_subtopic(sub_id):
    sub = Subtopic.query.get_or_404(sub_id)
    data = request.get_json(force=True)
    sub.title = data.get("title", sub.title)
    sub.description = data.get("description", sub.description)
    sub.order_index = data.get("order_index", sub.order_index)
    db.session.commit()
    return jsonify(sub.to_dict())


@app.route("/api/admin/subtopics/<int:sub_id>", methods=["DELETE"])
@admin_required
def admin_delete_subtopic(sub_id):
    sub = Subtopic.query.get_or_404(sub_id)
    db.session.delete(sub)
    db.session.commit()
    return jsonify({"ok": True})


def _apply_question(q, data):
    """Copies validated fields from `data` onto question `q`. Returns an error string or None."""
    kind = data.get("kind", q.kind or "mcq")
    if kind not in ("mcq", "code"):
        return "kind must be 'mcq' or 'code'."
    text = (data.get("text", q.text) or "").strip()
    if not text:
        return "text is required."
    if kind == "mcq":
        options = data.get("options", q.options)
        idx = data.get("answer_index", q.answer_index)
        if not isinstance(options, list) or len(options) < 2 or not all(isinstance(o, str) and o.strip() for o in options):
            return "An mcq needs at least 2 non-empty options."
        if not isinstance(idx, int) or not 0 <= idx < len(options):
            return "answer_index must point at one of the options."
        q.options_json = json.dumps(options)
        q.answer_index = idx
    else:
        checks = data.get("checks", q.checks)
        if not isinstance(checks, list) or not checks:
            return "A code question needs at least one check."
        for c in checks:
            if not isinstance(c, dict) or not c.get("label") or not c.get("pattern"):
                return "Each check needs a label and a pattern."
            try:
                re.compile(c["pattern"])
            except re.error:
                return f"Invalid pattern for check '{c['label']}'."
        q.checks_json = json.dumps(checks)
        q.language = data.get("language", q.language or "")
        q.starter = data.get("starter", q.starter or "")
        q.solution = data.get("solution", q.solution or "")
    q.kind = kind
    q.text = text
    q.explanation = data.get("explanation", q.explanation or "")
    q.order_index = data.get("order_index", q.order_index or 0)
    return None


@app.route("/api/admin/modules/<int:module_id>/questions", methods=["GET"])
@admin_required
def admin_list_questions(module_id):
    module = Module.query.get_or_404(module_id)
    return jsonify([q.admin_dict() for q in module.questions])


@app.route("/api/admin/questions", methods=["POST"])
@admin_required
def admin_create_question():
    data = request.get_json(force=True)
    if not Module.query.get(data.get("module_id")):
        return jsonify({"error": "module_id doesn't match a step."}), 400
    q = Question(module_id=data["module_id"])
    error = _apply_question(q, data)
    if error:
        return jsonify({"error": error}), 400
    db.session.add(q)
    db.session.commit()
    return jsonify(q.admin_dict()), 201


@app.route("/api/admin/questions/<int:qid>", methods=["PUT"])
@admin_required
def admin_update_question(qid):
    q = Question.query.get_or_404(qid)
    error = _apply_question(q, request.get_json(force=True))
    if error:
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify(q.admin_dict())


@app.route("/api/admin/questions/<int:qid>", methods=["DELETE"])
@admin_required
def admin_delete_question(qid):
    q = Question.query.get_or_404(qid)
    db.session.delete(q)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_list_users():
    """Every account, with a little activity summary for each."""
    activity = {}
    for a in Attempt.query.all():
        e = activity.setdefault(a.user_id, {"attempts": 0, "passed": set()})
        e["attempts"] += 1
        if a.passed:
            e["passed"].add(a.module_id)
    certs = {}
    for c in Certificate.query.all():
        certs[c.user_id] = certs.get(c.user_id, 0) + 1
    out = []
    for u in User.query.order_by(User.id).all():
        e = activity.get(u.id, {"attempts": 0, "passed": set()})
        d = u.to_dict()
        d.update({
            "stepsPassed": len(e["passed"]), "attempts": e["attempts"],
            "certificates": certs.get(u.id, 0),
            "joined": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
        })
        out.append(d)
    return jsonify(out)


@app.route("/api/admin/users/<int:uid>", methods=["PUT"])
@admin_required
def admin_update_user(uid):
    """Promote a learner to admin, or make an admin a learner again."""
    target = User.query.get_or_404(uid)
    role = (request.get_json(force=True, silent=True) or {}).get("role")
    if role not in ("user", "admin"):
        return jsonify({"error": "role must be 'user' or 'admin'."}), 400
    if target.id == session["user_id"] and role != "admin":
        return jsonify({"error": "You can't remove your own admin access."}), 400
    target.role = role
    db.session.commit()
    return jsonify(target.to_dict())


@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def admin_delete_user(uid):
    """Delete a learner and everything of theirs (scores, bookmarks, certificates)."""
    target = User.query.get_or_404(uid)
    if target.id == session["user_id"]:
        return jsonify({"error": "You can't delete your own account."}), 400
    if target.role == "admin":
        return jsonify({"error": "Make this account a learner first, then delete it."}), 400
    for model in (Attempt, Bookmark, Certificate):
        model.query.filter_by(user_id=target.id).delete()
    db.session.delete(target)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    """Numbers for the admin overview page."""
    users = User.query.all()
    attempts = Attempt.query.all()
    certs = Certificate.query.all()
    passed_attempts = [a for a in attempts if a.passed]
    per_skill = []
    for skill in Skill.query.order_by(Skill.id).all():
        module_ids = {m.id for m in skill.modules}
        in_skill = [a for a in attempts if a.module_id in module_ids]
        best = {}
        for a in in_skill:
            pct = a.score / a.total * 100 if a.total else 0
            best[(a.user_id, a.module_id)] = max(best.get((a.user_id, a.module_id), 0), pct)
        per_skill.append({
            "key": skill.key, "name": skill.name, "steps": len(module_ids),
            "learners": len({a.user_id for a in in_skill}),
            "certificates": sum(1 for c in certs if c.skill_id == skill.id),
            "averageBestPercent": round(sum(best.values()) / len(best)) if best else None,
        })
    names = {u.id: u.name for u in users}
    recent = []
    for a in sorted(attempts, key=lambda x: x.id, reverse=True)[:10]:
        recent.append({
            "learner": names.get(a.user_id, "(deleted user)"),
            "step": a.module.title, "skill": a.module.skill.name,
            "score": a.score, "total": a.total, "passed": bool(a.passed),
            "when": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        })
    return jsonify({
        "learners": sum(1 for u in users if u.role != "admin"),
        "admins": sum(1 for u in users if u.role == "admin"),
        "attempts": len(attempts),
        "passRatePercent": round(len(passed_attempts) / len(attempts) * 100) if attempts else None,
        "certificates": len(certs),
        "skills": Skill.query.count(),
        "steps": Module.query.count(),
        "questions": Question.query.count(),
        "perSkill": per_skill,
        "recent": recent,
    })


@app.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(force=True, silent=True) or {}
    user = current_user()
    if not user.check_password(data.get("old_password") or ""):
        return jsonify({"error": "Your current password isn't correct."}), 400
    new = data.get("new_password") or ""
    if len(new) < 6:
        return jsonify({"error": "The new password needs at least 6 characters."}), 400
    user.set_password(new)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create a default admin account the first time the DB is created.
        if not User.query.filter_by(role="admin").first():
            admin = User(name="Admin", email="admin@skillpath.com", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Created default admin login -> email: admin@skillpath.com  password: admin123")
            print("Change this password after your first login.")

    app.run(debug=True, port=5000)
