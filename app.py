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

# Global dictionaries for bot management
user_bots = {}
user_bot_threads = {}

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

@app.route('/api/api-keys')
@login_required
def api_api_keys():
    """Get user's API keys"""
    try:
        api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': key.id,
            'exchange_name': key.exchange_name,
            'is_sandbox': key.is_sandbox,
            'created_at': key.created_at.strftime('%m/%d/%Y')
        } for key in api_keys])
    except Exception as e:
        print(f"API keys error: {str(e)}")
        return jsonify([])

@app.route('/api/bot-config')
@login_required
def api_bot_config():
    """Get user's bot configurations"""
    try:
        configs = BotConfig.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': config.id,
            'name': config.name,
            'is_active': config.is_active,
            'created_at': config.created_at.strftime('%m/%d/%Y'),
            'config_data': json.loads(config.config_json) if config.config_json else {}
        } for config in configs])
    except Exception as e:
        print(f"Bot config error: {str(e)}")
        return jsonify([])

@app.route('/api/trades')
@login_required
def api_trades():
    """Get user's trade history"""
    try:
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
    except Exception as e:
        print(f"Trades error: {str(e)}")
        return jsonify({'trades': [], 'total': 0})

# Also fix the settings route to handle the POST properly
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            data = request.get_json()
            print(f"Settings POST data: {data}")  # Debug log
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            action = data.get('action')
            
            if action == 'save_api_keys':
                exchange = data.get('exchange')
                api_key = data.get('api_key')
                secret_key = data.get('secret_key')
                is_sandbox = data.get('is_sandbox', True)
                
                print(f"Saving API keys: {exchange}, sandbox: {is_sandbox}")  # Debug
                
                if not exchange or not api_key or not secret_key:
                    return jsonify({'error': 'All fields are required'}), 400
                
                try:
                    # Delete existing API key for this exchange
                    existing = APIKey.query.filter_by(user_id=current_user.id, exchange_name=exchange).first()
                    if existing:
                        db.session.delete(existing)
                    
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
                    
                    print("API key saved successfully!")  # Debug
                    return jsonify({'success': True})
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"Database error: {str(e)}")
                    return jsonify({'error': f'Database error: {str(e)}'}), 500
            
            elif action == 'save_bot_config':
                strategies = data.get('strategies', [])
                symbols = data.get('symbols', [])
                
                print(f"Saving bot config: strategies={strategies}, symbols={symbols}")  # Debug
                
                if not strategies:
                    return jsonify({'error': 'Please select at least one strategy'}), 400
                
                if not symbols:
                    return jsonify({'error': 'Please select at least one symbol'}), 400
                
                try:
                    # Create config data
                    config_data = {
                        'strategies': [{'type': s} for s in strategies],
                        'symbols': [{'symbol': s, 'exchange': 'coinbase'} for s in symbols],
                        'cycle_interval': 300
                    }
                    
                    # Deactivate old configs
                    old_configs = BotConfig.query.filter_by(user_id=current_user.id, is_active=True).all()
                    for config in old_configs:
                        config.is_active = False
                    
                    # Create new config
                    from datetime import datetime
                    bot_config = BotConfig(
                        user_id=current_user.id,
                        name=f'Config {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}',
                        config_json=json.dumps(config_data),
                        is_active=True
                    )
                    
                    db.session.add(bot_config)
                    db.session.commit()
                    
                    print("Bot config saved successfully!")  # Debug
                    return jsonify({'success': True})
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"Config save error: {str(e)}")
                    return jsonify({'error': f'Database error: {str(e)}'}), 500
            
            else:
                return jsonify({'error': f'Unknown action: {action}'}), 400
                
        except Exception as e:
            print(f"Settings error: {str(e)}")
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    
    # GET request
    return render_template('settings.html', user=current_user)

