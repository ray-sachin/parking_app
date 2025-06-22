from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.database import db
from models.parking import ParkingLot, ParkingSpot, Reservation
from forms.parking_forms import ReservationForm, ReleaseForm
from datetime import datetime
from sqlalchemy import func

user_bp = Blueprint('user', __name__, url_prefix='/user')

# Regular user authentication decorator
def regular_user_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_admin:
            flash('Admin cannot access user pages.', 'warning')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@user_bp.route('/dashboard')
@regular_user_required
def dashboard():
    # Get user's active reservation if any
    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id, is_active=True
    ).first()
    
    # Get parking lots with available spots
    available_lots = ParkingLot.query.filter(
        ParkingLot.id.in_(
            db.session.query(ParkingSpot.lot_id)
            .filter_by(status='A')
            .group_by(ParkingSpot.lot_id)
        )
    ).all()
    
    # Get user's recent reservations
    recent_reservations = Reservation.query.filter_by(
        user_id=current_user.id, is_active=False
    ).order_by(Reservation.parking_time.desc()).limit(5).all()
    
    return render_template('user/dashboard.html',
                           active_reservation=active_reservation,
                           available_lots=available_lots,
                           recent_reservations=recent_reservations)

@user_bp.route('/reserve', methods=['GET', 'POST'])
@regular_user_required
def reserve():
    # Check if user already has an active reservation
    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id, is_active=True
    ).first()
    
    if active_reservation:
        flash('You already have an active reservation.', 'warning')
        return redirect(url_for('user.dashboard'))
    
    form = ReservationForm()
    
    # Populate lot choices dynamically
    lots_with_spots = ParkingLot.query.filter(
        ParkingLot.id.in_(
            db.session.query(ParkingSpot.lot_id)
            .filter_by(status='A')
            .group_by(ParkingSpot.lot_id)
        )
    ).all()
    
    form.lot_id.choices = [(lot.id, f"{lot.name} - ₹{lot.price}/hr") for lot in lots_with_spots]
    
    if form.validate_on_submit():
        # Find first available spot in the selected lot
        available_spot = ParkingSpot.query.filter_by(
            lot_id=form.lot_id.data, status='A'
        ).first()
        
        if not available_spot:
            flash('No spots available in this lot.', 'danger')
            return redirect(url_for('user.reserve'))
        
        # Mark spot as occupied
        available_spot.status = 'O'
        
        # Create reservation
        reservation = Reservation(
            spot_id=available_spot.id,
            user_id=current_user.id,
            vehicle_number=form.vehicle_number.data,
            parking_time=datetime.utcnow()
        )
        
        db.session.add(reservation)
        db.session.commit()
        
        flash('Parking spot reserved successfully!', 'success')
        return redirect(url_for('user.dashboard'))
    
    return render_template('user/reserve.html', form=form)

@user_bp.route('/release', methods=['GET', 'POST'])
@regular_user_required
def release():
    # Get user's active reservation
    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id, is_active=True
    ).first()
    
    if not active_reservation:
        flash('You do not have an active reservation to release.', 'warning')
        return redirect(url_for('user.dashboard'))
    
    form = ReleaseForm()
    
    if form.validate_on_submit():
        # Mark reservation as inactive
        active_reservation.is_active = False
        active_reservation.leaving_time = datetime.utcnow()
        
        # Calculate parking cost
        lot = ParkingLot.query.join(ParkingSpot).filter(
            ParkingSpot.id == active_reservation.spot_id
        ).first()
        
        time_diff = active_reservation.leaving_time - active_reservation.parking_time
        hours = time_diff.total_seconds() / 3600
        active_reservation.parking_cost = round(hours * lot.price, 2)
        
        # Mark spot as available
        spot = ParkingSpot.query.get(active_reservation.spot_id)
        spot.status = 'A'
        
        db.session.commit()
        
        flash(f'Parking spot released successfully! Cost: ₹{active_reservation.parking_cost:.2f}', 'success')
        return redirect(url_for('user.dashboard'))
    
    # Get spot and lot info for display
    spot = ParkingSpot.query.get(active_reservation.spot_id)
    lot = ParkingLot.query.get(spot.lot_id)
    
    return render_template('user/release.html', 
                           form=form, 
                           reservation=active_reservation,
                           spot=spot,
                           lot=lot)

@user_bp.route('/history')
@regular_user_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get user's reservation history
    reservations = Reservation.query.filter_by(
        user_id=current_user.id
    ).order_by(Reservation.parking_time.desc()).paginate(page=page, per_page=per_page)
    
    # Get spot and lot info for each reservation
    reservation_details = []
    for res in reservations.items:
        spot = ParkingSpot.query.get(res.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        
        reservation_details.append({
            'reservation': res,
            'spot': spot,
            'lot': lot
        })
    
    return render_template('user/history.html', 
                           reservation_details=reservation_details,
                           pagination=reservations)

@user_bp.route('/summary')
@regular_user_required
def summary():
    # Get user's total reservations
    total_reservations = Reservation.query.filter_by(user_id=current_user.id).count()
    
    # Get user's total spending
    total_spending = db.session.query(func.sum(Reservation.parking_cost)).filter(
        Reservation.user_id == current_user.id,
        Reservation.is_active == False
    ).scalar() or 0
    
    # Get user's recent reservations by month
    monthly_data = db.session.query(
        func.strftime('%Y-%m', Reservation.parking_time).label('month'),
        func.count().label('count'),
        func.sum(Reservation.parking_cost).label('cost')
    ).filter(
        Reservation.user_id == current_user.id,
        Reservation.is_active == False
    ).group_by(
        func.strftime('%Y-%m', Reservation.parking_time)
    ).order_by(
        func.strftime('%Y-%m', Reservation.parking_time)
    ).limit(6).all()
    
    months = [data.month for data in monthly_data]
    counts = [data.count for data in monthly_data]
    costs = [float(data.cost or 0) for data in monthly_data]
    
    # Get favorite parking lots
    favorite_lots = db.session.query(
        ParkingLot.name,
        func.count().label('count')
    ).join(
        ParkingSpot, ParkingLot.id == ParkingSpot.lot_id
    ).join(
        Reservation, ParkingSpot.id == Reservation.spot_id
    ).filter(
        Reservation.user_id == current_user.id
    ).group_by(
        ParkingLot.id
    ).order_by(
        func.count().desc()
    ).limit(5).all()
    
    lot_names = [lot.name for lot in favorite_lots]
    lot_counts = [lot.count for lot in favorite_lots]
    
    return render_template('user/summary.html',
                           total_reservations=total_reservations,
                           total_spending=total_spending,
                           months=months,
                           counts=counts,
                           costs=costs,
                           lot_names=lot_names,
                           lot_counts=lot_counts)

@user_bp.route('/search', methods=['GET', 'POST'])
@regular_user_required
def search():
    query = request.args.get('query', '')
    
    if query:
        # Search for parking lots
        lots = ParkingLot.query.filter(
            (ParkingLot.name.contains(query)) |
            (ParkingLot.address.contains(query)) |
            (ParkingLot.pin_code.contains(query))
        ).all()
        
        # Get available spots count for each lot
        lot_availability = {}
        for lot in lots:
            lot_availability[lot.id] = ParkingSpot.query.filter_by(
                lot_id=lot.id, status='A'
            ).count()
        
        return render_template('user/search_results.html', 
                               query=query, 
                               lots=lots,
                               lot_availability=lot_availability)
    
    return render_template('user/search.html')