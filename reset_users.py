from app import app, db, User

def reset_users():
    with app.app_context():
        # Get all users who are NOT 'it_expert'
        users_to_delete = User.query.filter(User.role != 'it_expert').all()
        
        count = 0
        for user in users_to_delete:
            db.session.delete(user)
            count += 1
            
        db.session.commit()
        print(f"Deleted {count} users (Doctors/Staff). Admin and Patient data preserved.")
        
        # Verify Admin exists
        admin = User.query.filter_by(role='it_expert').first()
        if admin:
             print(f"Admin '{admin.username}' checks out ok.")
        else:
             print("WARNING: Admin user not found! You might need to restart app to recreate it.")

if __name__ == '__main__':
    reset_users()
