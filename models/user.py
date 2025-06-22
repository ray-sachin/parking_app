from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pytz import timezone, utc
from models.database import db

# Utility function to convert UTC to IST
def to_ist(utc_dt):
    if utc_dt is None:
        return None
    ist = timezone('Asia/Kolkata')
    return utc_dt.replace(tzinfo=utc).astimezone(ist)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with reservations
    reservations = db.relationship('Reservation', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.email}>'

    @property
    def created_at_ist(self):
        return to_ist(self.created_at)

# Admin creation utility
def create_admin_user():
    """Create admin user if it doesn't exist"""
    from models.database import db

    existing_admin = User.query.filter_by(email='admin@parking.com').first()
    if existing_admin:
        return existing_admin

    admin = User(
        name='Admin',
        email='admin@parking.com',
        address='Admin Office',
        pin_code='000000',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    return admin
