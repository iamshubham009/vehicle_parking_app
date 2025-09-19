from flask_sqlalchemy import SQLAlchemy               
db = SQLAlchemy()

class User(db.Model):                                                           
    __tablename__ = 'users' 
    id = db.Column(db.Integer, primary_key = True)                              
    username = db.Column(db.String(20), unique = True, nullable = False)       
    email = db.Column(db.String(50), unique = True , nullable = False)
    password = db.Column(db.String(50), nullable = False)
    role = db.Column(db.String(10),default= 'user')

    reserves = db.relationship('Reserve', backref = 'lot', lazy = True)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id = db.Column(db.Integer, primary_key = True)
    prime_location = db.Column(db.String(50),nullable = False)
    address= db.Column(db.String(50),nullable = False)
    pincode = db.Column(db.String(50), nullable = False)
    price = db.Column(db.Float, nullable = False)
    max_spot = db.Column(db.Integer, nullable = False)

    spots = db.relationship('ParkingSpot', backref = 'lot', lazy = True)

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key = True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable = False) 
    status = db.Column(db.Boolean, default = True, nullable = False)  

    reserves = db.relationship('Reserve', backref = 'spot', lazy = True)

class Reserve(db.Model):
    __tablename__ = 'reserves'                   
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),nullable = False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable = False)
    vehicle_number  = db.Column(db.String(50),unique = True, nullable = False)
    start_time = db.Column(db.DateTime, nullable = False)
    end_time = db.Column(db.DateTime, nullable = False)
    total_cost = db.Column(db.Float, nullable = False)
    reserve_status = db.Column(db.String(50),default = "active", nullable = False) 