# Bot control endpoints
@app.route('/bot/start', methods=['POST'])
@login_required
def start_bot():
    """Start the user's trading bot"""
    try:
        user_id = current_user.id
        
        # Check if bot is already running
        if user_id in user_bots and user_bot_threads.get(user_id) and user_bot_threads[user_id].is_alive():
            return jsonify({'error': 'Bot is already running'}), 400
        
        # Check subscription
        if not current_user.is_subscription_active():
            return jsonify({'error': 'Active subscription required'}), 403
        
        print(f"🚀 Starting bot for user {current_user.username} (ID: {user_id})")
        
        # Get user's API keys
        api_keys = APIKey.query.filter_by(user_id=user_id).all()
        if not api_keys:
            return jsonify({'error': 'No API keys configured. Please add your exchange API keys in Settings.'}), 400
        
        print(f"✅ Found {len(api_keys)} API keys")
        
        # Get user's active bot config
        bot_config = BotConfig.query.filter_by(user_id=user_id, is_active=True).first()
        if not bot_config:
            return jsonify({'error': 'No bot configuration found. Please configure your strategies in Settings.'}), 400
        
        print(f"✅ Found active bot config: {bot_config.name}")
        
        # Parse the config
        try:
            config_data = json.loads(bot_config.config_json)
            print(f"✅ Config parsed: {len(config_data.get('strategies', []))} strategies, {len(config_data.get('symbols', []))} symbols")
        except Exception as e:
            return jsonify({'error': f'Invalid bot configuration: {str(e)}'}), 400
        
        # Build the trading bot config
        trading_config = {
            'exchanges': [],
            'strategies': config_data.get('strategies', []),
            'symbols': config_data.get('symbols', []),
            'cycle_interval': config_data.get('cycle_interval', 300)
        }
        
        # Add exchange configurations
        for api_key in api_keys:
            exchange_config = {
                'name': api_key.exchange_name,
                'api_key': api_key.api_key,
                'secret': api_key.secret_key,
                'sandbox': api_key.is_sandbox
            }
            trading_config['exchanges'].append(exchange_config)
        
        print(f"✅ Trading config built with {len(trading_config['exchanges'])} exchanges")
        
        # Create the trading bot
        from core_engine import TradingBot
        bot = TradingBot(trading_config)
        print("✅ Trading bot created successfully")
        
        # Test the bot with one analysis cycle first
        print("🧪 Testing bot with one analysis cycle...")
        try:
            bot.run_analysis_cycle()
            print("✅ Test analysis cycle completed successfully")
        except Exception as e:
            print(f"❌ Test analysis failed: {e}")
            return jsonify({'error': f'Bot test failed: {str(e)}'}), 500
        
        # Store the bot instance
        user_bots[user_id] = bot
        
        # Create a function to run the bot continuously
        def run_bot_continuously():
            try:
                print(f"🔄 Starting continuous bot for user {user_id}")
                
                # Override execute_signal for safety if in sandbox mode
                original_execute = bot.execute_signal
                def safe_execute_signal(signal, exchange_name):
                    # Check if any exchange is in sandbox mode
                    exchange = bot.exchanges.get(exchange_name)
                    if exchange and exchange.sandbox:
                        print(f"🛡️ SAFE MODE: {signal.action.value.upper()} {signal.symbol} at ${signal.price:.2f} (SIMULATED)")
                        
                        # Create a simulated trade record
                        try:
                            trade_record = TradeRecord(
                                user_id=user_id,
                                symbol=signal.symbol,
                                side=signal.action.value,
                                amount=0.001,  # Small simulated amount
                                price=signal.price,
                                strategy=signal.strategy.value,
                                exchange=exchange_name,
                                order_id=f'SIM_{int(time.time())}',
                                status='simulated',
                                pnl=0.0
                            )
                            db.session.add(trade_record)
                            db.session.commit()
                            print(f"✅ Simulated trade recorded")
                        except Exception as e:
                            print(f"⚠️ Failed to record simulated trade: {e}")
                    else:
                        # Real trading - call original method
                        print(f"🚨 LIVE TRADE: {signal.action.value.upper()} {signal.symbol} at ${signal.price:.2f}")
                        original_execute(signal, exchange_name)
                
                bot.execute_signal = safe_execute_signal
                
                # Run the bot
                while user_id in user_bots:
                    try:
                        print(f"🔄 Running analysis cycle for user {user_id}")
                        bot.run_analysis_cycle()
                        
                        # Sleep for the configured interval
                        sleep_time = trading_config.get('cycle_interval', 300)
                        print(f"😴 Sleeping for {sleep_time} seconds...")
                        
                        # Sleep in small chunks so we can stop quickly
                        for _ in range(sleep_time):
                            if user_id not in user_bots:
                                break
                            time.sleep(1)
                            
                    except Exception as e:
                        print(f"❌ Error in bot cycle for user {user_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        time.sleep(60)  # Wait 1 minute before retrying
                        
                print(f"🛑 Bot stopped for user {user_id}")
                
            except Exception as e:
                print(f"❌ Bot thread error for user {user_id}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Clean up
                if user_id in user_bots:
                    del user_bots[user_id]
                if user_id in user_bot_threads:
                    del user_bot_threads[user_id]
        
        # Start the bot in a separate thread
        bot_thread = threading.Thread(target=run_bot_continuously, daemon=True)
        bot_thread.start()
        user_bot_threads[user_id] = bot_thread
        
        print(f"✅ Bot thread started for user {user_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Trading bot started successfully!',
            'status': 'running'
        })
        
    except Exception as e:
        print(f"❌ Failed to start bot for user {current_user.id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to start bot: {str(e)}'}), 500

@app.route('/bot/stop', methods=['POST'])
@login_required
def stop_bot():
    """Stop the user's trading bot"""
    try:
        user_id = current_user.id
        
        print(f"🛑 Stopping bot for user {current_user.username} (ID: {user_id})")
        
        # Check if bot is running
        if user_id not in user_bots:
            return jsonify({'error': 'Bot is not running'}), 400
        
        # Stop the bot by removing it from the dictionary
        if user_id in user_bots:
            print(f"✅ Removed bot from active bots")
            del user_bots[user_id]
        
        # Wait a moment for the thread to finish
        if user_id in user_bot_threads:
            thread = user_bot_threads[user_id]
            if thread.is_alive():
                print("⏳ Waiting for bot thread to finish...")
                thread.join(timeout=5)  # Wait up to 5 seconds
            del user_bot_threads[user_id]
        
        print(f"✅ Bot stopped for user {user_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Trading bot stopped successfully!',
            'status': 'stopped'
        })
        
    except Exception as e:
        print(f"❌ Failed to stop bot for user {current_user.id}: {str(e)}")
        return jsonify({'error': f'Failed to stop bot: {str(e)}'}), 500
    
@app.route('/bot/status')
@login_required
def bot_status():
    """Get bot status for user"""
    try:
        user_id = current_user.id
        
        # Check if bot is running
        is_running = (user_id in user_bots and 
                     user_id in user_bot_threads and 
                     user_bot_threads[user_id].is_alive())
        
        # Get some basic stats
        total_trades = TradeRecord.query.filter_by(user_id=user_id).count()
        
        return jsonify({
            'running': is_running,
            'subscription_active': current_user.is_subscription_active(),
            'tier': current_user.subscription_tier,
            'total_trades': total_trades,
            'user_id': user_id  # For debugging
        })
        
    except Exception as e:
        print(f"❌ Bot status error for user {current_user.id}: {e}")
        return jsonify({
            'running': False,
            'subscription_active': False,
            'tier': 'free',
            'error': str(e)
        })
# Also add a route to see all running bots (for debugging)
@app.route('/admin/bots')
@login_required
def admin_bots():
    """Admin view of all running bots"""
    if current_user.subscription_tier != 'enterprise':
        return jsonify({'error': 'Admin access required'}), 403
    
    running_bots = []
    for user_id, bot in user_bots.items():
        user = User.query.get(user_id)
        thread = user_bot_threads.get(user_id)
        
        running_bots.append({
            'user_id': user_id,
            'username': user.username if user else 'Unknown',
            'thread_alive': thread.is_alive() if thread else False,
            'strategies': len(bot.strategies) if bot else 0,
            'exchanges': len(bot.exchanges) if bot else 0
        })
    
    return jsonify({
        'total_running_bots': len(user_bots),
        'bots': running_bots
    })

# Clean up function when app shuts down
import atexit

def cleanup_bots():
    """Clean up all running bots when app shuts down"""
    print("🧹 Cleaning up all running bots...")
    global user_bots, user_bot_threads
    
    # Stop all bots
    for user_id in list(user_bots.keys()):
        if user_id in user_bots:
            del user_bots[user_id]
    
    # Wait for threads to finish
    for user_id, thread in user_bot_threads.items():
        if thread.is_alive():
            thread.join(timeout=2)
    
    user_bot_threads.clear()
    print("✅ All bots cleaned up")

atexit.register(cleanup_bots)

@app.route('/bot/test')
@login_required
def test_bot_setup():
    """Test what's available for bot setup"""
    try:
        user_id = current_user.id
        
        # Check API keys
        api_keys = APIKey.query.filter_by(user_id=user_id).all()
        
        # Check bot config
        bot_config = BotConfig.query.filter_by(user_id=user_id, is_active=True).first()
        
        # Check imports
        try:
            from core_engine import TradingBot
            trading_bot_available = True
        except Exception as e:
            trading_bot_available = str(e)
        
        return jsonify({
            'user_id': user_id,
            'api_keys_count': len(api_keys),
            'has_bot_config': bot_config is not None,
            'trading_bot_available': trading_bot_available,
            'subscription_active': current_user.is_subscription_active()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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