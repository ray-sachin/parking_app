from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.database import db
from models.parking import ParkingLot, ParkingSpot, Reservation
from models.user import User
from sqlalchemy import func
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Admin API authentication decorator
def admin_api_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Unauthorized access'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@api_bp.route('/parking-stats')
@admin_api_required
def parking_stats():
    """Get parking statistics for admin dashboard"""
    # Overall stats
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='A').count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    
    # Lot-wise stats
    lots = ParkingLot.query.all()
    lot_stats = []
    
    for lot in lots:
        total = ParkingSpot.query.filter_by(lot_id=lot.id).count()
        available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        
        lot_stats.append({
            'id': lot.id,
            'name': lot.name,
            'total': total,
            'available': available,
            'occupied': occupied,
            'occupancy_rate': (occupied / total * 100) if total > 0 else 0
        })
    
    return jsonify({
        'overall': {
            'total': total_spots,
            'available': available_spots,
            'occupied': occupied_spots,
            'occupancy_rate': (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        },
        'lots': lot_stats
    })

@api_bp.route('/revenue-stats')
@admin_api_required
def revenue_stats():
    """Get revenue statistics for admin dashboard"""
    # Daily revenue for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_revenue = db.session.query(
        func.date(Reservation.leaving_time).label('date'),
        func.sum(Reservation.parking_cost).label('revenue')
    ).filter(
        Reservation.leaving_time >= thirty_days_ago,
        Reservation.leaving_time.isnot(None)
    ).group_by(
        func.date(Reservation.leaving_time)
    ).all()
    
    # Convert to dictionary format
    revenue_data = [{'date': str(day.date), 'revenue': float(day.revenue)} for day in daily_revenue]
    
    # Monthly revenue summary
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', Reservation.leaving_time).label('month'),
        func.sum(Reservation.parking_cost).label('revenue')
    ).filter(
        Reservation.leaving_time.isnot(None)
    ).group_by(
        func.strftime('%Y-%m', Reservation.leaving_time)
    ).order_by(
        func.strftime('%Y-%m', Reservation.leaving_time).desc()
    ).limit(12).all()
    
    monthly_data = [{'month': month.month, 'revenue': float(month.revenue)} for month in monthly_revenue]
    
    return jsonify({
        'daily': revenue_data,
        'monthly': monthly_data
    })

@api_bp.route('/user-stats/<int:user_id>')
@login_required
def user_stats(user_id):
    """Get parking statistics for a specific user"""
    # Check permissions
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Get user's reservation history
    reservations = Reservation.query.filter_by(user_id=user_id).all()
    
    # Calculate stats
    total_reservations = len(reservations)
    completed_reservations = len([r for r in reservations if not r.is_active])
    active_reservations = len([r for r in reservations if r.is_active])
    
    total_spent = sum([r.parking_cost or 0 for r in reservations if r.parking_cost])
    avg_duration = 0
    
    if completed_reservations > 0:
        total_duration = sum([
            (r.leaving_time - r.parking_time).total_seconds() / 3600 
            for r in reservations 
            if r.leaving_time
        ])
        avg_duration = total_duration / completed_reservations
    
    return jsonify({
        'user_id': user_id,
        'total_reservations': total_reservations,
        'completed_reservations': completed_reservations,
        'active_reservations': active_reservations,
        'total_spent': total_spent,
        'avg_duration_hours': avg_duration
    })

@api_bp.route('/available-spots/<int:lot_id>')
def available_spots(lot_id):
    """Get available spots for a specific parking lot"""
    # Get the parking lot
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Get available spots
    spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').all()
    
    spot_data = [{
        'id': spot.id,
        'spot_number': spot.spot_number
    } for spot in spots]
    
    return jsonify({
        'lot_id': lot.id,
        'lot_name': lot.name,
        'available_spots': spot_data,
        'total_available': len(spot_data),
        'price_per_hour': lot.price
    })