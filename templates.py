import os

def create_templates():
    """Create all HTML template files for the Flask app"""
    
    # Create templates directory
    os.makedirs('templates', exist_ok=True)
    print("📁 Created templates directory")
    
    # Base template
    base_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}CryptoBot Pro{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Navigation -->
    {% if current_user.is_authenticated %}
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-bold text-gray-900">CryptoBot Pro</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Dashboard</a>
                    <a href="{{ url_for('settings') }}" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Settings</a>
                    <a href="{{ url_for('subscription') }}" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Subscription</a>
                    <div class="flex items-center space-x-2">
                        <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">{{ current_user.subscription_tier.title() }}</span>
                        <a href="{{ url_for('logout') }}" class="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">Logout</a>
                    </div>
                </div>
            </div>
        </div>
    </nav>
    {% endif %}

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                {% for category, message in messages %}
                    <div class="p-4 rounded-md {% if category == 'error' %}bg-red-50 text-red-800{% else %}bg-green-50 text-green-800{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {% block content %}{% endblock %}
    </main>
</body>
</html>'''
    
    # Landing page
    landing_html = '''{% extends "base.html" %}

{% block content %}
<div class="bg-gradient-to-br from-blue-900 to-purple-900 text-white">
    <div class="max-w-7xl mx-auto px-4 py-20 text-center">
        <h1 class="text-5xl font-bold mb-6">Automated Crypto Trading Made Simple</h1>
        <p class="text-xl mb-8 max-w-2xl mx-auto">Professional-grade trading bots with customizable strategies. Start trading smarter, not harder.</p>
        
        <div class="flex justify-center space-x-4">
            <a href="{{ url_for('register') }}" class="bg-white text-blue-900 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100">Get Started Free</a>
            <a href="{{ url_for('login') }}" class="border border-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-900">Sign In</a>
        </div>
    </div>
</div>

<!-- Pricing Section -->
<div class="py-20 bg-gray-50">
    <div class="max-w-7xl mx-auto px-4">
        <h2 class="text-3xl font-bold text-center mb-12">Choose Your Trading Plan</h2>
        
        <div class="grid md:grid-cols-4 gap-8">
            <!-- Basic Plan -->
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h3 class="text-xl font-bold mb-2">Basic</h3>
                <div class="text-3xl font-bold mb-4">$19<span class="text-sm text-gray-500">/month</span></div>
                
                <ul class="space-y-2 mb-6">
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        2 Strategies (SMA, RSI)
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        5 Trading Symbols
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        10 Signals per hour
                    </li>
                </ul>
                
                <a href="{{ url_for('register') }}" class="block w-full bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700">
                    Start Free Trial
                </a>
            </div>

            <!-- Pro Plan -->
            <div class="bg-white rounded-lg shadow-lg p-6 ring-2 ring-blue-500 transform scale-105">
                <div class="bg-blue-500 text-white text-center py-2 text-sm font-medium -m-6 mb-4 rounded-t-lg">Most Popular</div>
                <h3 class="text-xl font-bold mb-2">Pro</h3>
                <div class="text-3xl font-bold mb-4">$49<span class="text-sm text-gray-500">/month</span></div>
                
                <ul class="space-y-2 mb-6">
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        5 Strategies + MACD
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        20 Trading Symbols
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        50 Signals per hour
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Custom Parameters
                    </li>
                </ul>
                
                <a href="{{ url_for('register') }}" class="block w-full bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700">
                    Get Started
                </a>
            </div>

            <!-- Premium Plan -->
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h3 class="text-xl font-bold mb-2">Premium</h3>
                <div class="text-3xl font-bold mb-4">$99<span class="text-sm text-gray-500">/month</span></div>
                
                <ul class="space-y-2 mb-6">
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        All Strategies
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Unlimited Symbols
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Unlimited Signals
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Portfolio Management
                    </li>
                </ul>
                
                <a href="{{ url_for('register') }}" class="block w-full bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700">
                    Get Started
                </a>
            </div>

            <!-- Enterprise Plan -->
            <div class="bg-white rounded-lg shadow-lg p-6">
                <h3 class="text-xl font-bold mb-2">Enterprise</h3>
                <div class="text-3xl font-bold mb-4">$199<span class="text-sm text-gray-500">/month</span></div>
                
                <ul class="space-y-2 mb-6">
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Everything in Premium
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Multi-Exchange
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Priority Support
                    </li>
                    <li class="flex items-center text-sm">
                        <svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                        </svg>
                        Custom Strategies
                    </li>
                </ul>
                
                <a href="{{ url_for('register') }}" class="block w-full bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700">
                    Get Started
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

    # Auth template
    auth_html = '''{% extends "base.html" %}

{% block content %}
<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8" x-data="authForm()">
        <div>
            <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
                {% if mode == 'register' %}Create your account{% else %}Sign in to your account{% endif %}
            </h2>
        </div>
        
        <form class="mt-8 space-y-6" @submit.prevent="submitForm">
            <div class="rounded-md shadow-sm -space-y-px">
                {% if mode == 'register' %}
                <div>
                    <input x-model="form.username" type="text" required class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500" placeholder="Username">
                </div>
                <div>
                    <input x-model="form.email" type="email" required class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500" placeholder="Email address">
                </div>
                {% else %}
                <div>
                    <input x-model="form.username" type="text" required class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500" placeholder="Username">
                </div>
                {% endif %}
                <div>
                    <input x-model="form.password" type="password" required class="relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500" placeholder="Password">
                </div>
            </div>

            <div x-show="error" class="text-red-600 text-sm" x-text="error"></div>

            <div>
                <button type="submit" :disabled="loading" class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50">
                    <span x-show="!loading">{% if mode == 'register' %}Create Account{% else %}Sign In{% endif %}</span>
                    <span x-show="loading">Loading...</span>
                </button>
            </div>

            <div class="text-center">
                {% if mode == 'register' %}
                    <a href="{{ url_for('login') }}" class="text-blue-600 hover:text-blue-500">Already have an account? Sign in</a>
                {% else %}
                    <a href="{{ url_for('register') }}" class="text-blue-600 hover:text-blue-500">Don't have an account? Sign up</a>
                {% endif %}
            </div>
        </form>
    </div>
</div>

<script>
function authForm() {
    return {
        form: {
            username: '',
            {% if mode == 'register' %}email: '',{% endif %}
            password: ''
        },
        loading: false,
        error: '',
        
        async submitForm() {
            this.loading = true;
            this.error = '';
            
            try {
                const response = await fetch('{{ url_for(mode) }}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(this.form)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    this.error = data.error || 'An error occurred';
                }
            } catch (err) {
                this.error = 'Network error. Please try again.';
            } finally {
                this.loading = false;
            }
        }
    }
}
</script>
{% endblock %}'''

    # Simple dashboard
    dashboard_html = '''{% extends "base.html" %}

{% block content %}
<div class="px-4 py-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Trading Dashboard</h1>
    
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-medium mb-4">Welcome to CryptoBot Pro!</h2>
        <p class="text-gray-600 mb-4">Your crypto trading bot is ready to go.</p>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="bg-blue-50 p-4 rounded-lg">
                <h3 class="font-medium text-blue-900">Current Plan</h3>
                <p class="text-2xl font-bold text-blue-600">{{ current_user.subscription_tier.title() }}</p>
            </div>
            
            <div class="bg-green-50 p-4 rounded-lg">
                <h3 class="font-medium text-green-900">Status</h3>
                <p class="text-2xl font-bold text-green-600">Active</p>
            </div>
            
            <div class="bg-purple-50 p-4 rounded-lg">
                <h3 class="font-medium text-purple-900">Total Trades</h3>
                <p class="text-2xl font-bold text-purple-600">0</p>
            </div>
        </div>
        
        <div class="space-y-4">
            <a href="{{ url_for('settings') }}" class="inline-block bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                Configure Settings
            </a>
            <a href="{{ url_for('subscription') }}" class="inline-block bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 ml-4">
                Manage Subscription
            </a>
        </div>
    </div>
</div>
{% endblock %}'''

    # Simple settings
    settings_html = '''{% extends "base.html" %}

{% block content %}
<div class="px-4 py-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Settings</h1>
    
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-medium mb-4">API Configuration</h2>
        <p class="text-gray-600 mb-4">Add your exchange API keys to enable trading.</p>
        
        <div class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Coinbase API Key</label>
                <input type="text" class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Your Coinbase API key">
            </div>
            
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Coinbase Secret</label>
                <input type="password" class="w-full px-3 py-2 border border-gray-300 rounded-md" placeholder="Your Coinbase secret">
            </div>
            
            <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                Save Configuration
            </button>
        </div>
    </div>
</div>
{% endblock %}'''

    # Simple subscription
    subscription_html = '''{% extends "base.html" %}

{% block content %}
<div class="px-4 py-6">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Subscription Management</h1>
    
    <div class="bg-white rounded-lg shadow p-6">
        <h2 class="text-lg font-medium mb-4">Current Plan: {{ current_user.subscription_tier.title() }}</h2>
        <p class="text-gray-600 mb-6">Manage your subscription and billing.</p>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="border rounded-lg p-4">
                <h3 class="font-bold mb-2">Basic</h3>
                <p class="text-2xl font-bold mb-2">$19/month</p>
                <ul class="text-sm text-gray-600 mb-4">
                    <li>• 2 Strategies</li>
                    <li>• 5 Symbols</li>
                    <li>• 10 Signals/hour</li>
                </ul>
                <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Select</button>
            </div>
            
            <div class="border rounded-lg p-4 ring-2 ring-blue-500">
                <h3 class="font-bold mb-2">Pro</h3>
                <p class="text-2xl font-bold mb-2">$49/month</p>
                <ul class="text-sm text-gray-600 mb-4">
                    <li>• 5 Strategies</li>
                    <li>• 20 Symbols</li>
                    <li>• 50 Signals/hour</li>
                </ul>
                <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Select</button>
            </div>
            
            <div class="border rounded-lg p-4">
                <h3 class="font-bold mb-2">Premium</h3>
                <p class="text-2xl font-bold mb-2">$99/month</p>
                <ul class="text-sm text-gray-600 mb-4">
                    <li>• All Strategies</li>
                    <li>• Unlimited Symbols</li>
                    <li>• Unlimited Signals</li>
                </ul>
                <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Select</button>
            </div>
            
            <div class="border rounded-lg p-4">
                <h3 class="font-bold mb-2">Enterprise</h3>
                <p class="text-2xl font-bold mb-2">$199/month</p>
                <ul class="text-sm text-gray-600 mb-4">
                    <li>• Everything</li>
                    <li>• Multi-Exchange</li>
                    <li>• Priority Support</li>
                </ul>
                <button class="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Select</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

    # Write all template files
    templates = {
        'base.html': base_html,
        'landing.html': landing_html,
        'auth.html': auth_html,
        'dashboard.html': dashboard_html,
        'settings.html': settings_html,
        'subscription.html': subscription_html
    }
    
    for filename, content in templates.items():
        with open(f'templates/{filename}', 'w') as f:
            f.write(content)
        print(f"✅ Created templates/{filename}")
    
    print("\n🎉 All templates created successfully!")
    print("📁 Your templates/ folder now contains:")
    for filename in templates.keys():
        print(f"   - {filename}")
    
    return True

if __name__ == "__main__":
    print("🛠️ Creating Flask Templates")
    print("=" * 40)
    
    if create_templates():
        print("\n🚀 Ready to run your Flask app!")
        print("Now run: python app.py")
    else:
        print("\n❌ Failed to create templates")