SkillPath Backend — Setup
=========================

This is the Flask + database backend for SkillPath: real user accounts,
an admin role, and saved progress/bookmarks (replacing the browser-only
mock data in the website).

FOLDER CONTENTS
---------------
app.py           -> the Flask API (models, auth, admin routes)
seed_data.py      -> fills the database with the same skills/roadmaps used on the website
requirements.txt  -> Python packages needed


1. INSTALL (run once)
----------------------
Open a terminal in this folder and run:

    pip install -r requirements.txt

(If pip isn't recognized on Windows, use: python -m pip install -r requirements.txt)


2. CREATE + SEED THE DATABASE (run once)
-----------------------------------------
    python app.py

The first time this runs it will:
  - create skillpath.db (a SQLite database file, right in this folder)
  - create a default admin account:
        email:    admin@skillpath.com
        password: admin123
  - start the server at http://127.0.0.1:5000

Stop the server (Ctrl+C), then run:

    python seed_data.py

This loads the 5 skills and 23 roadmap steps (Python, Data Science, AWS,
Web Development, Cybersecurity) with the same videos/certifications the
website already shows.


3. RUN THE SERVER
------------------
    python app.py

Leave this running. The API is now live at http://127.0.0.1:5000

Quick check in your browser: http://127.0.0.1:5000/api/health
should show {"status": "ok"}


4. LOGGING IN AS ADMIN
-----------------------
Use these credentials (change the password after your first login by
adding your own "change password" logic, or directly editing the row in
skillpath.db):

    email:    admin@skillpath.com
    password: admin123

An admin account can:
  - POST   /api/admin/skills          (add a new skill)
  - PUT    /api/admin/skills/<id>     (edit a skill)
  - DELETE /api/admin/skills/<id>     (delete a skill)
  - POST   /api/admin/modules         (add a roadmap step)
  - PUT    /api/admin/modules/<id>    (edit a roadmap step)
  - DELETE /api/admin/modules/<id>    (delete a roadmap step)
  - GET    /api/admin/users           (list all registered users)

A normal user (created via /api/register) can only:
  - browse skills/roadmaps
  - mark modules as reached (progress)
  - bookmark modules
  - view/update their own account


5. SWITCHING FROM SQLITE TO MYSQL (optional, matches your deck's tech stack)
------------------------------------------------------------------------------
SQLite (the default) needs zero setup, which is why it's used here.
To use MySQL instead, once MySQL is installed and a "skillpath" database
exists:

    pip install pymysql

Then, before running app.py, set an environment variable:

  Windows (PowerShell):
    $env:SKILLPATH_DATABASE_URL = "mysql+pymysql://root:yourpassword@localhost/skillpath"

  Mac/Linux:
    export SKILLPATH_DATABASE_URL="mysql+pymysql://root:yourpassword@localhost/skillpath"

Then run app.py and seed_data.py as normal — everything else stays the same.


6. CONNECTING THE REACT WEBSITE TO THIS BACKEND
-------------------------------------------------
Right now, the website (skillpath-website.jsx) still uses its own local
mock data and does NOT call this API yet. Wiring them together means
replacing the hardcoded SKILLS object and local useState progress/
bookmarks with fetch() calls to these endpoints. That's a separate step —
ask me when you're ready and I'll do that wiring for you.


API ENDPOINT SUMMARY
---------------------
Auth:
  POST /api/register        {name, email, password}
  POST /api/login           {email, password}
  POST /api/logout
  GET  /api/me

Public:
  GET  /api/skills
  GET  /api/skills/<key>

User (must be logged in):
  GET  /api/progress
  POST /api/progress/<module_id>      (toggles complete/incomplete)
  GET  /api/bookmarks
  POST /api/bookmarks/<module_id>     (toggles bookmark)

Admin only:
  POST   /api/admin/skills
  PUT    /api/admin/skills/<id>
  DELETE /api/admin/skills/<id>
  POST   /api/admin/modules
  PUT    /api/admin/modules/<id>
  DELETE /api/admin/modules/<id>
  GET    /api/admin/users
