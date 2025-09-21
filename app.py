from flask import Flask ,render_template, flash, redirect, request, url_for, session
from models import db, User, ParkingLot, ParkingSpot, Reserve
from datetime import datetime, timedelta

import numpy as np 
import os

import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///parking.db"
app.config['SECRET_KEY'] = 'parking@123'

db.init_app(app)

def make_admin():
    admin =User.query.filter_by(username = 'shubham').first()
    if not admin:
        admin = User(username = 'shubham',
                     email = 'shubham@admin.com',
                     password = '123',
                     role = 'admin'
                     )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin.username}")
    else:
        print("Admin user already exists.")

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/admin_login', methods = ['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = User.query.filter_by(username = username, password = password, role = 'admin').first()
        if admin:
            session['admin_id'] = admin.id
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html')
            
    return render_template('admin_login.html')

@app.route('/user_signup', methods = ['GET','POST'])
def user_signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        exited_user = User.query.filter_by(username=username).first()
        if exited_user:
            flash('Username already exists. Please choose a different username.')
            return redirect(url_for('user_signup'))

        new_user = User(username=username, email=email,password=password, role='user')
        db.session.add(new_user)
        db.session.commit()  
        return redirect(url_for('user_login'))
    return render_template('user_signup.html')  

@app.route('/user_login', methods = ['GET','POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user.role == 'admin':
            return redirect(url_for('user_login'))
        else:
            session['user_id'] = user.id
            session['role'] = 'user'
            return redirect(url_for('user_dashboard'))
    return render_template('user_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    users = User.query.all()
    parking_lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', users=users, parking_lots=parking_lots)
    
@app.route('/user_dashboard', methods = ['GET', 'POST'])
def user_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        return redirect(url_for('user_login'))
    
    parking_lots = ParkingLot.query.all()
    active_bookings = Reserve.query.filter_by(user_id = user_id,reserve_status= "active").all()
    released_bookings = Reserve.query.filter_by(user_id = user_id, reserve_status = "released").all()

    available_lots = []
    for lot in parking_lots:
        lot.available_spots = len([spot for spot in lot.spots if spot.status == True])
        if lot.available_spots > 0:
            available_lots.append(lot)

    return render_template('user_dashboard.html', user=user, parking_lots = parking_lots, my_bookings=active_bookings, released_bookings=released_bookings)


@app.route('/parking_users', methods = ['GET','POST'])
def parking_users():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    users = User.query.all()
    return render_template('parking_users.html', users=users)

@app.route('/create_parking_lot', methods = ['GET','POST'])
def create_parking_lot():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        prime_location = request.form['prime_location']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price'])
        maximum_spot = int(request.form['maximum_spot'])
        new_parking_lot = ParkingLot(prime_location=prime_location, address=address, pincode=pincode, price = price, max_spot = maximum_spot)

        db.session.add(new_parking_lot)
        db.session.commit()

        for i in range(maximum_spot):
            new_spot = ParkingSpot(lot_id = new_parking_lot.id, status = True)
            db.session.add(new_spot)
        db.session.commit()    
        return redirect(url_for('admin_dashboard'))

    return render_template('create_parking_lot.html')

@app.route('/edit_parking_lot/<int:lot_id>', methods = ['GET','POST'])
def edit_parking_lot(lot_id):
    parking_lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        parking_lot.prime_location = request.form['prime_location']
        parking_lot.address = request.form['address']
        parking_lot.pincode = request.form['pincode']
        parking_lot.price = float(request.form['price'])
        
        new_max_spot = int(request.form['maximum_spot'])
        current_spots = len(parking_lot.spots)

        if new_max_spot >current_spots:
            for i in range(new_max_spot - current_spots):
                new_spot = ParkingSpot(lot_id = parking_lot.id, status = True)
                db.session.add(new_spot)

        elif new_max_spot < current_spots:
            spot_to_remove = current_spots - new_max_spot
            deletable_spots = (ParkingSpot.query
                                .filter_by(lot_id = parking_lot.id, status = True)
                                .order_by(ParkingSpot.id.desc())
                                .limit(spot_to_remove)
                                .all()
            )

            if len(deletable_spots) < spot_to_remove:
                flash("Not enough spots to remove!", "danger")

            for spot in deletable_spots:
                db.session.delete(spot)

        parking_lot.max_spot = new_max_spot
        db.session.commit()
        flash("Parking lot updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_parking_lot.html',parking_lot = parking_lot)

@app.route('/release_reserve/<int:reserve_id>', methods=['GET', 'POST'])
def release_reserve(reserve_id):    
    reserve = Reserve.query.get_or_404(reserve_id)

    if reserve.user_id != session.get('user_id'):
        return "Unauthorized"
    
    parking_lot = ParkingLot.query.get(reserve.spot.lot_id)

    reserve.end_time = datetime.now()
    duration = (reserve.end_time - reserve.start_time).total_seconds() / 60
    hours = duration / 60
    reserve.total_cost = round(hours * parking_lot.price, 2)
    # reserve.total_cost = int(-(-duration_hours // 1)) * lot.price    # Ceiling division to charge for full hours
    # reserve.total_cost = -(-duration_minutes // 30)

    if request.method == 'POST':
        reserve.spot.status = True
        reserve.reserve_status = "released"
        db.session.commit()

        return redirect(url_for('user_dashboard'))
    return render_template('release_reserve.html', reserve=reserve)


@app.route('/delete_parking_lot/<int:id>', methods=['POST'])
def delete_parking_lot(id):
    lot = ParkingLot.query.get_or_404(id)

    # Check if all spots are available
    all_available = all(spot.status for spot in lot.spots)

    if all_available:
        
        for spot in lot.spots:
            db.session.delete(spot)
        
        db.session.delete(lot)
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/book_spot/<int:lot_id>', methods=['GET', 'POST'])
def book_spot(lot_id):

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('user_login'))
    
    lot = ParkingLot.query.get_or_404(lot_id)
    spot = ParkingSpot.query.filter_by(lot_id=lot.id, status=True).first()

    if not spot:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        vehicle_no = request.form['vehicle_number']
        
        user = User.query.get(user_id)
        start_time = datetime.now()  
        
        
        reservation = Reserve(
            spot_id=spot.id,
            user_id=user.id,
            vehicle_number=vehicle_no,
            start_time=start_time,
            end_time= None,
            total_cost=0,
            reserve_status="active"
        )

        spot.status = False
        db.session.add(reservation)
        db.session.commit()

        return redirect(url_for('user_dashboard'))
        #update_summary_chart()
    return render_template('book_spot.html', lot=lot, spot=spot, user=user)


@app.route('/spot_reservation_detail/<int:spot_id>')
def spot_reservation_detail(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    reserve = Reserve.query.filter_by(spot_id=spot_id).first()

    if not reserve:
        return f"No reservation found for Spot ID {spot_id}"

    user = User.query.get(reserve.user_id)
    lot = ParkingLot.query.get(spot.lot_id)

    return render_template('spot_reservation_detail.html', reserve=reserve, user=user, lot=lot, spot=spot)

@app.route('/admin_summary')
def admin_summary():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    
    lots = ParkingLot.query.all()
    lot_names = [lot.prime_location for lot in lots]
    occupied_counts = []
    max_spots = []
    revenue_data = []  # For pie chart

    for lot in lots:
        total = len(lot.spots)
        occupied = sum(1 for spot in lot.spots if not spot.status)  # status=False means occupied
        occupied_counts.append(occupied)
        max_spots.append(lot.max_spot)

        # Total revenue from reserves in this lot
        lot_reserves = Reserve.query.join(ParkingSpot).filter(ParkingSpot.lot_id == lot.id).all()
        lot_revenue = sum(res.total_cost for res in lot_reserves)
        revenue_data.append(lot_revenue)

    x = np.arange(len(lot_names))

    plt.figure(figsize=(12, 6))
    bars = plt.bar(x, occupied_counts, color='orange', width=0.6)

    # Add value labels on top of bars
    for i, value in enumerate(occupied_counts):
        plt.text(i, value + 0.2, str(value), ha='center', va='bottom')

    plt.xlabel('Parking Lot Location')
    plt.ylabel('Occupied Spots')
    plt.title('Occupied Spots per Parking Lot')
    plt.xticks(x, lot_names, rotation=45, ha='right')

    # Y-axis from 0 to highest max spot (e.g., 20)
    y_max = max(max_spots) if max_spots else 10
    plt.yticks(np.arange(0, y_max + 2, 1))
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.tight_layout()

    # Save chart
    charts_folder = os.path.join('static', 'charts')
    os.makedirs(charts_folder, exist_ok=True)
    chart_path = os.path.join(charts_folder, 'summary.png')
    plt.savefig(chart_path)
    plt.close()

    # ----- 🥧 Pie Chart: Revenue per Parking Lot -----
    plt.figure(figsize=(8, 8))
    plt.pie(revenue_data, labels=lot_names, autopct='%1.1f%%', startangle=140)
    plt.title('Revenue Share by Parking Lot')
    plt.tight_layout()
    pie_chart_path = os.path.join(charts_folder, 'revenue_pie.png')
    plt.savefig(pie_chart_path)
    plt.close()


    return render_template('admin_summary.html', chart_url=url_for('static', filename='charts/summary.png'),pie_url=url_for('static', filename='charts/revenue_pie.png'))

@app.route('/user_summary')
def user_summary():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('user_login'))

    # Collect user-specific reserves
    bookings = Reserve.query.filter_by(user_id=user_id).all()

    # Group by location
    location_counts = {}
    for booking in bookings:
        location = booking.spot.lot.prime_location
        location_counts[location] = location_counts.get(location, 0) + 1

    if not location_counts:
        location_counts["No Bookings"] = 0

    locations = list(location_counts.keys())
    counts = list(location_counts.values())

    x = np.arange(len(locations))

    plt.figure(figsize=(10, 5))
    bars = plt.bar(x, counts, color='skyblue', width=0.5)

    for i, value in enumerate(counts):
        plt.text(i, value + 0.1, str(value), ha='center', va='bottom')

    plt.xlabel('Location')
    plt.ylabel('Number of Bookings')
    plt.title('Your Bookings per Parking Lot')
    plt.xticks(x, locations, rotation=45, ha='right')
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()

    # Save to static folder
    charts_folder = os.path.join('static', 'charts')
    os.makedirs(charts_folder, exist_ok=True)
    chart_path = os.path.join(charts_folder, f'user_summary_{user_id}.png')
    plt.savefig(chart_path)
    plt.close()

    return render_template('user_summary.html', chart_url=url_for('static', filename=f'charts/user_summary_{user_id}.png'))
    

@app.route('/logout')
def logout():
    role = session.get('role')  # assuming you store this
    session.clear()
    if role == 'admin':
        return redirect(url_for('admin_login'))
    else:
        return redirect(url_for('user_login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        make_admin()

    app.run(debug= True)