"""
Populates the SkillPath database with the same skills, roadmaps, and resource
links used in the React frontend (skillpath-website.jsx), so the API and the
website show identical content.

Run once, after app.py has created the database:
    python seed_data.py
"""

import json
import random

from app import app, db, Skill, Module, Subtopic, Question
from questions_data import QUESTIONS

DATA = [
    {
        "key": "python", "name": "Python Programming",
        "tagline": "The general-purpose language that opens the door to everything else.",
        "modules": [
            dict(order_index=1, duration="WK 1–2", title="Python Foundations",
                 description="Variables, data types, loops, and functions — the building blocks you'll use in every Python program.",
                 video_title="Learn Python – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=rfscVS0vtbw",
                 cert_label="freeCodeCamp — Scientific Computing with Python",
                 cert_url="https://www.freecodecamp.org/learn/scientific-computing-with-python/"),
            dict(order_index=2, duration="WK 3", title="Data Structures & File Handling",
                 description="Lists, dictionaries, tuples, and reading/writing files — how Python organizes and stores information.",
                 video_title="Learn Python – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=rfscVS0vtbw",
                 cert_label="Kaggle Learn — Python", cert_url="https://www.kaggle.com/learn/python"),
            dict(order_index=3, duration="WK 4", title="Object-Oriented Python",
                 description="Classes, objects, and inheritance — structuring larger programs the way real projects are built.",
                 video_title="Object Oriented Programming with Python – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=Ej_02ICOIgs",
                 cert_label="freeCodeCamp — Learn", cert_url="https://www.freecodecamp.org/learn"),
            dict(order_index=4, duration="WK 5", title="Working with Libraries",
                 description="NumPy, Pandas basics, and virtual environments — the tools that make Python practical for real work.",
                 video_title="Data Analysis with Python – NumPy, Pandas, Matplotlib, Seaborn", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=r-uOLxNrNk8",
                 cert_label="Kaggle Learn — Pandas", cert_url="https://www.kaggle.com/learn/pandas"),
            dict(order_index=5, duration="WK 6", title="Build a Project",
                 description="Put it together: a small command-line or automation project you can show in an interview.",
                 video_title="Learn Python – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=rfscVS0vtbw",
                 cert_label="HP LIFE — Free Courses", cert_url="https://www.life-global.org"),
        ],
    },
    {
        "key": "datascience", "name": "Data Science",
        "tagline": "Turning raw numbers into decisions worth trusting.",
        "modules": [
            dict(order_index=1, duration="WK 1", title="Python & SQL Refresher",
                 description="The two languages every data role runs on — enough to query, clean, and explore a dataset.",
                 video_title="SQL Tutorial – Full Database Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=HXV3zeQKqGY",
                 cert_label="Kaggle Learn — Intro to SQL", cert_url="https://www.kaggle.com/learn/intro-to-sql"),
            dict(order_index=2, duration="WK 2", title="Statistics Fundamentals",
                 description="Distributions, correlation, and hypothesis testing — the reasoning behind every chart you'll make.",
                 video_title="Learn Data Science Tutorial – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=ua-CiDNNj30",
                 cert_label="IBM SkillsBuild", cert_url="https://skillsbuild.org"),
            dict(order_index=3, duration="WK 3–4", title="Data Cleaning & Visualization",
                 description="Pandas, Matplotlib, and the unglamorous work of getting messy data into a shape worth showing.",
                 video_title="Data Analysis with Python – NumPy, Pandas, Matplotlib, Seaborn", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=r-uOLxNrNk8",
                 cert_label="Kaggle Learn — Data Visualization", cert_url="https://www.kaggle.com/learn/data-visualization"),
            dict(order_index=4, duration="WK 5–6", title="Machine Learning Basics",
                 description="Regression, classification, and how a model actually learns from examples.",
                 video_title="Learn Data Science Tutorial – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=ua-CiDNNj30",
                 cert_label="Kaggle Learn — Intro to Machine Learning", cert_url="https://www.kaggle.com/learn/intro-to-machine-learning"),
            dict(order_index=5, duration="WK 7", title="Capstone Mini-Project",
                 description="One end-to-end analysis, from raw CSV to a finding you can explain in plain language.",
                 video_title="Data Analysis with Python – NumPy, Pandas, Matplotlib, Seaborn", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=r-uOLxNrNk8",
                 cert_label="IBM SkillsBuild", cert_url="https://skillsbuild.org"),
        ],
    },
    {
        "key": "aws", "name": "AWS Cloud Computing",
        "tagline": "Where most production software actually lives.",
        "modules": [
            dict(order_index=1, duration="WK 1", title="Cloud Computing Basics",
                 description="What 'the cloud' really means, and the vocabulary every AWS service builds on.",
                 video_title="AWS Certified Cloud Practitioner Training – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=3hLmDS179YE",
                 cert_label="AWS Skill Builder", cert_url="https://skillbuilder.aws"),
            dict(order_index=2, duration="WK 2", title="Core Services — EC2, S3, IAM",
                 description="Compute, storage, and access control — the three services almost every AWS project touches first.",
                 video_title="AWS Solutions Architect Associate (SAA-C03) – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=c3Cn4xYfxJY",
                 cert_label="AWS Skill Builder", cert_url="https://skillbuilder.aws"),
            dict(order_index=3, duration="WK 3", title="Databases & Networking",
                 description="RDS and VPC basics — how AWS resources talk to each other, safely.",
                 video_title="AWS Solutions Architect Associate (SAA-C03) – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=c3Cn4xYfxJY",
                 cert_label="AWS Skill Builder", cert_url="https://skillbuilder.aws"),
            dict(order_index=4, duration="WK 4", title="Cloud Practitioner Prep",
                 description="Consolidate what you've learned into exam-ready knowledge for the entry-level AWS certification.",
                 video_title="AWS Certified Cloud Practitioner Training – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=3hLmDS179YE",
                 cert_label="AWS Skill Builder", cert_url="https://skillbuilder.aws"),
        ],
    },
    {
        "key": "webdev", "name": "Web Development",
        "tagline": "Build the thing people actually click on.",
        "modules": [
            dict(order_index=1, duration="WK 1–2", title="HTML & CSS Foundations",
                 description="Structure and style — every website you've ever used is built from these two languages.",
                 video_title="Responsive Web Design – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=EfNCTL3UNVc",
                 cert_label="freeCodeCamp — Responsive Web Design",
                 cert_url="https://www.freecodecamp.org/learn/responsive-web-design/"),
            dict(order_index=2, duration="WK 3–4", title="JavaScript Essentials",
                 description="Variables, functions, and DOM manipulation — what makes a page interactive instead of static.",
                 video_title="Learn JavaScript – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=PkZNo7MFNFg",
                 cert_label="freeCodeCamp — JS Algorithms & Data Structures",
                 cert_url="https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"),
            dict(order_index=3, duration="WK 5", title="Responsive & Accessible Design",
                 description="Making a layout that works on a phone, a laptop, and a screen reader — not just your monitor.",
                 video_title="Responsive Web Design – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=EfNCTL3UNVc",
                 cert_label="freeCodeCamp — Responsive Web Design",
                 cert_url="https://www.freecodecamp.org/learn/responsive-web-design/"),
            dict(order_index=4, duration="WK 6–7", title="React Basics",
                 description="Components, props, and state — the mental model behind most modern web apps, including this one.",
                 video_title="Beginner React Tutorial", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=5OcBwxsr5zg",
                 cert_label="freeCodeCamp — Front End Libraries",
                 cert_url="https://www.freecodecamp.org/learn/front-end-development-libraries/"),
            dict(order_index=5, duration="WK 8", title="Build & Deploy a Portfolio Site",
                 description="Ship something real and put a live link on your resume.",
                 video_title="Learn JavaScript – Full Course for Beginners", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=PkZNo7MFNFg",
                 cert_label="HP LIFE — Free Courses", cert_url="https://www.life-global.org"),
        ],
    },
    {
        "key": "cyber", "name": "Cybersecurity Basics",
        "tagline": "Understand how things break before you're the one defending them.",
        "modules": [
            dict(order_index=1, duration="WK 1", title="Security Fundamentals",
                 description="Confidentiality, integrity, availability — the three ideas every security decision comes back to.",
                 video_title="Practical Ethical Hacking – Full Course", video_channel="TCM Security, via freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=3Kq1MIfTWCE",
                 cert_label="Cisco Networking Academy", cert_url="https://www.netacad.com"),
            dict(order_index=2, duration="WK 2", title="Networking Essentials",
                 description="You can't secure a network you don't understand — IP addressing, ports, and traffic basics.",
                 video_title="Computer Networking Fundamentals – Full Course", video_channel="freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=k9ZigsW9il0",
                 cert_label="Cisco Networking Academy", cert_url="https://www.netacad.com"),
            dict(order_index=3, duration="WK 3", title="Threats & Defense",
                 description="Common attack types and the everyday defenses that stop most of them.",
                 video_title="Practical Ethical Hacking – Full Course", video_channel="TCM Security, via freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=3Kq1MIfTWCE",
                 cert_label="Cisco Networking Academy", cert_url="https://www.netacad.com"),
            dict(order_index=4, duration="WK 4", title="Ethical Hacking Intro",
                 description="How penetration testers think — probing systems the same way an attacker would, with permission.",
                 video_title="Practical Ethical Hacking – Full Course", video_channel="TCM Security, via freeCodeCamp.org",
                 video_url="https://www.youtube.com/watch?v=3Kq1MIfTWCE",
                 cert_label="Cisco Networking Academy", cert_url="https://www.netacad.com"),
        ],
    },
]



