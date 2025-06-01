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
            "https://wmhelper.com",
            "https://www.wmhelper.com",
            "https://nbwm.netlify.app"
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

# Initialize database
def init_db():
    try:
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
        
        # Create chat sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Create chat messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            message TEXT,
            sender TEXT,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

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
        'subscription_tier': user_data[0] if user_data else 'free',
        'subscription_end_date': user_data[1] if user_data else None,
        'stripe_customer_id': user_data[2] if user_data else None
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
    
    # Define limits based on tier
    limits = {
    'free': {'daily': 2, 'monthly': 6},        # Very restrictive
    'paid': {'daily': 50, 'monthly': 500}      # Actually usable
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

# Basic test route
@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({
        'message': 'Backend is working!', 
        'user_id': request.args.get('user_id'),
        'timestamp': datetime.now().isoformat()
    })

# Get user usage statistics
@app.route('/api/usage', methods=['GET'])
def get_usage():
    user_id = request.args.get('user_id')
    logger.info(f"Usage request for user_id: {user_id}")
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Get or create user first
        user = get_or_create_user(user_id)
        
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
        
        response_data = {
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
        }
        
        logger.info(f"Successfully retrieved usage data for user {user_id}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting usage data: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

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
            
        # For now, return a placeholder response since Stripe isn't fully configured
        return jsonify({
            'error': 'Stripe checkout not yet configured',
            'message': 'Please set up Stripe price IDs in environment variables'
        }), 501
        
    except Exception as e:
        logger.error(f"Checkout session error: {str(e)}")
        return jsonify({
            "error": "An error occurred creating checkout session",
            "details": str(e)
        }), 500

# Endpoint to create a Stripe PaymentIntent
@app.route('/api/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        amount = data.get('amount')  # Amount in dollars
        currency = data.get('currency', 'usd')
        user_id = data.get('user_id')
        tier = data.get('tier')
        
        if not amount or not user_id or not tier:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not app.config['STRIPE_SECRET_KEY']:
            return jsonify({'error': 'Stripe not configured'}), 501
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),  # Convert dollars to cents
            currency=currency,
            metadata={
                'user_id': user_id,
                'tier': tier
            }
        )
        
        logger.info(f"Created payment intent for user {user_id}, tier {tier}, amount ${amount}")
        
        return jsonify({
            'client_secret': intent.client_secret
        })
        
    except Exception as e:
        logger.error(f"Payment intent creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Update user subscription (manual option for free tier)
@app.route('/api/subscribe', methods=['POST'])
def update_subscription():
    try:
        data = request.json
        user_id = data.get('user_id')
        tier = data.get('tier')
        
        if not user_id or not tier:
            return jsonify({'error': 'User ID and tier are required'}), 400
        
        if tier not in ['free', 'paid']:
            return jsonify({'error': 'Invalid subscription tier'}), 400
        
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Get or create user
        user = get_or_create_user(user_id)
        
        # For paid tiers, users should use Stripe Checkout (for now, allow direct update for testing)
        if tier != 'free':
            # For testing purposes, allow direct subscription updates
            # In production, this should redirect to Stripe
            pass
        
        # Calculate end date for paid tiers
        end_date = None
        if tier != 'free':
            end_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        # Update subscription
        cursor.execute(
            'UPDATE users SET subscription_tier = ?, subscription_end_date = ? WHERE id = ?',
            (tier, end_date, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated subscription for user {user_id} to {tier}")
        
        return jsonify({
            'success': True,
            'message': f'Subscription updated to {tier}',
            'user_id': user_id,
            'subscription_tier': tier,
            'subscription_end_date': end_date
        })
        
    except Exception as e:
        logger.error(f"Subscription update error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# Enhanced version of your query endpoint that includes chat history
@app.route('/api/query', methods=['POST'])
def query_claude():
    try:
        user_query = request.json.get('query')
        scope = request.json.get('scope', 'mass_laws')
        user_id = request.json.get('user_id')
        session_id = request.json.get('session_id')  # New: include session ID
        
        if not user_query:
            return jsonify({'error': 'Query is required'}), 400
            
        logger.info(f"Processing query: {user_query} [scope: {scope}] [user: {user_id}] [session: {session_id}]")

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
        
        # Get chat history for context if session_id provided
        chat_context = ""
        if session_id and user_id:
            try:
                conn = sqlite3.connect(app.config['DB_PATH'])
                cursor = conn.cursor()
                
                # Get recent messages from this session (last 10 messages)
                cursor.execute('''
                    SELECT message, sender FROM chat_messages 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', (session_id,))
                
                recent_messages = cursor.fetchall()
                conn.close()
                
                if recent_messages:
                    # Reverse to get chronological order
                    recent_messages.reverse()
                    
                    chat_history = []
                    for message, sender in recent_messages:
                        role = "Human" if sender == "user" else "Assistant"
                        chat_history.append(f"{role}: {message}")
                    
                    chat_context = f"\n\nCONVERSATION HISTORY:\n" + "\n".join(chat_history) + "\n\n"
                
            except Exception as e:
                logger.error(f"Error getting chat context: {str(e)}")
                # Continue without context if there's an error
        
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
        if not app.config['ANTHROPIC_API_KEY']:
            return jsonify({'error': 'Anthropic API not configured'}), 501
            
        client = anthropic.Anthropic(api_key=app.config['ANTHROPIC_API_KEY'])
        
        # Create system prompt with guidance about document precedence
        system_prompt = """
        You are an AI assistant specialized in Massachusetts weights and measures laws and procedures.
        Provide accurate and helpful information based on the given context. You are chatting with a Weights and Measures official.
        
        IMPORTANT GUIDANCE ON SOURCES:
        If a conflict exists between a scanned legacy document and a law or regulation, the law always takes precedence.
        * The legacy document is a general reference created approximately 20 years ago and may not reflect current standards.
        * Use the legacy document to provide historical context or procedural insight, but defer to official laws for enforcement or compliance guidance.
        
        Be concise in your responses while being accurate and helpful. If there is conversation history, consider it for context but focus on the current question.
        """
        
        # Build the content with optional chat context
        content = f"MASSACHUSETTS WEIGHTS AND MEASURES LAWS:\n{laws_text}\n\nLEGACY REFERENCE DOCUMENT:\n{legacy_text}"
        
        if chat_context:
            content += chat_context
            
        content += f"\nCurrent question: {user_query}"
        
        # Make the Claude query
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": content
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

# Get chat history for a user
@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Get all chat sessions for user, ordered by most recent
        cursor.execute('''
            SELECT id, title, created_at, updated_at 
            FROM chat_sessions 
            WHERE user_id = ? 
            ORDER BY updated_at DESC 
            LIMIT 50
        ''', (user_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'sessions': sessions,
            'total': len(sessions)
        })
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        return jsonify({'error': 'Failed to fetch chat history'}), 500

# Get messages for a specific chat session
@app.route('/api/chat-session/<int:session_id>', methods=['GET'])
def get_chat_session(session_id):
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Verify session belongs to user
        cursor.execute('''
            SELECT title FROM chat_sessions 
            WHERE id = ? AND user_id = ?
        ''', (session_id, user_id))
        
        session = cursor.fetchone()
        if not session:
            conn.close()
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all messages for this session
        cursor.execute('''
            SELECT message, sender, created_at 
            FROM chat_messages 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        ''', (session_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'text': row[0],
                'sender': row[1],
                'created_at': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'session_id': session_id,
            'title': session[0],
            'messages': messages
        })
        
    except Exception as e:
        logger.error(f"Error fetching chat session: {str(e)}")
        return jsonify({'error': 'Failed to fetch chat session'}), 500

# Create or update a chat session
@app.route('/api/chat-session', methods=['POST'])
def save_chat_session():
    try:
        data = request.json
        user_id = data.get('user_id')
        session_id = data.get('session_id')  # None for new session
        title = data.get('title')
        messages = data.get('messages', [])
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        # Create new session or update existing
        if not session_id:
            # Create new session
            cursor.execute('''
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, title, current_time, current_time))
            session_id = cursor.lastrowid
        else:
            # Update existing session
            cursor.execute('''
                UPDATE chat_sessions 
                SET title = ?, updated_at = ? 
                WHERE id = ? AND user_id = ?
            ''', (title, current_time, session_id, user_id))
        
        # Save new messages (only save the last message to avoid duplicates)
        if messages:
            latest_message = messages[-1]
            cursor.execute('''
                INSERT INTO chat_messages (session_id, message, sender, created_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, latest_message['text'], latest_message['sender'], current_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved chat session {session_id} for user {user_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'title': title
        })
        
    except Exception as e:
        logger.error(f"Error saving chat session: {str(e)}")
        return jsonify({'error': 'Failed to save chat session'}), 500

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