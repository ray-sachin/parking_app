from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from models.database import db
from models.user import User
from controllers.auth_controller import auth_bp
from controllers.admin_controller import admin_bp
from controllers.user_controller import user_bp
from controllers.api_controller import api_bp
from models.user import create_admin_user  

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bae15670c1336191a65f0968'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(api_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Create the admin user and all tables when the app is first set up
def initialize_app():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email='admin@parking.com').first()
        if not admin:
            create_admin_user()

if __name__ == '__main__':
    initialize_app()
    app.run(debug=True)