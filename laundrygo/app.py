from datetime import datetime, date, timedelta
from functools import wraps
import random
import string

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from config import Config
from models import db, User, Service, Order, OrderItem, Payment, ContactMessage
from forms import RegisterForm, LoginForm, ProfileForm, ContactForm, ServiceForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

SLOTS = [
    "8:00 AM – 10:00 AM",
    "10:00 AM – 12:00 PM",
    "12:00 PM – 2:00 PM",
    "2:00 PM – 4:00 PM",
    "4:00 PM – 6:00 PM",
    "6:00 PM – 8:00 PM",
]

STATUSES = [
    "Pending",
    "Confirmed",
    "Pickup Scheduled",
    "Picked Up",
    "In Process",
    "Ready",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]

FREE_PICKUP_MIN = 250
PICKUP_FEE = 40
EXPRESS_FEE = 80


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def generate_order_no():
    stamp = datetime.now().strftime("%y%m%d")
    last = Order.query.order_by(Order.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"LG{stamp}{n:04d}"


def txn_id():
    return "TXN" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    services = Service.query.filter_by(is_active=True).all()
    return render_template("index.html", services=services)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services_page():
    services = Service.query.filter_by(is_active=True).all()
    return render_template("services.html", services=services)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=(form.phone.data or "").strip(),
            subject=form.subject.data.strip(),
            message=form.message.data.strip(),
        )
        db.session.add(msg)
        db.session.commit()
        flash("Thanks! We received your message and will reply shortly.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html", form=form)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("register.html", form=form)
        user = User(
            name=form.name.data.strip(),
            email=email,
            phone=form.phone.data.strip(),
            password_hash=generate_password_hash(form.password.data),
            address=form.address.data.strip(),
            city=form.city.data.strip(),
            pincode=form.pincode.data.strip(),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to LaundryGo. Book your first pickup!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard" if current_user.is_admin() else "dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash(f"Welcome back, {user.name.split()[0]}!", "success")
            nxt = request.args.get("next")
            if nxt:
                return redirect(nxt)
            return redirect(url_for("admin_dashboard" if user.is_admin() else "dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for("admin_dashboard"))
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .limit(6)
        .all()
    )
    total = Order.query.filter_by(user_id=current_user.id).count()
    active = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status.notin_(["Delivered", "Cancelled"]),
    ).count()
    spent = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.user_id == current_user.id, Order.status != "Cancelled")
        .scalar()
    )
    return render_template(
        "customer/dashboard.html",
        orders=orders,
        total=total,
        active=active,
        spent=spent,
    )


@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    if current_user.is_admin():
        return redirect(url_for("admin_dashboard"))
    services = Service.query.filter_by(is_active=True).all()
    today = date.today().isoformat()
    if request.method == "POST":
        items = []
        subtotal = 0.0
        for svc in services:
            raw = request.form.get(f"qty_{svc.id}", "0").strip()
            try:
                qty = float(raw or 0)
            except ValueError:
                qty = 0
            if qty > 0:
                line = round(qty * svc.price, 2)
                items.append((svc, qty, line))
                subtotal += line
        if not items:
            flash("Please add at least one service.", "warning")
            return render_template(
                "customer/book.html",
                services=services,
                slots=SLOTS,
                today=today,
            )

        pickup_date_s = request.form.get("pickup_date")
        delivery_date_s = request.form.get("delivery_date")
        pickup_slot = request.form.get("pickup_slot")
        delivery_slot = request.form.get("delivery_slot")
        address = (request.form.get("address") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        is_express = request.form.get("is_express") == "on"
        method = request.form.get("payment_method") or "COD"

        try:
            pickup_d = datetime.strptime(pickup_date_s, "%Y-%m-%d").date()
            delivery_d = datetime.strptime(delivery_date_s, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Please choose valid pickup and delivery dates.", "danger")
            return render_template(
                "customer/book.html", services=services, slots=SLOTS, today=today
            )

        if pickup_d < date.today():
            flash("Pickup date cannot be in the past.", "danger")
            return render_template(
                "customer/book.html", services=services, slots=SLOTS, today=today
            )
        min_gap = 1 if is_express else 2
        if delivery_d < pickup_d + timedelta(days=min_gap):
            flash(
                f"Delivery must be at least {min_gap} day(s) after pickup.",
                "danger",
            )
            return render_template(
                "customer/book.html", services=services, slots=SLOTS, today=today
            )
        if not address:
            flash("Pickup address is required.", "danger")
            return render_template(
                "customer/book.html", services=services, slots=SLOTS, today=today
            )
        if pickup_slot not in SLOTS or delivery_slot not in SLOTS:
            flash("Please choose valid time slots.", "danger")
            return render_template(
                "customer/book.html", services=services, slots=SLOTS, today=today
            )

        pickup_fee = 0 if subtotal >= FREE_PICKUP_MIN else PICKUP_FEE
        express_fee = EXPRESS_FEE if is_express else 0
        total = round(subtotal + pickup_fee + express_fee, 2)

        order = Order(
            order_no=generate_order_no(),
            user_id=current_user.id,
            pickup_date=pickup_d,
            pickup_slot=pickup_slot,
            delivery_date=delivery_d,
            delivery_slot=delivery_slot,
            pickup_address=address,
            status="Pending",
            subtotal=round(subtotal, 2),
            pickup_fee=pickup_fee,
            express_fee=express_fee,
            total_amount=total,
            is_express=is_express,
            payment_status="Pending",
            payment_method=method,
            notes=notes,
        )
        db.session.add(order)
        db.session.flush()
        for svc, qty, line in items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    service_id=svc.id,
                    quantity=qty,
                    unit_price=svc.price,
                    subtotal=line,
                )
            )
        db.session.commit()

        if method == "Online":
            return redirect(url_for("pay", order_id=order.id))
        flash(f"Order {order.order_no} placed. Pay cash on delivery.", "success")
        return redirect(url_for("order_detail", order_id=order.id))

    return render_template(
        "customer/book.html",
        services=services,
        slots=SLOTS,
        today=today,
        free_min=FREE_PICKUP_MIN,
        pickup_fee=PICKUP_FEE,
        express_fee=EXPRESS_FEE,
    )


