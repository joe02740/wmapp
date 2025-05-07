from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
import logging
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
from datetime import datetime, timedelta
import json
import stripe

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
            "https://nbwm.netlify.app",
            "http://localhost:5173",  # Vite dev server
            "http://localhost:5174"   # Alternative port
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
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
stripe_price_ids = {
    'basic': os.getenv('STRIPE_BASIC_PRICE_ID'),
    'pro': os.getenv('STRIPE_PRO_PRICE_ID')
}

# Configure proxy headers if using a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database
def init_db():
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        name TEXT,
        subscription_tier TEXT DEFAULT 'free',
        subscription_end_date TEXT,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        created_at TEXT,
        last_login TEXT
    )
    ''')
    
    # Create usage table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        query TEXT,
        scope TEXT,
        tokens_used INTEGER,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Get user from database or create new user
def get_or_create_user(user_id, email=None, name=None):
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    current_time = datetime.now().isoformat()
    
    if not user:
        # Create new user
        cursor.execute(
            'INSERT INTO users (id, email, name, subscription_tier, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, email, name, 'free', current_time, current_time)
        )
        conn.commit()
        logger.info(f"Created new user: {user_id}")
    else:
        # Update last login
        cursor.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (current_time, user_id)
        )
        conn.commit()
    
    # Get user subscription tier
    cursor.execute('SELECT subscription_tier, subscription_end_date, stripe_customer_id FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    return {
        'id': user_id,
        'subscription_tier': user_data[0],
        'subscription_end_date': user_data[1],
        'stripe_customer_id': user_data[2]
    }

# Check usage limits
def check_usage_limit(user_id):
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Get user subscription tier
    cursor.execute('SELECT subscription_tier, subscription_end_date FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return False, "User not found"
    
    tier, end_date = user_data
    
    # Check if subscription has expired
    if tier != 'free' and end_date:
        subscription_end = datetime.fromisoformat(end_date)
        if datetime.now() > subscription_end:
            # Downgrade to free if subscription expired
            cursor.execute('UPDATE users SET subscription_tier = "free" WHERE id = ?', (user_id,))
            conn.commit()
            tier = 'free'
    
    # Get today's usage
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        'SELECT COUNT(*) FROM usage WHERE user_id = ? AND created_at LIKE ?', 
        (user_id, f"{today}%")
    )
    today_count = cursor.fetchone()[0]
    
    # Get monthly usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute(
        'SELECT COUNT(*) FROM usage WHERE user_id = ? AND created_at LIKE ?', 
        (user_id, f"{current_month}%")
    )
    month_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Define limits based on tier (reduced limits)
    limits = {
        'free': {'daily': 1, 'monthly': 10},
        'basic': {'daily': 10, 'monthly': 100},
        'pro': {'daily': 50, 'monthly': 500}
    }
    
    # Check limits
    if tier in limits:
        if today_count >= limits[tier]['daily']:
            return False, f"Daily limit reached for {tier} tier ({limits[tier]['daily']} queries per day)"
        
        if month_count >= limits[tier]['monthly']:
            return False, f"Monthly limit reached for {tier} tier ({limits[tier]['monthly']} queries per month)"
    
    return True, None

# Record usage
def record_usage(user_id, query, scope, tokens_used):
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    
    cursor.execute(
        'INSERT INTO usage (user_id, query, scope, tokens_used, created_at) VALUES (?, ?, ?, ?, ?)',
        (user_id, query, scope, tokens_used, current_time)
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Recorded usage for user {user_id}: {tokens_used} tokens")

# Get user usage statistics
@app.route('/api/usage', methods=['GET'])
def get_usage():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Get user subscription info
    cursor.execute('SELECT subscription_tier, subscription_end_date FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    tier, end_date = user_data
    
    # Get today's usage
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        'SELECT COUNT(*) FROM usage WHERE user_id = ? AND created_at LIKE ?', 
        (user_id, f"{today}%")
    )
    today_count = cursor.fetchone()[0]
    
    # Get monthly usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute(
        'SELECT COUNT(*) FROM usage WHERE user_id = ? AND created_at LIKE ?', 
        (user_id, f"{current_month}%")
    )
    month_count = cursor.fetchone()[0]
    
    # Get total usage
    cursor.execute('SELECT COUNT(*) FROM usage WHERE user_id = ?', (user_id,))
    total_count = cursor.fetchone()[0]
    
    # Get recent queries
    cursor.execute(
        'SELECT query, scope, tokens_used, created_at FROM usage WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', 
        (user_id,)
    )
    recent_queries = cursor.fetchall()
    
    conn.close()
    
    # Format recent queries
    recent = []
    for query, scope, tokens, created_at in recent_queries:
        recent.append({
            'query': query,
            'scope': scope,
            'tokens_used': tokens,
            'created_at': created_at
        })
    
    # Define limits based on tier
    limits = {
        'free': {'daily': 1, 'monthly': 10},
        'basic': {'daily': 10, 'monthly': 100},
        'pro': {'daily': 50, 'monthly': 500}
    }
    
    return jsonify({
        'user_id': user_id,
        'subscription_tier': tier,
        'subscription_end_date': end_date,
        'usage': {
            'daily': today_count,
            'daily_limit': limits.get(tier, {}).get('daily', 0),
            'monthly': month_count,
            'monthly_limit': limits.get(tier, {}).get('monthly', 0),
            'total': total_count
        },
        'recent_queries': recent
    })

# Create Stripe checkout session
@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        tier = data.get('tier')
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
            
        if tier not in ['basic', 'pro']:
            return jsonify({'error': 'Invalid subscription tier'}), 400
            
        # Get price ID from tier
        price_id = stripe_price_ids.get(tier)
        if not price_id:
            return jsonify({'error': 'Invalid subscription tier or price not configured'}), 400
        
        # Get or create user
        user = get_or_create_user(user_id)
        
        # Check if user already has a Stripe customer ID
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        cursor.execute('SELECT stripe_customer_id, email, name FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
            
        stripe_customer_id, email, name = user_data
        
        # Create or get Stripe customer
        if not stripe_customer_id:
            # Create customer in Stripe
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={'user_id': user_id}
            )
            
            # Save customer ID to database
            cursor.execute(
                'UPDATE users SET stripe_customer_id = ? WHERE id = ?',
                (customer.id, user_id)
            )
            conn.commit()
            stripe_customer_id = customer.id
        
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
            success_url='https://nbwm.netlify.app/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://nbwm.netlify.app/cancel',
            client_reference_id=user_id,  # Store your user ID for reference
            metadata={'user_id': user_id, 'tier': tier}
        )
        
        return jsonify({'checkoutUrl': checkout_session.url})
        
    except Exception as e:
        logger.error(f"Checkout session error: {str(e)}")
        return jsonify({
            "error": "An error occurred creating checkout session",
            "details": str(e)
        }), 500

# Stripe webhook endpoint
@app.route('/api/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('client_reference_id')
            subscription_id = session.get('subscription')
            
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            tier = session.get('metadata', {}).get('tier')
            
            if not tier:
                # Determine tier from price ID if not in metadata
                price_id = subscription.plan.id
                tier = 'basic' if price_id == stripe_price_ids['basic'] else 'pro'
            
            # Calculate subscription end date
            current_period_end = subscription.current_period_end
            end_date = datetime.fromtimestamp(current_period_end).isoformat()
            
            # Update user's subscription in database
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE users SET subscription_tier = ?, subscription_end_date = ?, stripe_subscription_id = ? WHERE id = ?',
                (tier, end_date, subscription_id, user_id)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Subscription {subscription_id} activated for user {user_id}")
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            subscription_id = invoice.get('subscription')
            
            if subscription_id:
                # Get subscription details
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer_id = subscription.customer
                
                # Find user with this Stripe customer ID
                conn = sqlite3.connect(app.config['DB_PATH'])
                cursor = conn.cursor()
                
                cursor.execute('SELECT id, subscription_tier FROM users WHERE stripe_customer_id = ?', (customer_id,))
                user_data = cursor.fetchone()
                
                if user_data:
                    user_id, tier = user_data
                    
                    # Calculate new subscription end date
                    current_period_end = subscription.current_period_end
                    end_date = datetime.fromtimestamp(current_period_end).isoformat()
                    
                    # Update subscription end date
                    cursor.execute(
                        'UPDATE users SET subscription_end_date = ? WHERE id = ?',
                        (end_date, user_id)
                    )
                    
                    conn.commit()
                    logger.info(f"Subscription {subscription_id} renewed for user {user_id}")
                
                conn.close()
                
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.customer
            
            # Find user with this Stripe customer ID
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM users WHERE stripe_customer_id = ?', (customer_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                user_id = user_data[0]
                
                # Downgrade user to free tier
                cursor.execute(
                    'UPDATE users SET subscription_tier = "free", subscription_end_date = NULL, stripe_subscription_id = NULL WHERE id = ?',
                    (user_id,)
                )
                
                conn.commit()
                logger.info(f"Subscription ended for user {user_id}")
            
            conn.close()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error'}), 400

# Update user subscription (manual option for free tier)
@app.route('/api/subscribe', methods=['POST'])
def update_subscription():
    data = request.json
    user_id = data.get('user_id')
    tier = data.get('tier')
    
    if not user_id or not tier:
        return jsonify({'error': 'User ID and tier are required'}), 400
    
    if tier not in ['free', 'basic', 'pro']:
        return jsonify({'error': 'Invalid subscription tier'}), 400
    
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # For paid tiers, users should use Stripe Checkout
    if tier != 'free':
        conn.close()
        return jsonify({
            'error': 'For paid tiers, please use Stripe Checkout',
            'redirect': True
        }), 400
    
    # Update subscription to free tier
    cursor.execute(
        'UPDATE users SET subscription_tier = ?, subscription_end_date = NULL WHERE id = ?',
        (tier, user_id)
    )
    
    # If user has active Stripe subscription, cancel it
    cursor.execute('SELECT stripe_subscription_id FROM users WHERE id = ?', (user_id,))
    subscription_data = cursor.fetchone()
    
    if subscription_data and subscription_data[0]:
        try:
            # Cancel subscription in Stripe
            stripe.Subscription.delete(subscription_data[0])
            
            # Clear subscription ID in database
            cursor.execute(
                'UPDATE users SET stripe_subscription_id = NULL WHERE id = ?',
                (user_id,)
            )
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Updated subscription for user {user_id} to {tier}")
    
    return jsonify({
        'success': True,
        'message': f'Subscription updated to {tier}',
        'user_id': user_id,
        'subscription_tier': tier,
        'subscription_end_date': None
    })

# Claude query endpoint
@app.route('/api/query', methods=['POST'])
def query_claude():
    try:
        user_query = request.json.get('query')
        scope = request.json.get('scope', 'mass_laws')
        user_id = request.json.get('user_id')
        
        if not user_query:
            return jsonify({'error': 'Query is required'}), 400
            
        logger.info(f"Processing query: {user_query} [scope: {scope}] [user: {user_id}]")

        # Check user and usage limits if user_id is provided
        if user_id:
            # Get or create user
            user = get_or_create_user(user_id)
            
            # Check usage limits
            can_query, limit_message = check_usage_limit(user_id)
            
            if not can_query:
                return jsonify({
                    "type": "error",
                    "response": limit_message,
                    "upgrade_required": True
                }), 429
        
        # Read both the laws and legacy document files
        laws_path = os.path.join(os.path.dirname(__file__), 'data', 'mass_weights_measures_laws.txt')
        legacy_path = os.path.join(os.path.dirname(__file__), 'data', 'combined_output.txt')
        
        try:
            with open(laws_path, 'r', encoding='utf-8') as file:
                laws_text = file.read()
                
            with open(legacy_path, 'r', encoding='utf-8') as file:
                legacy_text = file.read()
        except Exception as e:
            logger.error(f"Error reading data files: {str(e)}")
            laws_text = "Error loading laws document."
            legacy_text = "Error loading legacy document."

        # Create Anthropic client
        client = anthropic.Anthropic(api_key=app.config['ANTHROPIC_API_KEY'])
        
        # Create system prompt with guidance about document precedence
        system_prompt = """
        You are an AI assistant specialized in Massachusetts weights and measures laws and procedures.
        Provide accurate and helpful information based on the given context. You are chatting with a Weights and Measures official.
        
        IMPORTANT GUIDANCE ON SOURCES:
        If a conflict exists between a scanned legacy document and a law or regulation, the law always takes precedence.
        * The legacy document is a general reference created approximately 20 years ago and may not reflect current standards.
        * Use the legacy document to provide historical context or procedural insight, but defer to official laws for enforcement or compliance guidance.
        
        Be concise in your responses while being accurate and helpful.
        """
        
        # Make the Claude query
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"MASSACHUSETTS WEIGHTS AND MEASURES LAWS:\n{laws_text}\n\nLEGACY REFERENCE DOCUMENT:\n{legacy_text}\n\nUser question: {user_query}"
                }
            ]
        )

        # Record usage if user_id is provided
        if user_id:
            tokens_used = response.usage.output_tokens
            record_usage(user_id, user_query, scope, tokens_used)

        return jsonify({
            "type": scope,
            "response": response.content[0].text
        })

    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e)
        }), 500

# Initialize database when app starts
with app.app_context():
    init_db()

if __name__ == '__main__':
    # Only enable debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Get port from environment variable for production deployment
    port = int(os.environ.get("PORT", 5000))
    
    app.run(host='0.0.0.0', port=port, debug=debug)