# LaundryGo — Online Laundry Pickup & Delivery System

MCA Mini Project · APJ Abdul Kalam Technological University  
Submitted by **Muhammed Ajzel**

LaundryGo is a web application that lets customers book washing, ironing and dry-cleaning online, schedule doorstep pickup and delivery, track order status, and lets the shop manage customers, schedules and payments.

## Tech stack

| Layer | Tools |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Backend | Python 3, Flask |
| Database | SQLite (default) or MySQL |
| Auth | Flask-Login, hashed passwords (Werkzeug) |

## Features

**Customer**
- Register / login
- Book services with quantities, pickup & delivery slots
- Express (next-day) option
- Cash on delivery or simulated online payment
- Live order tracking timeline
- Cancel pending orders
- Profile management

**Admin**
- Dashboard with stats and 7-day chart
- Manage all orders and update status
- Pickup & delivery schedules by date
- Customer directory
- Payment ledger and outstanding dues
- Service catalogue CRUD
- Contact-form inbox

## Run locally

```bash
cd laundrygo
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

### Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@laundrygo.com | Admin@123 |
| Customer | demo@laundrygo.com | Demo@123 |

## Use MySQL (optional)

1. Create a database: `CREATE DATABASE laundrygo CHARACTER SET utf8mb4;`
2. Install PyMySQL (already in requirements).
3. Run with:

```bash
export DATABASE_URL="mysql+pymysql://root:YOURPASSWORD@localhost/laundrygo"
python app.py
```

On first start the tables and seed data are created automatically.

## Project structure

```
laundrygo/
  app.py              # routes, seed data
  models.py           # SQLAlchemy models
  forms.py            # WTForms
  config.py
  templates/          # Jinja2 pages
  static/css|js|img
```

## Viva talking points

1. **Problem** — urban customers do not have time to visit a laundry shop.
2. **Actors** — Customer and Admin, with role-based access.
3. **Order life cycle** — Pending → Confirmed → Pickup Scheduled → Picked Up → In Process → Ready → Out for Delivery → Delivered.
4. **Security** — password hashing, CSRF tokens, login_required, admin_required.
5. **Database** — users, services, orders, order_items, payments, contact_messages.
6. **Frontend** — Bootstrap + custom CSS, responsive sidebar, live booking total in JavaScript.
