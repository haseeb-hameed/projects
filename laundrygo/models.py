from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), default="Palakkad")
    pincode = db.Column(db.String(10), default="678001")
    role = db.Column(db.String(20), default="customer")  # customer | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", backref="customer", lazy=True)

    def is_admin(self):
        return self.role == "admin"


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # kg | piece
    price = db.Column(db.Float, nullable=False)
    icon = db.Column(db.String(40), default="bi-droplet")
    is_active = db.Column(db.Boolean, default=True)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pickup_date = db.Column(db.Date, nullable=False)
    pickup_slot = db.Column(db.String(40), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    delivery_slot = db.Column(db.String(40), nullable=False)
    pickup_address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="Pending")
    subtotal = db.Column(db.Float, default=0)
    pickup_fee = db.Column(db.Float, default=0)
    express_fee = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    is_express = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.String(20), default="Pending")  # Pending | Paid
    payment_method = db.Column(db.String(20), default="COD")  # COD | Online
    notes = db.Column(db.Text)
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="order", lazy=True, cascade="all, delete-orphan"
    )
    payments = db.relationship(
        "Payment", backref="order", lazy=True, cascade="all, delete-orphan"
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    service = db.relationship("Service")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Paid")
    transaction_id = db.Column(db.String(40))
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15))
    subject = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
