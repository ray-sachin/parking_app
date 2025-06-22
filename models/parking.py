from datetime import datetime, timedelta
from pytz import timezone, utc
from models.database import db

# Utility function to convert UTC datetime to IST
def to_ist(utc_dt):
    if utc_dt is None:
        return None
    ist = timezone('Asia/Kolkata')
    return utc_dt.replace(tzinfo=utc).astimezone(ist)


class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(20), nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with parking spots
    spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ParkingLot {self.name}>'

    def count_available_spots(self):
        """Count available parking spots"""
        return ParkingSpot.query.filter_by(lot_id=self.id, status='A').count()

    def count_occupied_spots(self):
        """Count occupied parking spots"""
        return ParkingSpot.query.filter_by(lot_id=self.id, status='O').count()

    @property
    def created_at_ist(self):
        return to_ist(self.created_at)


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(1), default='A')  # 'A' for Available, 'O' for Occupied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with reservations
    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)

    def __repr__(self):
        return f'<ParkingSpot {self.id} - Lot {self.lot_id}>'

    @property
    def created_at_ist(self):
        return to_ist(self.created_at)


class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    parking_time = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_time = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Reservation {self.id} - Spot {self.spot_id}>'

    def calculate_cost(self):
        """Calculate parking cost based on time spent"""
        if self.leaving_time and self.parking_time:
            from models.parking import ParkingLot, ParkingSpot

            # Get hours spent
            time_diff = self.leaving_time - self.parking_time
            hours_spent = time_diff.total_seconds() / 3600

            # Get hourly rate from parking lot
            spot = ParkingSpot.query.get(self.spot_id)
            lot = ParkingLot.query.get(spot.lot_id)

            # Calculate and return cost
            return round(hours_spent * lot.price, 2)
        return 0

    @property
    def parking_time_ist(self):
        return to_ist(self.parking_time)

    @property
    def leaving_time_ist(self):
        return to_ist(self.leaving_time)