@app.route("/pay/<int:order_id>", methods=["GET", "POST"])
@login_required
def pay(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    if order.payment_status == "Paid":
        flash("This order is already paid.", "info")
        return redirect(url_for("order_detail", order_id=order.id))
    if request.method == "POST":
        order.payment_status = "Paid"
        order.payment_method = "Online"
        db.session.add(
            Payment(
                order_id=order.id,
                amount=order.total_amount,
                method="Online",
                status="Paid",
                transaction_id=txn_id(),
            )
        )
        db.session.commit()
        flash("Payment successful. Your pickup is being scheduled.", "success")
        return redirect(url_for("order_detail", order_id=order.id))
    return render_template("customer/pay.html", order=order)


@app.route("/orders")
@login_required
def my_orders():
    if current_user.is_admin():
        return redirect(url_for("admin_orders"))
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Order.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(Order.order_no.ilike(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template(
        "customer/orders.html", orders=orders, q=q, status=status, statuses=STATUSES
    )


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin():
        abort(403)
    return render_template(
        "customer/order_detail.html", order=order, statuses=STATUSES
    )


@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    if order.status not in ("Pending", "Confirmed"):
        flash("This order can no longer be cancelled.", "warning")
        return redirect(url_for("order_detail", order_id=order.id))
    order.status = "Cancelled"
    db.session.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("order_detail", order_id=order.id))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.is_admin():
        return redirect(url_for("admin_dashboard"))
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip()
        current_user.address = form.address.data.strip()
        current_user.city = form.city.data.strip()
        current_user.pincode = form.pincode.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("customer/profile.html", form=form)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    total_orders = Order.query.count()
    total_customers = User.query.filter_by(role="customer").count()
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status != "Cancelled")
        .scalar()
    )
    pending = Order.query.filter(Order.status.in_(["Pending", "Confirmed"])).count()
    today = date.today()
    pickups_today = Order.query.filter(
        Order.pickup_date == today, Order.status.notin_(["Cancelled", "Delivered"])
    ).count()
    deliveries_today = Order.query.filter(
        Order.delivery_date == today, Order.status.notin_(["Cancelled"])
    ).count()
    unread = ContactMessage.query.filter_by(is_read=False).count()

    # last 7 days chart
    labels, counts, amounts = [], [], []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        day_q = Order.query.filter(func.date(Order.created_at) == d)
        counts.append(day_q.count())
        amounts.append(
            float(
                db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
                .filter(func.date(Order.created_at) == d, Order.status != "Cancelled")
                .scalar()
            )
        )

    recent = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    status_counts = {
        s: Order.query.filter_by(status=s).count() for s in STATUSES if s != "Cancelled"
    }
    return render_template(
        "admin/dashboard.html",
        total_orders=total_orders,
        total_customers=total_customers,
        revenue=revenue,
        pending=pending,
        pickups_today=pickups_today,
        deliveries_today=deliveries_today,
        unread=unread,
        labels=labels,
        counts=counts,
        amounts=amounts,
        recent=recent,
        status_counts=status_counts,
    )


