from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import os
from enum import Enum
import threading
import time
from core_engine import TradingBot, TradingStrategy
from config import DEFAULT_CONFIG
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Production database URL
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///trading_bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Subscription Tiers
class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

# Tier configurations
TIER_CONFIG = {
    SubscriptionTier.FREE: {
        'name': 'Free',
        'price': 0,
        'max_strategies': 0,
        'max_symbols': 0,
        'signals_per_hour': 0,
        'features': ['View dashboard', 'Market analysis'],
        'stripe_price_id': None
    },
    SubscriptionTier.BASIC: {
        'name': 'Basic',
        'price': 19,
        'max_strategies': 2,
        'max_symbols': 5,
        'signals_per_hour': 10,
        'features': ['SMA Strategy', 'RSI Strategy', '5 coins', '10 signals/hour'],
        'stripe_price_id': 'price_basic_monthly'
    },
    SubscriptionTier.PRO: {
        'name': 'Pro',
        'price': 49,
        'max_strategies': 5,
        'max_symbols': 20,
        'signals_per_hour': 50,
        'features': ['All Basic features', 'MACD Strategy', 'Bollinger Bands', '20 coins', '50 signals/hour', 'Custom parameters'],
        'stripe_price_id': 'price_pro_monthly'
    },
    SubscriptionTier.PREMIUM: {
        'name': 'Premium',
        'price': 99,
        'max_strategies': 10,
        'max_symbols': -1,  # Unlimited
        'signals_per_hour': -1,  # Unlimited
        'features': ['All Pro features', 'Advanced strategies', 'Unlimited coins', 'Unlimited signals', 'Portfolio management'],
        'stripe_price_id': 'price_premium_monthly'
    },
    SubscriptionTier.ENTERPRISE: {
        'name': 'Enterprise',
        'price': 199,
        'max_strategies': -1,  # Unlimited
        'max_symbols': -1,  # Unlimited
        'signals_per_hour': -1,  # Unlimited
        'features': ['All Premium features', 'Multi-exchange', 'Advanced risk controls', 'Priority support', 'Custom strategies'],
        'stripe_price_id': 'price_enterprise_monthly'
    }
}

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    subscription_tier = db.Column(db.String(20), default=SubscriptionTier.FREE.value)
    subscription_active = db.Column(db.Boolean, default=False)
    subscription_expires = db.Column(db.DateTime)
    stripe_customer_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Trading settings
    api_keys = db.relationship('APIKey', backref='user', lazy=True)
    bot_configs = db.relationship('BotConfig', backref='user', lazy=True)
    trade_history = db.relationship('TradeRecord', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_tier_config(self):
        return TIER_CONFIG.get(SubscriptionTier(self.subscription_tier), TIER_CONFIG[SubscriptionTier.FREE])
    
    def can_access_feature(self, feature_name):
        tier_config = self.get_tier_config()
        return feature_name in tier_config.get('allowed_features', [])
    
    def is_subscription_active(self):
        if not self.subscription_active:
            return False
        if self.subscription_expires and self.subscription_expires < datetime.utcnow():
            return False
        return True

class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exchange_name = db.Column(db.String(50), nullable=False)
    api_key = db.Column(db.String(200), nullable=False)
    secret_key = db.Column(db.String(200), nullable=False)
    is_sandbox = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BotConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    config_json = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TradeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    strategy = db.Column(db.String(50), nullable=False)
    exchange = db.Column(db.String(50), nullable=False)
    order_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    pnl = db.Column(db.Float, default=0.0)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)

# Global bot instances
user_bots = {}  # Dictionary to store active bots per user

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html', tier_config=TIER_CONFIG)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validation
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('auth.html', mode='login')

@app.route('/logout')
@login_required
def logout():
    # Stop user's bot if running
    if current_user.id in user_bots:
        user_bots[current_user.id].stop()
        del user_bots[current_user.id]
    
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's trading stats
    recent_trades = TradeRecord.query.filter_by(user_id=current_user.id).order_by(TradeRecord.executed_at.desc()).limit(10).all()
    
    # Calculate basic stats
    total_trades = TradeRecord.query.filter_by(user_id=current_user.id).count()
    total_pnl = db.session.query(db.func.sum(TradeRecord.pnl)).filter_by(user_id=current_user.id).scalar() or 0
    
    bot_status = 'running' if current_user.id in user_bots else 'stopped'
    
    return render_template('dashboard.html', 
                         user=current_user,
                         recent_trades=recent_trades,
                         total_trades=total_trades,
                         total_pnl=total_pnl,
                         bot_status=bot_status,
                         tier_config=current_user.get_tier_config())

@app.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html', 
                         user=current_user,
                         tier_config=TIER_CONFIG,
                         current_tier=current_user.get_tier_config())

