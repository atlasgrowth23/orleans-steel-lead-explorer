import logging
from pg_database import PostgresDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_postgres_database():
    """Check the PostgreSQL database connection and contents"""
    try:
        # Initialize the PostgreSQL database
        pg_db = PostgresDatabase()
        
        # Check permit count
        count = pg_db.get_total_permits()
        print(f"PostgreSQL database contains {count} permits")
        
        if count > 0:
            # Get min/max dates
            min_date, max_date = pg_db.get_date_range()
            print(f"Date range: {min_date} to {max_date}")
            
            # Get sample data
            from sqlalchemy import text
            with pg_db.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT \"Applicant\", \"Description\", \"ConstrVal\", steel_related " 
                    "FROM permits LIMIT 5"
                ))
                print("\nSample data:")
                for row in result:
                    print(f"Applicant: {row[0]}, Value: ${row[2]}, Steel: {'Yes' if row[3] else 'No'}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking PostgreSQL database: {e}")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_postgres_database()
