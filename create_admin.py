from app import app, db, User, SubscriptionTier
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def create_admin_user():
    """Create an admin user with Enterprise subscription"""
    
    print("🔧 Creating Admin User")
    print("=" * 40)
    
    # Get admin credentials
    admin_username = input("Enter admin username (default: admin): ").strip() or "admin"
    admin_email = input("Enter admin email (default: admin@cryptobot.com): ").strip() or "admin@cryptobot.com"
    admin_password = input("Enter admin password (default: admin123): ").strip() or "admin123"
    
    print(f"\n📝 Creating user:")
    print(f"   Username: {admin_username}")
    print(f"   Email: {admin_email}")
    print(f"   Subscription: Enterprise")
    
    try:
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(username=admin_username).first()
            if existing_user:
                print(f"\n⚠️ User '{admin_username}' already exists!")
                
                update = input("Update to Enterprise? (y/n): ").strip().lower()
                if update == 'y':
                    # Update existing user to Enterprise
                    existing_user.subscription_tier = SubscriptionTier.ENTERPRISE.value
                    existing_user.subscription_active = True
                    existing_user.subscription_expires = datetime.utcnow() + timedelta(days=365)  # 1 year
                    db.session.commit()
                    print(f"✅ Updated '{admin_username}' to Enterprise subscription!")
                    return existing_user
                else:
                    print("❌ Admin creation cancelled")
                    return None
            
            # Create new admin user
            admin_user = User(
                username=admin_username,
                email=admin_email,
                subscription_tier=SubscriptionTier.ENTERPRISE.value,
                subscription_active=True,
                subscription_expires=datetime.utcnow() + timedelta(days=365)  # 1 year
            )
            
            # Set password
            admin_user.set_password(admin_password)
            
            # Add to database
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"\n✅ Admin user created successfully!")
            print(f"📊 User Details:")
            print(f"   ID: {admin_user.id}")
            print(f"   Username: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   Tier: {admin_user.subscription_tier}")
            print(f"   Active: {admin_user.subscription_active}")
            print(f"   Expires: {admin_user.subscription_expires}")
            
            return admin_user
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return None

def create_test_users():
    """Create test users for different subscription tiers"""
    
    print("\n🧪 Creating Test Users for All Tiers")
    print("=" * 40)
    
    test_users = [
        {
            'username': 'free_user',
            'email': 'free@test.com',
            'password': 'test123',
            'tier': SubscriptionTier.FREE.value,
            'active': False
        },
        {
            'username': 'basic_user', 
            'email': 'basic@test.com',
            'password': 'test123',
            'tier': SubscriptionTier.BASIC.value,
            'active': True
        },
        {
            'username': 'pro_user',
            'email': 'pro@test.com', 
            'password': 'test123',
            'tier': SubscriptionTier.PRO.value,
            'active': True
        },
        {
            'username': 'premium_user',
            'email': 'premium@test.com',
            'password': 'test123', 
            'tier': SubscriptionTier.PREMIUM.value,
            'active': True
        }
    ]
    
    created_users = []
    
    try:
        with app.app_context():
            for user_data in test_users:
                # Check if user exists
                existing = User.query.filter_by(username=user_data['username']).first()
                if existing:
                    print(f"⚠️ {user_data['username']} already exists, skipping...")
                    continue
                
                # Create user
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    subscription_tier=user_data['tier'],
                    subscription_active=user_data['active'],
                    subscription_expires=datetime.utcnow() + timedelta(days=30) if user_data['active'] else None
                )
                
                user.set_password(user_data['password'])
                db.session.add(user)
                created_users.append(user_data['username'])
            
            db.session.commit()
            
            if created_users:
                print(f"✅ Created test users: {', '.join(created_users)}")
            else:
                print("ℹ️ All test users already exist")
                
    except Exception as e:
        print(f"❌ Error creating test users: {e}")

def show_all_users():
    """Display all users in the database"""
    
    print("\n👥 All Users in Database")
    print("=" * 60)
    
    try:
        with app.app_context():
            users = User.query.all()
            
            if not users:
                print("No users found in database")
                return
            
            print(f"{'ID':<4} {'Username':<15} {'Email':<25} {'Tier':<12} {'Active':<8}")
            print("-" * 60)
            
            for user in users:
                print(f"{user.id:<4} {user.username:<15} {user.email:<25} {user.subscription_tier:<12} {str(user.subscription_active):<8}")
                
    except Exception as e:
        print(f"❌ Error fetching users: {e}")

def grant_enterprise_access():
    """Grant Enterprise access to any existing user"""
    
    print("\n🚀 Grant Enterprise Access")
    print("=" * 40)
    
    try:
        with app.app_context():
            # Show existing users
            users = User.query.all()
            if not users:
                print("No users found in database")
                return
            
            print("Existing users:")
            for i, user in enumerate(users, 1):
                print(f"{i}. {user.username} ({user.email}) - {user.subscription_tier}")
            
            # Get selection
            choice = input(f"\nSelect user (1-{len(users)}) or enter username: ").strip()
            
            selected_user = None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(users):
                    selected_user = users[idx]
            else:
                selected_user = User.query.filter_by(username=choice).first()
            
            if not selected_user:
                print("❌ User not found")
                return
            
            # Update to Enterprise
            selected_user.subscription_tier = SubscriptionTier.ENTERPRISE.value
            selected_user.subscription_active = True
            selected_user.subscription_expires = datetime.utcnow() + timedelta(days=365)
            
            db.session.commit()
            
            print(f"✅ Granted Enterprise access to '{selected_user.username}'!")
            
    except Exception as e:
        print(f"❌ Error granting access: {e}")

def main():
    """Main menu for admin management"""
    
    print("🔐 CryptoBot Admin Management")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Create admin user (Enterprise)")
        print("2. Create test users (all tiers)")
        print("3. Show all users")
        print("4. Grant Enterprise access to user")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            create_admin_user()
        elif choice == "2":
            create_test_users()
        elif choice == "3":
            show_all_users()
        elif choice == "4":
            grant_enterprise_access()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
