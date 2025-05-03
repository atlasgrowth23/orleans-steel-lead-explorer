import pandas as pd
import sqlite3
import logging
from pg_database import PostgresDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_to_postgres():
    """Migrate data from SQLite to PostgreSQL"""
    # Connect to SQLite database
    logger.info("Connecting to SQLite database")
    try:
        conn = sqlite3.connect('permits.db')
        
        # Get count of permits in SQLite
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM permits")
        count = cursor.fetchone()[0]
        logger.info(f"Found {count} permits in SQLite database")
        
        if count == 0:
            logger.warning("No data to migrate from SQLite database")
            return 0
        
        # Read data from SQLite
        logger.info("Reading data from SQLite")
        df = pd.read_sql_query("SELECT * FROM permits", conn)
        conn.close()
        
        # Convert boolean columns
        if 'steel_related' in df.columns:
            df['steel_related'] = df['steel_related'].astype(bool)
        if 'IsClosed' in df.columns:
            df['IsClosed'] = df['IsClosed'].astype(bool)
        
        # Convert date columns
        date_columns = ['FilingDate', 'IssueDate', 'CurrentStatusDate', 'NextStatusDate']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Drop SQLite rowid column if it exists
        if 'rowid' in df.columns:
            df = df.drop('rowid', axis=1)
        
        # Initialize PostgreSQL database
        logger.info("Connecting to PostgreSQL database")
        pg_db = PostgresDatabase()
        
        # Insert data into PostgreSQL
        logger.info("Inserting data into PostgreSQL")
        records_inserted = pg_db.insert_permits(df)
        
        logger.info(f"Successfully migrated {records_inserted} records to PostgreSQL")
        return records_inserted
    
    except Exception as e:
        logger.error(f"Error migrating data to PostgreSQL: {e}")
        return 0

if __name__ == "__main__":
    migrate_to_postgres()
