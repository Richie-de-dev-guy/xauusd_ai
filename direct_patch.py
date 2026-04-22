import sqlite3
import os

def check_and_patch():
    db_file = 'sentinel.db'
    
    if not os.path.exists(db_file):
        print(f"❌ Could not find {db_file} in {os.getcwd()}")
        return

    try:
        # Connect directly to the SQLite file
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # 1. First, let's see if the table exists and what's in it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscribers';")
        if not cursor.fetchone():
            print("❌ Table 'subscribers' does not exist yet. Run your main bot once to create it.")
            return

        # 2. Apply the update
        cursor.execute("""
            UPDATE subscribers 
            SET api_key = 'Effiom3009', 
                email = 'richmondhenshaw35@gmail.com',
                is_active = 1
            WHERE id = 1
        """)
        
        conn.commit()
        
        # 3. Verify
        cursor.execute("SELECT id, email, api_key FROM subscribers WHERE id = 1")
        row = cursor.fetchone()
        
        if row:
            print("✅ SUCCESS!")
            print(f"Confirmed: ID {row[0]} is now {row[1]} with key {row[2]}")
        else:
            print("⚠️ Update ran, but no subscriber with ID 1 was found.")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_and_patch()