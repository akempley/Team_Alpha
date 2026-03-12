from extensions import db
from flask_login import UserMixin # Only if you are using Flask-Login for the Movie Archive

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    rating = db.Column(db.String(10)) # G, PG, R
    has_gore = db.Column(db.Boolean, default=False)
    has_extreme = db.Column(db.Boolean, default=False)