# ---------------------------------------------------------------------------
# Subtopics: the smaller boxes that branch off each roadmap step.
# Keyed by skill key, then by the step's order number (1, 2, 3 ...).
# Each entry is (title, one-line description).
# ---------------------------------------------------------------------------
SUBTOPICS = {
    "python": {
        1: [("Variables & Data Types", "Storing values and knowing whether they are numbers, text, or True/False."),
            ("Strings & Input/Output", "Reading user input, printing results, and formatting text."),
            ("Conditionals", "Making decisions with if, elif, and else."),
            ("Loops", "Repeating work with for and while loops."),
            ("Functions & Scope", "Packaging code into reusable functions and understanding where variables live.")],
        2: [("Lists & Tuples", "Ordered collections — changeable (lists) and fixed (tuples)."),
            ("Dictionaries & Sets", "Key-value lookups and collections of unique items."),
            ("Reading & Writing Files", "Opening, reading, and saving text and CSV files."),
            ("Exceptions", "Handling errors gracefully with try / except.")],
        3: [("Classes & Objects", "Defining your own types with attributes and methods."),
            ("Inheritance", "Building new classes on top of existing ones."),
            ("Encapsulation & Polymorphism", "Hiding internals and letting different objects respond to the same call."),
            ("Dunder Methods", "Special methods like __init__ and __str__ that customise behaviour.")],
        4: [("NumPy Arrays", "Fast numerical arrays and vectorised maths."),
            ("Pandas DataFrames", "Table-style data you can filter, group, and summarise."),
            ("pip & Virtual Environments", "Installing packages without breaking other projects."),
            ("Calling APIs with requests", "Fetching live data from web services.")],
        5: [("Plan the Project", "Pick a small, finishable idea and list what it must do."),
            ("Structure Your Code", "Split the work into modules and functions."),
            ("Add Tests", "Check your own code automatically with a few simple tests."),
            ("Publish on GitHub", "Write a README and share the finished project.")],
    },
    "datascience": {
        1: [("SELECT & Filtering", "Pulling the rows and columns you need with WHERE."),
            ("Joins", "Combining data from several tables."),
            ("Aggregation & GROUP BY", "Counting, summing, and averaging by category."),
            ("Python for Data", "The loops, functions, and data structures analysis code relies on.")],
        2: [("Descriptive Statistics", "Mean, median, spread — summarising a dataset in a few numbers."),
            ("Probability Basics", "How likely events are and how probabilities combine."),
            ("Distributions", "The shapes data tends to take, such as the normal distribution."),
            ("Hypothesis Testing", "Deciding whether a result is real or just chance."),
            ("Correlation", "Measuring how two variables move together.")],
        3: [("Handling Missing Values", "Deciding whether to drop, fill, or flag gaps."),
            ("Outliers & Duplicates", "Spotting and treating values that distort results."),
            ("Matplotlib Basics", "Building line, bar, and scatter charts."),
            ("Seaborn Charts", "Cleaner statistical plots with less code.")],
        4: [("Supervised vs Unsupervised", "Learning from labelled examples versus finding structure on your own."),
            ("Regression & Classification", "Predicting numbers versus predicting categories."),
            ("Train / Test Split", "Keeping data aside to test honestly."),
            ("Evaluation Metrics", "Accuracy, precision, recall, and when each matters."),
            ("Overfitting", "When a model memorises instead of learning.")],
        5: [("Pick a Dataset", "Choose real data you care about."),
            ("Clean & Explore (EDA)", "Understand the data before modelling it."),
            ("Build a Model", "Train, test, and improve a first model."),
            ("Present Your Findings", "Explain the result in plain language.")],
    },
    "aws": {
        1: [("Service Models: IaaS, PaaS, SaaS", "How much the provider manages for you."),
            ("Regions & Availability Zones", "Where AWS runs and how it stays available."),
            ("Shared Responsibility Model", "What AWS secures versus what you secure."),
            ("Pricing & Free Tier", "How you are billed and how to learn for free.")],
        2: [("EC2 Instances", "Virtual servers you can launch in minutes."),
            ("S3 Buckets", "Storing files and static websites."),
            ("IAM Users & Roles", "Controlling who can do what."),
            ("Security Groups", "Virtual firewalls around your resources.")],
        3: [("RDS", "Managed relational databases."),
            ("DynamoDB", "A managed NoSQL key-value database."),
            ("VPC & Subnets", "Your private network inside AWS."),
            ("Load Balancing", "Spreading traffic across several servers.")],
        4: [("Cloud Concepts", "The foundations the exam starts with."),
            ("Security & Compliance", "Protecting accounts, data, and meeting rules."),
            ("Billing & Support Plans", "Cost tools and support tiers."),
            ("Practice Exams", "Testing yourself under exam conditions.")],
    },
    "webdev": {
        1: [("Semantic HTML", "Using the right tags so pages have meaning and structure."),
            ("Forms & Inputs", "Collecting information from users."),
            ("Selectors & the Box Model", "Targeting elements and understanding spacing."),
            ("Flexbox", "One-dimensional layouts that adapt."),
            ("CSS Grid", "Two-dimensional page layouts.")],
        2: [("Variables & Types", "Storing and labelling data in JavaScript."),
            ("Functions & Arrays", "Reusable logic and working with lists."),
            ("DOM Manipulation", "Changing the page from code."),
            ("Events", "Reacting to clicks, typing, and scrolling."),
            ("Fetch & Promises", "Loading data from a server without reloading the page.")],
        3: [("Media Queries", "Changing styles by screen size."),
            ("Mobile-First Design", "Starting small and growing up."),
            ("ARIA & Semantic Roles", "Helping screen readers understand your page."),
            ("Contrast & Keyboard Navigation", "Making pages usable for everyone.")],
        4: [("Components & JSX", "Building a page out of reusable pieces."),
            ("Props", "Passing data into components."),
            ("State & useState", "Remembering values that change."),
            ("Effects & useEffect", "Running code when something changes, like fetching data."),
            ("Lists & Forms", "Rendering collections and handling input.")],
        5: [("Git & GitHub", "Tracking changes and sharing code."),
            ("Portfolio Layout", "Deciding what to show and how."),
            ("Hosting", "Publishing on GitHub Pages or Netlify."),
            ("Domain & SEO Basics", "Making the site easy to find.")],
    },
    "cyber": {
        1: [("The CIA Triad", "Confidentiality, integrity, availability."),
            ("Threats, Vulnerabilities & Risk", "How weaknesses and attackers combine into risk."),
            ("Authentication & Passwords", "Proving who you are, and doing it safely."),
            ("Encryption Basics", "Scrambling data so only the right people read it.")],
        2: [("IP Addressing & Subnets", "How devices are identified on a network."),
            ("TCP, UDP & Ports", "How data is delivered and which doors are open."),
            ("DNS & HTTP", "How names resolve and how the web talks."),
            ("Firewalls", "Filtering traffic at the edge.")],
        3: [("Malware & Phishing", "The most common ways people get compromised."),
            ("Network Attacks", "Denial of service and man-in-the-middle."),
            ("Web Attacks", "SQL injection and cross-site scripting."),
            ("Defense in Depth", "Layering protections so one failure is not fatal.")],
        4: [("Reconnaissance", "Gathering information about a target, with permission."),
            ("Scanning & Enumeration", "Finding open services and users."),
            ("Exploitation Basics", "Safely proving a weakness is real."),
            ("Reporting & Legal Boundaries", "Documenting findings and staying within scope.")],
    },
}


