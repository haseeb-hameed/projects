from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SubmitField,
    FloatField,
    SelectField,
    BooleanField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
    NumberRange,
    Regexp,
)


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^[6-9]\d{9}$", message="Enter a valid 10-digit Indian mobile number"),
        ],
    )
    address = TextAreaField("Address", validators=[DataRequired(), Length(min=8, max=400)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    pincode = StringField(
        "PIN code",
        validators=[DataRequired(), Regexp(r"^\d{6}$", message="Enter a 6-digit PIN code")],
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=120)])
    phone = StringField(
        "Phone",
        validators=[
            DataRequired(),
            Regexp(r"^[6-9]\d{9}$", message="Enter a valid 10-digit Indian mobile number"),
        ],
    )
    address = TextAreaField("Address", validators=[DataRequired(), Length(min=8, max=400)])
    city = StringField("City", validators=[DataRequired(), Length(max=80)])
    pincode = StringField(
        "PIN code",
        validators=[DataRequired(), Regexp(r"^\d{6}$", message="Enter a 6-digit PIN code")],
    )
    submit = SubmitField("Save changes")


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone", validators=[Optional(), Length(max=15)])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=160)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField("Send message")


class ServiceForm(FlaskForm):
    name = StringField("Service name", validators=[DataRequired(), Length(max=80)])
    description = StringField("Description", validators=[DataRequired(), Length(max=255)])
    unit = SelectField("Unit", choices=[("kg", "Per kg"), ("piece", "Per piece")])
    price = FloatField("Price (₹)", validators=[DataRequired(), NumberRange(min=1)])
    icon = StringField("Bootstrap icon class", validators=[Optional(), Length(max=40)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save service")
