from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
import datetime
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///monolith.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key-not-for-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)


# ─────────────────────────────────────────────
# DATABASE MODELS — All in one file, one DB
# ─────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))
    sent_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ─────────────────────────────────────────────
# HEALTH CHECK — Required for Kubernetes later
# ─────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'monolith',
        'timestamp': datetime.datetime.utcnow().isoformat()
    }), 200

# ─────────────────────────────────────────────
# AUTH ROUTES — Tightly coupled inside same app
# ─────────────────────────────────────────────

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'username, email and password are required'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash
    )
    db.session.add(user)
    db.session.commit()

    # Problem: notification logic is directly inside auth logic — tightly coupled
    notification = Notification(
        user_id=user.id,
        message=f"Welcome {user.username}! Your account has been created.",
        notification_type='welcome'
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        'message': 'User registered successfully',
        'user_id': user.id,
        'username': user.username
    }), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = create_access_token(identity=str(user.id))

    return jsonify({
        'access_token': token,
        'user_id': user.id,
        'username': user.username
    }), 200

@app.route('/auth/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'created_at': user.created_at.isoformat()
    }), 200

# ─────────────────────────────────────────────
# PRODUCT ROUTES — Also in the same file
# ─────────────────────────────────────────────

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'stock': p.stock
    } for p in products]), 200

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock
    }), 200

@app.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('price'):
        return jsonify({'error': 'name and price are required'}), 400
    
    product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=data['price'],
        stock=data.get('stock', 0)
    )
    db.session.add(product)
    db.session.commit()

    return jsonify({
        'message': 'Product created',
        'product_id': product.id
    }), 201

# ─────────────────────────────────────────────
# ORDER ROUTES — Directly accesses Product model
# This is the tight coupling problem: order logic
# knows about product internals directly
# ─────────────────────────────────────────────

@app.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    user_id = int(get_jwt_identity())
    
    if not data or not data.get('product_id') or not data.get('quantity'):
        return jsonify({'error': 'product_id and quantity are required'}), 400
    
    # Problem: order service directly queries product table
    # In microservices, this would be an HTTP call instead
    product = Product.query.get(data['product_id'])
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    if product.stock < data['quantity']:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    total_price = product.price * data['quantity']
    
    order = Order(
        user_id=user_id,
        product_id=product.id,
        quantity=data['quantity'],
        total_price=total_price,
        status='confirmed'
    )

    # Problem: directly modifying product stock from order code
    product.stock -= data['quantity']
    
    db.session.add(order)
    db.session.commit()
    
    # Problem: notification logic directly inside order logic
    notification = Notification(
        user_id=user_id,
        message=f"Order #{order.id} confirmed! {data['quantity']}x {product.name} for ${total_price:.2f}",
        notification_type='order_confirmation'
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        'message': 'Order created successfully',
        'order_id': order.id,
        'total_price': total_price,
        'status': order.status
    }), 201

@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())
    orders = Order.query.filter_by(user_id=user_id).all()
    
    result = []
    for order in orders:
        product = Product.query.get(order.product_id)
        result.append({
            'order_id': order.id,
            'product_name': product.name if product else 'Unknown',
            'quantity': order.quantity,
            'total_price': order.total_price,
            'status': order.status,
            'created_at': order.created_at.isoformat()
        })
    
    return jsonify(result), 200

# ─────────────────────────────────────────────
# NOTIFICATION ROUTES
# ─────────────────────────────────────────────

@app.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    notifications = Notification.query.filter_by(user_id=user_id).order_by(
        Notification.sent_at.desc()
    ).all()

    return jsonify([{
        'id': n.id,
        'message': n.message,
        'type': n.notification_type,
        'sent_at': n.sent_at.isoformat()
    } for n in notifications]), 200

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database tables created")
        print("🚀 Monolith running on http://localhost:5000")
        print("")
        print("Available endpoints:")
        print("  POST /auth/register")
        print("  POST /auth/login")
        print("  GET  /auth/profile  (requires token)")
        print("  GET  /products")
        print("  POST /products      (requires token)")
        print("  POST /orders        (requires token)")
        print("  GET  /orders        (requires token)")
        print("  GET  /notifications (requires token)")
        print("  GET  /health")
    
    app.run(debug=True, host='0.0.0.0', port=5000)


