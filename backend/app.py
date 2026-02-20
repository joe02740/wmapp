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

# Initialize Stripe
app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
if app.config['STRIPE_SECRET_KEY']:
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
stripe_price_id_paid = os.getenv('STRIPE_PRICE_ID_PAID')

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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage 
            WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE
        ''', (user_id,))
        today_count = cursor.fetchone()[0]
        
        # Get monthly usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage 
            WHERE user_id = %s AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        ''', (user_id,))
        month_count = cursor.fetchone()[0]
        
        # Get total usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage WHERE user_id = %s
        ''', (user_id,))
        total_count = cursor.fetchone()[0]
        
        # Get recent queries (last 15)
        cursor.execute('''
            SELECT query, scope, tokens_used, created_at 
            FROM usage 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 15
        ''', (user_id,))
        recent_queries = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Define limits based on tier (UPDATED)
        limits = {
            'free': {'daily': 2, 'monthly': 6},
            'paid': {'daily': 25, 'monthly': 75}  # Updated from 50/500 to 25/75
        }
        
        user_limits = limits.get(user['subscription_tier'], limits['free'])
        
        return jsonify({
            'user_id': user_id,
            'subscription_tier': user['subscription_tier'],
            'subscription_end_date': user['subscription_end_date'],
            'usage': {
                'daily': today_count,
                'daily_limit': user_limits['daily'],
                'monthly': month_count,
                'monthly_limit': user_limits['monthly'],
                'total': total_count
            },
            'recent_queries': [
                {
                    'query': row[0],
                    'scope': row[1],
                    'tokens_used': row[2],
                    'created_at': row[3].isoformat() if row[3] else ''
                }
                for row in recent_queries
            ]
        })
        
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

print("7. Checkout session route defined")

@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, created_at, updated_at 
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY updated_at DESC
        ''', (user_id,))
        
        sessions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'sessions': [
                {
                    'id': row[0],
                    'title': row[1],
                    'created_at': row[2].isoformat() if row[2] else '',
                    'updated_at': row[3].isoformat() if row[3] else ''
                }
                for row in sessions
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in get_chat_history: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

print("8. Chat history route defined")

@app.route('/api/chat-session/<int:session_id>', methods=['GET'])
def get_chat_session(session_id):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute('''
            SELECT title, created_at 
            FROM chat_sessions 
            WHERE id = %s AND user_id = %s
        ''', (session_id, user_id))
        
        session = cursor.fetchone()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get messages from separate table
        cursor.execute('''
            SELECT message, sender, created_at 
            FROM chat_messages 
            WHERE session_id = %s 
            ORDER BY created_at ASC
        ''', (session_id,))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'title': session[0],
            'created_at': session[1].isoformat() if session[1] else '',
            'messages': [
                {
                    'text': row[0],
                    'sender': row[1]
                }
                for row in messages
            ]
        })
        
    except Exception as e:
        logger.error(f"Error loading chat session: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

print("9. Chat session get route defined")

@app.route('/api/chat-session', methods=['POST'])
def save_chat_session():
    data = request.json
    user_id = data.get('user_id')
    session_id = data.get('session_id')
    title = data.get('title')
    messages = data.get('messages', [])
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        
        if session_id:
            # Update existing session
            cursor.execute('''
                UPDATE chat_sessions 
                SET title = %s, updated_at = %s 
                WHERE id = %s AND user_id = %s
            ''', (title, current_time, session_id, user_id))
        else:
            # Create new session
            cursor.execute('''
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (user_id, title, current_time, current_time))
            session_id = cursor.fetchone()[0]
        
        # Clear existing messages for this session
        cursor.execute('DELETE FROM chat_messages WHERE session_id = %s', (session_id,))
        
        # Insert new messages into separate table
        for msg in messages:
            cursor.execute('''
                INSERT INTO chat_messages (session_id, message, sender, created_at)
                VALUES (%s, %s, %s, %s)
            ''', (session_id, msg.get('text'), msg.get('sender'), current_time))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'session_id': session_id,
            'title': title,
            'message': 'Chat session saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving chat session: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

print("10. Save chat session route defined")

@app.route('/api/query', methods=['POST'])
def handle_query():
    logger.info("=== QUERY ROUTE CALLED ===")
    data = request.json
    user_query = data.get('query')
    scope = data.get('scope', 'mass_laws')
    user_id = data.get('user_id')
    conversation_history = data.get('conversation_history', [])
    
    logger.info(f"Query: {user_query[:50]}... | User: {user_id} | Scope: {scope} | History: {len(conversation_history)} messages")
    
    if not user_query or not user_id:
        return jsonify({'error': 'Query and user ID are required'}), 400
    
    try:
        # Check usage limits
        can_use, limit_message = check_usage_limit(user_id)
        if not can_use:
            return jsonify({'response': limit_message}), 429
        
        if not app.config['ANTHROPIC_API_KEY']:
            return jsonify({'error': 'Anthropic API key not configured'}), 500
            
        # Read the appropriate laws/handbook file based on scope
        file_path = os.path.join(os.path.dirname(__file__), 'data', 'mass_weights_measures_laws.txt')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                laws_text = file.read()
                logger.info(f"Loaded laws file: {len(laws_text)} characters")
        except FileNotFoundError:
            logger.error(f"Laws file not found at: {file_path}")
            return jsonify({'error': 'Laws file not found. Please contact support.'}), 500
            
        # Create Anthropic client
        client = anthropic.Anthropic(api_key=app.config['ANTHROPIC_API_KEY'])
        
        # Build user context from past conversations
        user_context = build_user_context(user_id, exclude_session_id=data.get('session_id'))
        
        # Build the base system instruction with optional user context
        system_instruction = "You are an AI assistant specialized in Massachusetts weights and measures laws. Provide accurate and helpful information based on the given context. Please also assume you are chatting with someone who is a Weights and Measures official. When referencing specific laws or regulations, cite the section numbers. You have full conversation history, so feel free to reference previous questions and answers in this chat.\n"
        
        if user_context:
            system_instruction += f"\n{user_context}\n"
            logger.info("Injected user context into system prompt")
        
        # Build conversation messages with full history for multi-turn memory
        claude_messages = []
        for msg in conversation_history:
            role = 'user' if msg.get('sender') == 'user' else 'assistant'
            text = msg.get('text', '')
            if text:  # Skip empty messages
                claude_messages.append({"role": role, "content": text})
        
        # Add the current user query
        claude_messages.append({"role": "user", "content": user_query})
        
        # Ensure messages alternate properly (Claude requires user/assistant alternation)
        # Merge consecutive same-role messages if any
        cleaned_messages = []
        for msg in claude_messages:
            if cleaned_messages and cleaned_messages[-1]["role"] == msg["role"]:
                cleaned_messages[-1]["content"] += "\n" + msg["content"]
            else:
                cleaned_messages.append(msg)
        
        # Ensure first message is from user
        if cleaned_messages and cleaned_messages[0]["role"] != "user":
            cleaned_messages = cleaned_messages[1:]
        
        logger.info(f"Sending {len(cleaned_messages)} messages to Claude (with conversation history)")
        
        # Make the Claude query with prompt caching (Claude Sonnet 4.5)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": system_instruction
                },
                {
                    "type": "text", 
                    "text": laws_text,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=cleaned_messages
        )
        
        response_text = response.content[0].text
        logger.info(f"Got response: {len(response_text)} characters")
        
        # Log cache performance
        if hasattr(response, 'usage'):
            cache_creation = getattr(response.usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(response.usage, 'cache_read_input_tokens', 0)
            logger.info(f"Cache stats - creation: {cache_creation}, read: {cache_read}")
        
        # Record usage
        tokens_used = response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else len(user_query.split()) * 2
        record_usage(user_id, user_query, scope, tokens_used)
        
        return jsonify({
            "type": "mass_laws", 
            "response": response_text
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e)
        }), 500

print("11. Query route defined")

# Helper functions
def build_user_context(user_id, exclude_session_id=None):
    """
    Build a weighted summary of the user's past chat sessions.
    Recent sessions get more detail, older ones just get the topic.
    Returns a string to inject into the system prompt, or empty string if no history.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the user's last 15 chat sessions (excluding current one)
        if exclude_session_id:
            cursor.execute('''
                SELECT cs.id, cs.title, cs.updated_at,
                       COUNT(cm.id) as msg_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cm.session_id = cs.id
                WHERE cs.user_id = %s AND cs.id != %s
                GROUP BY cs.id, cs.title, cs.updated_at
                ORDER BY cs.updated_at DESC
                LIMIT 15
            ''', (user_id, exclude_session_id))
        else:
            cursor.execute('''
                SELECT cs.id, cs.title, cs.updated_at,
                       COUNT(cm.id) as msg_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cm.session_id = cs.id
                WHERE cs.user_id = %s
                GROUP BY cs.id, cs.title, cs.updated_at
                ORDER BY cs.updated_at DESC
                LIMIT 15
            ''', (user_id,))
        
        sessions = cursor.fetchall()
        
        if not sessions:
            cursor.close()
            conn.close()
            return ""
        
        summary_parts = []
        
        for i, (session_id, title, updated_at, msg_count) in enumerate(sessions):
            date_str = updated_at.strftime('%b %d, %Y') if updated_at else 'Unknown date'
            
            if i < 3:
                # RECENT (last 3 sessions): Include title + key Q&A snippets
                cursor.execute('''
                    SELECT message, sender FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    LIMIT 6
                ''', (session_id,))
                msgs = cursor.fetchall()
                
                # Build a compact summary of the conversation
                key_points = []
                for msg_text, sender in msgs:
                    if sender == 'user' and msg_text:
                        # Truncate long questions
                        snippet = msg_text[:120] + '...' if len(msg_text) > 120 else msg_text
                        key_points.append(f"  Asked: {snippet}")
                    elif sender == 'ai' and msg_text:
                        # Just grab the first sentence or two of the AI response
                        first_part = msg_text[:150].split('. ')
                        brief = '. '.join(first_part[:2])
                        if not brief.endswith('.'):
                            brief += '...'
                        key_points.append(f"  Answer summary: {brief}")
                
                points_str = '\n'.join(key_points[:4])  # Max 4 points per session
                summary_parts.append(f"[{date_str}] {title}\n{points_str}")
            
            elif i < 8:
                # MEDIUM (sessions 4-8): Title + first question only
                cursor.execute('''
                    SELECT message FROM chat_messages
                    WHERE session_id = %s AND sender = 'user'
                    ORDER BY created_at ASC
                    LIMIT 1
                ''', (session_id,))
                first_q = cursor.fetchone()
                q_text = ""
                if first_q and first_q[0]:
                    q_text = first_q[0][:80] + '...' if len(first_q[0]) > 80 else first_q[0]
                    q_text = f" - Asked: {q_text}"
                summary_parts.append(f"[{date_str}] {title}{q_text}")
            
            else:
                # OLDER (sessions 9-15): Just the title/topic
                summary_parts.append(f"[{date_str}] {title}")
        
        cursor.close()
        conn.close()
        
        if not summary_parts:
            return ""
        
        context = "=== USER'S PAST CONVERSATION HISTORY (most recent first) ===\n"
        context += "This official has previously asked about the following topics. "
        context += "Use this context to provide more personalized and relevant answers.\n\n"
        context += "\n\n".join(summary_parts)
        
        logger.info(f"Built user context for {user_id}: {len(summary_parts)} sessions, {len(context)} chars")
        return context
        
    except Exception as e:
        logger.error(f"Error building user context: {str(e)}")
        return ""  # Fail gracefully - don't block the query

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
            WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE
        ''', (user_id,))
        today_count = cursor.fetchone()[0]
        # Get monthly usage
        cursor.execute('''
            SELECT COUNT(*) FROM usage 
            WHERE user_id = %s AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        ''', (user_id,))
        month_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        # Updated limits based on new pricing
        limits = {
            'free': {'daily': 2, 'monthly': 6},
            'paid': {'daily': 25, 'monthly': 75}  # Updated from 50/500 to 25/75
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
    # Only enable debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    # Get port from environment variable for production deployment
    port = int(os.environ.get("PORT", 5000))
    
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)