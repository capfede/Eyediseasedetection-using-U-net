from app import app, db, User
import sys

def verify_and_reset():
    with app.app_context():
        # Check count
        count = User.query.filter(User.role != 'it_expert').count()
        print(f"Current non-admin users: {count}")
        
        if count > 0:
            print("Deleting remaining users...")
            User.query.filter(User.role != 'it_expert').delete()
            db.session.commit()
            print("Deletion complete.")
        else:
            print("Database already clean.")
            
        admin = User.query.filter_by(role='it_expert').first()
        if admin:
            print(f"Admin user '{admin.username}' exists.")
        else:
            print("Admin user MISSING.")

if __name__ == '__main__':
    verify_and_reset()