@app.route('/upgrade/<tier>', methods=['POST'])
@login_required
def upgrade_subscription(tier):
    try:
        tier_enum = SubscriptionTier(tier)
        tier_config = TIER_CONFIG[tier_enum]
        
        if not tier_config['stripe_price_id']:
            return jsonify({'error': 'Invalid tier'}), 400
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': tier_config['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('subscription_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('subscription', _external=True),
            metadata={
                'user_id': current_user.id,
                'tier': tier
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/subscription/success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                # Update user subscription
                tier = session.metadata['tier']
                current_user.subscription_tier = tier
                current_user.subscription_active = True
                current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
                current_user.stripe_customer_id = session.customer
                db.session.commit()
                
                flash('Subscription activated successfully!', 'success')
            
        except Exception as e:
            flash('Error processing subscription. Please contact support.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        data = request.get_json()
        
        if data.get('action') == 'save_api_keys':
            # Save API keys
            exchange = data.get('exchange')
            api_key = data.get('api_key')
            secret_key = data.get('secret_key')
            is_sandbox = data.get('is_sandbox', True)
            
            # Delete existing API key for this exchange
            APIKey.query.filter_by(user_id=current_user.id, exchange_name=exchange).delete()
            
            # Add new API key
            new_api_key = APIKey(
                user_id=current_user.id,
                exchange_name=exchange,
                api_key=api_key,
                secret_key=secret_key,
                is_sandbox=is_sandbox
            )
            db.session.add(new_api_key)
            db.session.commit()
            
            return jsonify({'success': True})
        
        elif data.get('action') == 'save_bot_config':
            # Save bot configuration
            config_name = data.get('name', 'Default Config')
            strategies = data.get('strategies', [])
            symbols = data.get('symbols', [])
            
            # Validate against user's tier limits
            tier_config = current_user.get_tier_config()
            
            if len(strategies) > tier_config['max_strategies'] and tier_config['max_strategies'] != -1:
                return jsonify({'error': f'Too many strategies for your tier. Limit: {tier_config["max_strategies"]}'}), 400
            
            if len(symbols) > tier_config['max_symbols'] and tier_config['max_symbols'] != -1:
                return jsonify({'error': f'Too many symbols for your tier. Limit: {tier_config["max_symbols"]}'}), 400
            
            # Create bot config
            config_data = {
                'strategies': strategies,
                'symbols': symbols,
                'cycle_interval': data.get('cycle_interval', 300)
            }
            
            # Deactivate old configs
            BotConfig.query.filter_by(user_id=current_user.id, is_active=True).update({'is_active': False})
            
            # Create new config
            bot_config = BotConfig(
                user_id=current_user.id,
                name=config_name,
                config_json=json.dumps(config_data),
                is_active=True
            )
            db.session.add(bot_config)
            db.session.commit()
            
            return jsonify({'success': True})
    
    # Get user's API keys and configs
    api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
    bot_configs = BotConfig.query.filter_by(user_id=current_user.id).all()
    
    return render_template('settings.html', 
                         user=current_user,
                         api_keys=api_keys,
                         bot_configs=bot_configs,
                         tier_config=current_user.get_tier_config())

@app.route('/bot/start', methods=['POST'])
@login_required
def start_bot():
    if not current_user.is_subscription_active():
        return jsonify({'error': 'Active subscription required'}), 403
    
    if current_user.id in user_bots:
        return jsonify({'error': 'Bot already running'}), 400
    
    try:
        # Get user's active config
        bot_config = BotConfig.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not bot_config:
            return jsonify({'error': 'No bot configuration found'}), 400
        
        # Get user's API keys
        api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
        if not api_keys:
            return jsonify({'error': 'No API keys configured'}), 400
        
        # Build config for trading bot
        config = json.loads(bot_config.config_json)
        config['exchanges'] = []
        
        for api_key in api_keys:
            config['exchanges'].append({
                'name': api_key.exchange_name,
                'api_key': api_key.api_key,
                'secret': api_key.secret_key,
                'sandbox': api_key.is_sandbox
            })
        
        # Create and start bot in separate thread
        bot = TradingBot(config)
        
        def run_bot():
            try:
                bot.start()
            except Exception as e:
                print(f"Bot error for user {current_user.id}: {e}")
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        user_bots[current_user.id] = bot
        
        return jsonify({'success': True, 'status': 'running'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/bot/stop', methods=['POST'])
@login_required
def stop_bot():
    if current_user.id not in user_bots:
        return jsonify({'error': 'Bot not running'}), 400
    
    try:
        user_bots[current_user.id].stop()
        del user_bots[current_user.id]
        return jsonify({'success': True, 'status': 'stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/bot/status')
@login_required
def bot_status():
    is_running = current_user.id in user_bots
    
    status_data = {
        'running': is_running,
        'subscription_active': current_user.is_subscription_active(),
        'tier': current_user.subscription_tier
    }
    
    if is_running:
        bot = user_bots[current_user.id]
        stats = bot.get_performance_stats()
        status_data.update(stats)
    
    return jsonify(status_data)

@app.route('/api/trades')
@login_required
def api_trades():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    trades = TradeRecord.query.filter_by(user_id=current_user.id)\
                             .order_by(TradeRecord.executed_at.desc())\
                             .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'trades': [{
            'id': trade.id,
            'symbol': trade.symbol,
            'side': trade.side,
            'amount': trade.amount,
            'price': trade.price,
            'strategy': trade.strategy,
            'exchange': trade.exchange,
            'pnl': trade.pnl,
            'status': trade.status,
            'executed_at': trade.executed_at.isoformat()
        } for trade in trades.items],
        'has_next': trades.has_next,
        'has_prev': trades.has_prev,
        'total': trades.total
    })

# Webhook for Stripe events
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_ENDPOINT_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    # Handle subscription events
    if event['type'] == 'invoice.payment_succeeded':
        # Subscription renewed
        subscription_id = event['data']['object']['subscription']
        # Update user subscription...
        
    elif event['type'] == 'invoice.payment_failed':
        # Payment failed
        subscription_id = event['data']['object']['subscription']
        # Deactivate user subscription...
    
    return 'Success', 200

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    # Create tables before running
    create_tables()
    app.run(debug=True)