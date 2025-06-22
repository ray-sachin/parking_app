from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError

class ParkingLotForm(FlaskForm):
    name = StringField('Location Name', validators=[DataRequired(), Length(min=3, max=100)])
    price = FloatField('Price per Hour (₹)', validators=[DataRequired(), NumberRange(min=1)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    pin_code = StringField('PIN Code', validators=[DataRequired(), Length(min=6, max=10)])
    max_spots = IntegerField('Maximum Number of Spots', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Parking Lot')

class ReservationForm(FlaskForm):
    lot_id = SelectField('Select Parking Lot', validators=[DataRequired()], coerce=int)
    vehicle_number = StringField('Vehicle Number', validators=[
        DataRequired(), 
        Length(min=5, max=20, message='Vehicle number must be between 5 and 20 characters')
    ])
    submit = SubmitField('Reserve Spot')
    
    def validate_vehicle_number(self, vehicle_number):
        # Vehicle number format validation (can be customized)
        import re
        if not re.match(r'^[A-Z0-9 -]+$', vehicle_number.data):
            raise ValidationError('Invalid vehicle number format. Use uppercase letters, numbers, spaces, or hyphens.')

class ReleaseForm(FlaskForm):
    submit = SubmitField('Release Spot')