def add_questions(module, skill_key, step_number):
    """Adds the 10 assessment questions (9 multiple-choice + 1 program) for one step."""
    bank = QUESTIONS.get(skill_key, {}).get(step_number)
    if not bank:
        return
    # Spread the correct answer evenly over positions A-D (shuffled, but the same every run).
    rng = random.Random(f"{skill_key}-{step_number}")
    targets = ([0, 1, 2, 3] * 3)[: len(bank["mcq"]) - 1] + [step_number % 4]
    rng.shuffle(targets)
    for i, (text, correct, wrong, explanation) in enumerate(bank["mcq"], start=1):
        options = list(wrong)
        rng.shuffle(options)
        options.insert(targets[i - 1], correct)
        db.session.add(Question(
            module_id=module.id, order_index=i, kind="mcq", text=text,
            options_json=json.dumps(options), answer_index=targets[i - 1], explanation=explanation,
        ))
    c = bank["code"]
    db.session.add(Question(
        module_id=module.id, order_index=len(bank["mcq"]) + 1, kind="code", text=c["prompt"],
        language=c["language"], starter=c["starter"], solution=c["solution"], explanation=c["explanation"],
        checks_json=json.dumps([{"label": label, "pattern": pattern} for label, pattern in c["checks"]]),
    ))


def seed():
    """Creates anything that is missing. Safe to run again on an existing database:
    it skips skills/steps that already exist and only adds missing subtopics."""
    with app.app_context():
        db.create_all()
        for skill_data in DATA:
            skill = Skill.query.filter_by(key=skill_data["key"]).first()
            if skill is None:
                skill = Skill(key=skill_data["key"], name=skill_data["name"], tagline=skill_data["tagline"])
                db.session.add(skill)
                db.session.flush()
                print(f"Added '{skill_data['key']}' with {len(skill_data['modules'])} modules.")
            else:
                print(f"'{skill_data['key']}' already exists — checking for missing parts.")

            existing = {m.title: m for m in skill.modules}
            for m in skill_data["modules"]:
                module = existing.get(m["title"])
                if module is None:
                    module = Module(skill_id=skill.id, **m)
                    db.session.add(module)
                    db.session.flush()
                if not module.subtopics:
                    for i, (title, desc) in enumerate(SUBTOPICS.get(skill.key, {}).get(m["order_index"], []), start=1):
                        db.session.add(Subtopic(module_id=module.id, order_index=i, title=title, description=desc))
                if not module.questions:
                    add_questions(module, skill.key, m["order_index"])
        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
