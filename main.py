from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-autofixer'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///autofixer.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
admin = Admin(app, name='Admin')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return SignUp.query.get(int(user_id))

with app.app_context():
    class SignUp(UserMixin, db.Model):
        __tablename__ = "user_info"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        phone = db.Column(db.String(20), nullable=False)
        address = db.Column(db.String(200), nullable=False)
        gender = db.Column(db.String(10), nullable=False)
        password = db.Column(db.String(120), nullable=False)
    db.create_all()

with app.app_context():
    class Car(db.Model):
        __tablename__ = "user_cars"
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
        car_brand = db.Column(db.String(100), nullable=False)
        car_model = db.Column(db.String(100), nullable=False)
        model_year = db.Column(db.Integer, nullable=False)
        plate_number = db.Column(db.String(20), nullable=False)
        km = db.Column(db.Integer, nullable=False)
        user = db.relationship('SignUp', backref=db.backref('user_cars', lazy=True))
    db.create_all()

with app.app_context():
    class ServiceBooking(db.Model):
        __tablename__ = 'service_bookings'
        id = db.Column(db.Integer, primary_key=True)
        car_id = db.Column(db.Integer, db.ForeignKey('user_cars.id'), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
        booking_date = db.Column(db.Date, nullable=False)
        booking_time = db.Column(db.String(20), nullable=False)
        location = db.Column(db.String(100), nullable=False)
        governorate = db.Column(db.String(100), nullable=False)
        date = db.Column(db.DateTime, default=datetime.utcnow)
        car = db.relationship('Car', backref=db.backref('bookings', lazy=True))
        user = db.relationship('SignUp', backref=db.backref('bookings', lazy=True))
    db.create_all()

admin.add_view(ModelView(SignUp, db.session))
admin.add_view(ModelView(Car, db.session))
admin.add_view(ModelView(ServiceBooking, db.session))

@app.route("/")
def index():
    return render_template("home.html")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        gender = request.form.get('gender')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if password != confirm:
            flash('Passwords do not match!')
            return redirect(url_for('sign_up'))

        user_exists = SignUp.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already exists. Please log in.')
            return redirect(url_for('login'))

        new_user = SignUp(
            name=name,
            email=email,
            phone=phone,
            address=address,
            gender=gender,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account created successfully!')
        return redirect(url_for('login'))

    return render_template("sign_up.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('rememberMe') else False

        user = SignUp.query.filter_by(email=email).first()

        if not user or user.password != password:
            flash('Please check your login details and try again.')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        return redirect(url_for('services_intro'))
    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/services_intro")
def services_intro():
    return render_template("services_intro.html")


@app.route('/ev_service_booking', methods=['GET', 'POST'])
@login_required
def ev_service_booking():
    user_cars = Car.query.filter_by(user_id=current_user.id).all()

    if not user_cars:
        flash('Please add a car before booking a service.', 'warning')
        return redirect(url_for('add_car'))

    if request.method == 'POST':
        car_id = request.form.get('car_id')

        car = Car.query.get_or_404(car_id)
        if car.user_id != current_user.id:
            flash('You do not have permission to book service for this car.', 'danger')
            return redirect(url_for('car_service_history'))

        booking_date = datetime.strptime(request.form.get('booking_date'), '%Y-%m-%d')
        booking_time = request.form.get('booking_time')
        location = request.form.get('location')
        governorate = request.form.get('governorate')

        new_booking = ServiceBooking(
            car_id=car.id,
            user_id=current_user.id,
            booking_date=booking_date,
            booking_time=booking_time,
            location=location,
            governorate=governorate,
        )

        db.session.add(new_booking)
        db.session.commit()

        flash('Service booking successful! We look forward to serving you.', 'success')
        return redirect(url_for('car_service_history'))

    return render_template('ev_service_booking.html', cars=user_cars)



@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/car_service_history")
@login_required
def car_service_history():
    user_cars = Car.query.filter_by(user_id=current_user.id).all()
    service_bookings = []
    for car in user_cars:
        car_bookings = ServiceBooking.query.filter_by(car_id=car.id).order_by(ServiceBooking.booking_date.desc()).all()
        for booking in car_bookings:
            service_bookings.append({
                'car_id': car.id,
                'car_name': f"{car.car_brand} {car.car_model} ({car.model_year})",
                'booking_date': booking.booking_date,
                'booking_time': booking.booking_time,
                'location': booking.location,
                'date': booking.date,
                'governorate': booking.governorate,
                'booking_id': booking.id
            })
    return render_template('car_service_history.html', user_cars=user_cars, service_bookings=service_bookings)

@app.route("/add_car", methods=['GET', 'POST'])
@login_required
def add_car():
    if request.method == 'POST':
        car_brand = request.form.get('car_brand')
        car_model = request.form.get('car_model')
        model_year = request.form.get('model_year')
        plate_number = request.form.get('plate_number')
        km = request.form.get('km')

        if not all([car_brand, car_model, model_year, plate_number, km]):
            flash('All fields are required', 'error')
            return render_template("add_car.html")

        new_car = Car(
            user_id=current_user.id,
            car_brand=car_brand,
            car_model=car_model,
            model_year=model_year,
            plate_number=plate_number,
            km=km,
        )

        db.session.add(new_car)
        try:
            db.session.commit()
            flash('Car added successfully!', 'success')
            return redirect(url_for('car_service_history'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the car.', 'error')
    return render_template("add_car.html")


@app.route("/accessories")
def accessories():
    return render_template("accessories.html")

@app.route("/road_service")
def road_service():
    return render_template("road_service.html")

if __name__ == "__main__":
    app.run(debug=True)