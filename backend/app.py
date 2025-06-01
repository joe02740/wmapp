print("1. Starting app.py")

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
import logging
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import json
import stripe

print("2. Basic imports done")

from database import init_db, get_db_connection

print("3. Database import done")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://wmhelper.com",
            "https://www.wmhelper.com",
            "https://nbwm.netlify.app",
            "http://localhost:5173",  # Keep for local dev
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Range", "X-Content-Range"],
        "supports_credentials": True,
        "max_age": 600
    }
})

# Load configuration from environment variables
app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')
app.config['DB_PATH'] = os.getenv('DB_PATH', 'wm_helper.db')

# Initialize Stripe
app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
if app.config['STRIPE_SECRET_KEY']:
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
stripe_price_ids = {
    'basic': os.getenv('STRIPE_BASIC_PRICE_ID'),
    'pro': os.getenv('STRIPE_PRO_PRICE_ID')
}

# Configure proxy headers if using a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

print("4. About to define routes")

@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({
        'message': 'Backend is working!', 
        'user_id': request.args.get('user_id'),
        'timestamp': datetime.now().isoformat()
    })

print("5. Test route defined")

@app.route('/api/usage', methods=['GET'])
def get_usage():
    user_id = request.args.get('user_id')
    logger.info(f"Usage request for user_id: {user_id}")
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    try:
        # Add debug logging
        logger.info("About to call get_or_create_user")
        user = get_or_create_user(user_id)
        logger.info(f"User created/retrieved: {user}")
        # Continue with your function...
        conn = get_db_connection()
        cursor = conn.cursor()
        # ...existing code for the rest of the function...
    except Exception as e:
        logger.error(f"Error in get_usage: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

print("6. Usage route defined")

@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        tier = data.get('tier')
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
            
        if tier != 'paid':
            return jsonify({'error': 'Invalid subscription tier'}), 400
        
        # Get price ID from environment
        price_id = os.getenv('STRIPE_PRICE_ID_PAID')
        if not price_id:
            return jsonify({'error': 'Stripe price not configured'}), 500
        
        # Get or create user
        user = get_or_create_user(user_id)
        
        # Get user email from Clerk (you might need to pass this from frontend)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT email, stripe_customer_id FROM users WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404
            
        email, stripe_customer_id = user_data
        
        # Create or get Stripe customer
        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=email,
                metadata={'user_id': user_id}
            )
            
            # Save customer ID to database
            cursor.execute('''
                UPDATE users SET stripe_customer_id = %s WHERE id = %s
            ''', (customer.id, user_id))
            conn.commit()
            stripe_customer_id = customer.id
        
        cursor.close()
        conn.close()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'https://wmhelper.com/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url='https://wmhelper.com/cancel',
            client_reference_id=user_id,
            metadata={'user_id': user_id, 'tier': tier}
        )
        
        logger.info(f"Created checkout session for user {user_id}")
        
        return jsonify({'checkoutUrl': checkout_session.url})
        
    except Exception as e:
        logger.error(f"Checkout session error: {str(e)}")
        return jsonify({
            "error": "An error occurred creating checkout session",
            "details": str(e)
        }), 500

# Get user from database or create new user
# REPLACED FUNCTION

def get_or_create_user(user_id, email=None, name=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if user exists
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        current_time = datetime.now()
        if not user:
            # Create new user
            cursor.execute('''
                INSERT INTO users (id, email, name, subscription_tier, created_at, last_login) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_id, email, name, 'free', current_time, current_time))
            conn.commit()
            logger.info(f"Created new user: {user_id}")
        else:
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = %s WHERE id = %s
            ''', (current_time, user_id))
            conn.commit()
        # Get user subscription tier
        cursor.execute('''
            SELECT subscription_tier, subscription_end_date, stripe_customer_id 
            FROM users WHERE id = %s
        ''', (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            'id': user_id,
            'subscription_tier': user_data[0] if user_data else 'free',
            'subscription_end_date': user_data[1].isoformat() if user_data and user_data[1] else None,
            'stripe_customer_id': user_data[2] if user_data else None
        }
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        return {
            'id': user_id,
            'subscription_tier': 'free',
            'subscription_end_date': None,
            'stripe_customer_id': None
        }

# Check usage limits
# REPLACED FUNCTION

def check_usage_limit(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Get user subscription tier
        cursor.execute('''
            SELECT subscription_tier, subscription_end_date 
            FROM users WHERE id = %s
        ''', (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            cursor.close()
            conn.close()
            return False, "User not found"
        tier, end_date = user_data
        # Check if subscription has expired
        if tier != 'free' and end_date:
            if datetime.now() > end_date:
                # Downgrade to free if subscription expired
                cursor.execute('''
                    UPDATE users SET subscription_tier = 'free' WHERE id = %s
                ''', (user_id,))
                conn.commit()
                tier = 'free'
        # Get today's usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage 
            WHERE user_id = %s AND created_at::date = CURRENT_DATE
        ''', (user_id,))
        today_count = cursor.fetchone()[0]
        # Get monthly usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage 
            WHERE user_id = %s AND created_at >= date_trunc('month', CURRENT_DATE)
        ''', (user_id,))
        month_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        # Define limits based on tier
        limits = {
            'free': {'daily': 2, 'monthly': 6},
            'paid': {'daily': 50, 'monthly': 500}
        }
        # Check limits
        if tier in limits:
            if today_count >= limits[tier]['daily']:
                return False, f"Daily limit reached for {tier} tier ({limits[tier]['daily']} queries per day)"
            if month_count >= limits[tier]['monthly']:
                return False, f"Monthly limit reached for {tier} tier ({limits[tier]['monthly']} queries per month)"
        return True, None
    except Exception as e:
        logger.error(f"Error checking usage limit: {str(e)}")
        return True, None  # Allow usage if error

# Record usage
# REPLACED FUNCTION

def record_usage(user_id, query, scope, tokens_used):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usage (user_id, query, scope, tokens_used, created_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, query, scope, tokens_used, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Recorded usage for user {user_id}: {tokens_used} tokens")
    except Exception as e:
        logger.error(f"Error recording usage: {str(e)}")

# Initialize database when app starts
init_db()

# Debug: Print registered routes
print("=== REGISTERED ROUTES ===")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")
print("========================")

if __name__ == '__main__':
    # Only enable debug mode in developmen
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Get port from environment variable for production deployment
    port = int(os.environ.get("PORT", 5000))
    
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)