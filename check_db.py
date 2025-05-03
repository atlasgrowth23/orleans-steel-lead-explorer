import sqlite3
import os

def check_database():
    conn = None
    if not os.path.exists('permits.db'):
        print('Database file not found!')
        return
        
    try:
        conn = sqlite3.connect('permits.db')
        cursor = conn.cursor()
        
        # Check if permits table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permits'")
        if not cursor.fetchone():
            print('Permits table does not exist!')
            return
            
        # Get count of permits
        cursor.execute('SELECT COUNT(*) FROM permits')
        count = cursor.fetchone()[0]
        print(f'Database contains {count} permits')
        
        if count > 0:
            # Get sample of data
            cursor.execute('SELECT Applicant, Description, ConstrVal, steel_related FROM permits LIMIT 5')
            print('\nSample data:')
            for row in cursor.fetchall():
                print(f'Applicant: {row[0]}, Value: ${row[2]}, Steel: {"Yes" if row[3] else "No"}')
                
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    check_database()
