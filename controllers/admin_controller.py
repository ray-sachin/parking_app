from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.database import db
from models.user import User
from models.parking import ParkingLot, ParkingSpot, Reservation
from forms.parking_forms import ParkingLotForm
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin authentication decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Get parking lots data
    parking_lots = ParkingLot.query.all()
    
    # Get overall stats
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='A').count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    total_users = User.query.filter_by(is_admin=False).count()
    active_reservations = Reservation.query.filter_by(is_active=True).count()
    
    return render_template('admin/dashboard.html', 
                           parking_lots=parking_lots,
                           total_lots=total_lots,
                           total_spots=total_spots,
                           available_spots=available_spots,
                           occupied_spots=occupied_spots,
                           total_users=total_users,
                           active_reservations=active_reservations)

@admin_bp.route('/parking-lots')
@admin_required
def parking_lots():
    lots = ParkingLot.query.all()
    return render_template('admin/parking_lots.html', lots=lots)

@admin_bp.route('/parking-lot/new', methods=['GET', 'POST'])
@admin_required
def new_parking_lot():
    form = ParkingLotForm()
    if form.validate_on_submit():
        lot = ParkingLot(
            name=form.name.data,
            price=form.price.data,
            address=form.address.data,
            pin_code=form.pin_code.data,
            max_spots=form.max_spots.data
        )
        db.session.add(lot)
        db.session.flush()  # To get the lot id
        
        # Create parking spots
        for i in range(1, form.max_spots.data + 1):
            spot = ParkingSpot(lot_id=lot.id, spot_number=i)
            db.session.add(spot)
        
        db.session.commit()
        flash('Parking lot created successfully!', 'success')
        return redirect(url_for('admin.parking_lots'))
    
    return render_template('admin/parking_lot_form.html', form=form, title='New Parking Lot')

@admin_bp.route('/parking-lot/<int:lot_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = ParkingLotForm(obj=lot)
    
    if form.validate_on_submit():
        # Update basic lot info
        lot.name = form.name.data
        lot.price = form.price.data
        lot.address = form.address.data
        lot.pin_code = form.pin_code.data
        
        # Handle spot count changes
        current_spots = ParkingSpot.query.filter_by(lot_id=lot_id).count()
        new_spots = form.max_spots.data
        
        if new_spots > current_spots:
            # Add new spots
            for i in range(current_spots + 1, new_spots + 1):
                spot = ParkingSpot(lot_id=lot_id, spot_number=i)
                db.session.add(spot)
        elif new_spots < current_spots:
            # Remove excess spots if they're not occupied
            spots_to_remove = ParkingSpot.query.filter_by(
                lot_id=lot_id, status='A'
            ).order_by(ParkingSpot.spot_number.desc()).limit(current_spots - new_spots).all()
            
            if len(spots_to_remove) < (current_spots - new_spots):
                flash('Cannot reduce spots as some are currently occupied.', 'danger')
                return render_template('admin/parking_lot_form.html', form=form, title='Edit Parking Lot')
            
            for spot in spots_to_remove:
                db.session.delete(spot)
        
        lot.max_spots = new_spots
        db.session.commit()
        flash('Parking lot updated successfully!', 'success')
        return redirect(url_for('admin.parking_lots'))
    
    return render_template('admin/parking_lot_form.html', form=form, title='Edit Parking Lot')

@admin_bp.route('/parking-lot/<int:lot_id>/delete', methods=['POST'])
@admin_required
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Check if any spots are occupied
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()
    if occupied_spots > 0:
        flash('Cannot delete parking lot as it has occupied spots.', 'danger')
        return redirect(url_for('admin.parking_lots'))
    
    db.session.delete(lot)  # This will also delete associated spots due to cascade
    db.session.commit()
    flash('Parking lot deleted successfully!', 'success')
    return redirect(url_for('admin.parking_lots'))

@admin_bp.route('/parking-spots/<int:lot_id>')
@admin_required
def parking_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).order_by(ParkingSpot.spot_number).all()
    
    # Get active reservations for occupied spots
    active_reservations = {}
    for spot in spots:
        if spot.status == 'O':
            reservation = Reservation.query.filter_by(spot_id=spot.id, is_active=True).first()
            if reservation:
                active_reservations[spot.id] = reservation
    
    return render_template('admin/parking_spots.html', lot=lot, spots=spots, reservations=active_reservations)

@admin_bp.route('/users')
@admin_required
def users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/summary')
@admin_required
def summary():
    # Get parking lots
    parking_lots = ParkingLot.query.all()
    
    # Overall stats
    total_spots = ParkingSpot.query.count()
    available_spots = ParkingSpot.query.filter_by(status='A').count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()
    
    # Revenue stats for last 30 days
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
    
    # Convert to format for charts
    dates = [str(r.date) for r in daily_revenue]
    revenues = [float(r.revenue) for r in daily_revenue]
    
    # Lot-wise occupancy
    lot_names = [lot.name for lot in parking_lots]
    lot_occupancy = []
    lot_availability = []
    
    for lot in parking_lots:
        occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        available = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        lot_occupancy.append(occupied)
        lot_availability.append(available)
    
    return render_template('admin/summary.html',
                           total_spots=total_spots,
                           available_spots=available_spots,
                           occupied_spots=occupied_spots,
                           dates=dates,
                           revenues=revenues,
                           lot_names=lot_names,
                           lot_occupancy=lot_occupancy,
                           lot_availability=lot_availability)

@admin_bp.route('/search', methods=['GET', 'POST'])
@admin_required
def search():
    query = request.args.get('query', '')
    
    if query:
        # Search for parking lots
        lots = ParkingLot.query.filter(
            (ParkingLot.name.contains(query)) |
            (ParkingLot.address.contains(query)) |
            (ParkingLot.pin_code.contains(query))
        ).all()
        
        # Search for users
        users = User.query.filter(
            (User.name.contains(query)) |
            (User.email.contains(query)) |
            (User.address.contains(query)) |
            (User.pin_code.contains(query))
        ).filter_by(is_admin=False).all()
        
        return render_template('admin/search_results.html', 
                               query=query, 
                               lots=lots, 
                               users=users)
    
    return render_template('admin/search.html')