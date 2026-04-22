import sqlite3
import os

def update_db():
    db_path = 'sentinel.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Could not find {db_path} in this folder.")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Update the subscriber record
        # We are setting the API Key to 'Effiom3009' and your email
        cursor.execute("""
            UPDATE subscribers 
            SET api_key = 'Effiom3009', 
                email = 'richmondhenshaw35@gmail.com',
                is_active = 1
            WHERE id = 1
        """)

        conn.commit()
        
        # Verify the change
        cursor.execute("SELECT id, name, email, api_key FROM subscribers WHERE id = 1")
        row = cursor.fetchone()
        
        print("✅ Database updated successfully!")
        print(f"Current Record: ID={row[0]}, Name={row[1]}, Email={row[2]}, Key={row[3]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    update_db()