@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    pay = request.args.get("pay", "").strip()
    query = Order.query
    if q:
        query = query.join(User).filter(
            db.or_(
                Order.order_no.ilike(f"%{q}%"),
                User.name.ilike(f"%{q}%"),
                User.phone.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(Order.status == status)
    if pay:
        query = query.filter(Order.payment_status == pay)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template(
        "admin/orders.html",
        orders=orders,
        q=q,
        status=status,
        pay=pay,
        statuses=STATUSES,
    )


@app.route("/admin/orders/<int:order_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == "POST":
        new_status = request.form.get("status")
        admin_note = (request.form.get("admin_note") or "").strip()
        if new_status in STATUSES:
            order.status = new_status
        order.admin_note = admin_note
        if request.form.get("mark_paid") == "1" and order.payment_status != "Paid":
            order.payment_status = "Paid"
            db.session.add(
                Payment(
                    order_id=order.id,
                    amount=order.total_amount,
                    method=order.payment_method,
                    status="Paid",
                    transaction_id=txn_id(),
                )
            )
        db.session.commit()
        flash("Order updated.", "success")
        return redirect(url_for("admin_order_detail", order_id=order.id))
    return render_template(
        "admin/order_detail.html", order=order, statuses=STATUSES
    )


@app.route("/admin/customers")
@login_required
@admin_required
def admin_customers():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="customer")
    if q:
        query = query.filter(
            db.or_(
                User.name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.phone.ilike(f"%{q}%"),
            )
        )
    customers = query.order_by(User.created_at.desc()).all()
    return render_template("admin/customers.html", customers=customers, q=q)


@app.route("/admin/schedules")
@login_required
@admin_required
def admin_schedules():
    day_s = request.args.get("day") or date.today().isoformat()
    try:
        day = datetime.strptime(day_s, "%Y-%m-%d").date()
    except ValueError:
        day = date.today()
    pickups = (
        Order.query.filter(
            Order.pickup_date == day, Order.status.notin_(["Cancelled", "Delivered"])
        )
        .order_by(Order.pickup_slot)
        .all()
    )
    deliveries = (
        Order.query.filter(
            Order.delivery_date == day, Order.status.notin_(["Cancelled"])
        )
        .order_by(Order.delivery_slot)
        .all()
    )
    return render_template(
        "admin/schedules.html",
        day=day,
        pickups=pickups,
        deliveries=deliveries,
        yesterday=(day - timedelta(days=1)).isoformat(),
        tomorrow=(day + timedelta(days=1)).isoformat(),
    )


@app.route("/admin/payments")
@login_required
@admin_required
def admin_payments():
    payments = Payment.query.order_by(Payment.paid_at.desc()).all()
    pending_orders = Order.query.filter(
        Order.payment_status == "Pending", Order.status != "Cancelled"
    ).order_by(Order.created_at.desc()).all()
    collected = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    )
    return render_template(
        "admin/payments.html",
        payments=payments,
        pending_orders=pending_orders,
        collected=collected,
    )


@app.route("/admin/services", methods=["GET", "POST"])
@login_required
@admin_required
def admin_services():
    form = ServiceForm()
    if form.validate_on_submit():
        svc = Service(
            name=form.name.data.strip(),
            description=form.description.data.strip(),
            unit=form.unit.data,
            price=form.price.data,
            icon=(form.icon.data or "bi-droplet").strip(),
            is_active=bool(form.is_active.data),
        )
        db.session.add(svc)
        db.session.commit()
        flash("Service added.", "success")
        return redirect(url_for("admin_services"))
    services = Service.query.order_by(Service.id).all()
    return render_template("admin/services.html", services=services, form=form)


@app.route("/admin/services/<int:service_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_service(service_id):
    svc = Service.query.get_or_404(service_id)
    svc.is_active = not svc.is_active
    db.session.commit()
    flash(f"{svc.name} is now {'active' if svc.is_active else 'hidden'}.", "info")
    return redirect(url_for("admin_services"))


@app.route("/admin/services/<int:service_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit_service(service_id):
    svc = Service.query.get_or_404(service_id)
    svc.name = request.form.get("name", svc.name).strip()
    svc.description = request.form.get("description", svc.description).strip()
    svc.unit = request.form.get("unit", svc.unit)
    try:
        svc.price = float(request.form.get("price", svc.price))
    except ValueError:
        pass
    svc.icon = request.form.get("icon", svc.icon).strip()
    db.session.commit()
    flash("Service updated.", "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/messages")
@login_required
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/messages/<int:msg_id>/read", methods=["POST"])
@login_required
@admin_required
def mark_message(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for("admin_messages"))


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(_e):
    return render_template("404.html"), 403


@app.context_processor
def inject_globals():
    unread = 0
    if current_user.is_authenticated and current_user.is_admin():
        unread = ContactMessage.query.filter_by(is_read=False).count()
    return {"STATUSES": STATUSES, "unread_messages": unread}


def seed_data():
    if Service.query.first():
        return

    services = [
        ("Wash & Fold", "Everyday laundry, washed, dried and neatly folded.", "kg", 70, "bi-droplet"),
        ("Wash & Iron", "Wash plus crisp professional pressing.", "kg", 95, "bi-shirt"),
        ("Dry Cleaning", "Gentle solvent care for suits, silk and formals.", "piece", 140, "bi-award"),
        ("Ironing Only", "Steam press for shirts, kurtas and trousers.", "piece", 15, "bi-lightning"),
        ("Bedding & Curtains", "Bedsheets, duvet covers and heavy drapes.", "kg", 110, "bi-house-heart"),
        ("Premium Care", "Enzyme wash, fabric conditioner and hand finish.", "kg", 160, "bi-gem"),
        ("Stain Treatment", "Spot treatment before the main wash.", "piece", 50, "bi-stars"),
        ("Shoes & Bags", "Sneaker and fabric bag refresh.", "piece", 180, "bi-bag"),
    ]
    for name, desc, unit, price, icon in services:
        db.session.add(
            Service(name=name, description=desc, unit=unit, price=price, icon=icon)
        )

    admin = User(
        name="LaundryGo Admin",
        email="admin@laundrygo.com",
        phone="9876543210",
        password_hash=generate_password_hash("Admin@123"),
        address="LaundryGo Hub, Stadium Bypass, Palakkad",
        city="Palakkad",
        pincode="678001",
        role="admin",
    )
    demo = User(
        name="Muhammed Ajzel",
        email="demo@laundrygo.com",
        phone="9895001122",
        password_hash=generate_password_hash("Demo@123"),
        address="12/44, Near Fort Maidan, Palakkad",
        city="Palakkad",
        pincode="678001",
        role="customer",
    )
    anjali = User(
        name="Anjali Menon",
        email="anjali@example.com",
        phone="9847012345",
        password_hash=generate_password_hash("Demo@123"),
        address="House No. 8, Kalpathy, Palakkad",
        city="Palakkad",
        pincode="678003",
        role="customer",
    )
    db.session.add_all([admin, demo, anjali])
    db.session.flush()

    svcs = Service.query.all()
    today = date.today()

    def make_order(user, status, pay_status, method, pickup_off, delivery_off, express=False, paid=False):
        sub = 0
        chosen = svcs[:3]
        order = Order(
            order_no=generate_order_no(),
            user_id=user.id,
            pickup_date=today + timedelta(days=pickup_off),
            pickup_slot=SLOTS[1],
            delivery_date=today + timedelta(days=delivery_off),
            delivery_slot=SLOTS[3],
            pickup_address=f"{user.address}, {user.city} {user.pincode}",
            status=status,
            is_express=express,
            payment_status=pay_status,
            payment_method=method,
            notes="Please ring the bell.",
        )
        db.session.add(order)
        db.session.flush()
        for i, svc in enumerate(chosen):
            qty = 2 if svc.unit == "kg" else 3
            line = qty * svc.price
            sub += line
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    service_id=svc.id,
                    quantity=qty,
                    unit_price=svc.price,
                    subtotal=line,
                )
            )
        order.subtotal = sub
        order.pickup_fee = 0 if sub >= FREE_PICKUP_MIN else PICKUP_FEE
        order.express_fee = EXPRESS_FEE if express else 0
        order.total_amount = order.subtotal + order.pickup_fee + order.express_fee
        if paid:
            db.session.add(
                Payment(
                    order_id=order.id,
                    amount=order.total_amount,
                    method=method,
                    status="Paid",
                    transaction_id=txn_id(),
                )
            )
        # stagger created_at
        order.created_at = datetime.utcnow() - timedelta(days=abs(pickup_off) + i)

    make_order(demo, "In Process", "Paid", "Online", 0, 2, paid=True)
    make_order(demo, "Delivered", "Paid", "COD", -5, -3, paid=True)
    make_order(demo, "Pending", "Pending", "COD", 1, 3)
    make_order(anjali, "Pickup Scheduled", "Paid", "Online", 0, 2, express=True, paid=True)
    make_order(anjali, "Out for Delivery", "Pending", "COD", -1, 0)

    db.session.add(
        ContactMessage(
            name="Rahul Krishnan",
            email="rahul@example.com",
            phone="9745011122",
            subject="Corporate tie-up",
            message="We run a 20-room PG in Palakkad. Can LaundryGo offer a weekly bulk plan?",
        )
    )
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
