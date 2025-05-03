import os
import logging
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, Date, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgresDatabase:
    """Database management for permits data using PostgreSQL"""
    
    def __init__(self):
        """Initialize with database environment variables"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")
            
        try:
            logger.info(f"Connecting to database at {self.db_url.split('@')[1] if '@' in self.db_url else 'postgres'}")
            self.engine = create_engine(self.db_url)
            self.metadata = MetaData()
            self.Base = declarative_base()
            self.initialize_db()
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def initialize_db(self):
        """Initialize the database if the tables don't exist"""
        try:
            # Define the permits table
            self.permits = Table(
                'permits', self.metadata,
                Column('id', Integer, primary_key=True),
                Column('NumString', String, unique=True, nullable=False),
                Column('Applicant', String),
                Column('Address', String),
                Column('Description', String),
                Column('Type', String),
                Column('FilingDate', Date),
                Column('IssueDate', Date),
                Column('CurrentStatusDate', Date),
                Column('NextStatusDate', Date),
                Column('ConstrVal', Float),
                Column('BldgArea', Float),
                Column('TotalFees', Float),
                Column('UnpaidFees', Float),
                Column('BondAmount', Float),
                Column('TotalInspections', Integer),
                Column('IsClosed', Boolean),
                Column('DaysOpen', Integer),
                Column('Beds', Integer),
                Column('Baths', Integer),
                Column('DaysIssued', Integer),
                Column('ProjectName', String),
                Column('steel_related', Boolean)
            )
            
            # Create tables if they don't exist
            self.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def insert_permits(self, permits_df, batch_size=1000):
        """Insert permits data in batches"""
        if permits_df.empty:
            logger.warning("Empty DataFrame provided, nothing to insert")
            return 0
        
        records_inserted = 0
        
        try:
            # Process in batches to handle large datasets
            for i in range(0, len(permits_df), batch_size):
                batch = permits_df.iloc[i:i+batch_size].copy()
                
                # Make sure we have all the columns needed and no extras
                column_names = [c.name for c in self.permits.columns if c.name != 'id']
                for col in column_names:
                    if col not in batch.columns:
                        batch[col] = None
                
                # Keep only the columns in our table
                batch = batch[column_names]
                
                # Insert data using SQLAlchemy
                batch.to_sql('permits', self.engine, if_exists='append', index=False)
                
                records_inserted += len(batch)
                logger.info(f"Inserted batch of {len(batch)} records. Total: {records_inserted}")
            
            logger.info(f"Total records inserted: {records_inserted}")
        except Exception as e:
            logger.error(f"Error inserting permits: {e}")
            raise
        
        return records_inserted
    
    def get_total_permits(self):
        """Get the total number of permits in the database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM permits"))
                return result.scalar()
        except Exception as e:
            logger.error(f"Error getting total permits: {e}")
            return 0
    
    def get_summary(self, date_from, date_to, steel_only=False, applicant_search=None):
        """Get summary data for the dashboard"""
        try:
            query = text("""
            SELECT 
                "Applicant", 
                COUNT(*) as permit_count, 
                SUM("ConstrVal") as total_construction_value,
                MAX("IssueDate") as last_permit_date,
                SUM(CASE WHEN steel_related = TRUE THEN 1 ELSE 0 END) as steel_related_count
            FROM permits
            WHERE 
                "IssueDate" BETWEEN :date_from AND :date_to
            """
            )
            
            params = {'date_from': date_from, 'date_to': date_to}
            
            if applicant_search:
                query = text(str(query) + " AND LOWER(\"Applicant\") LIKE :applicant")
                params['applicant'] = f'%{applicant_search.lower()}%'
            
            if steel_only:
                query = text(str(query) + " AND steel_related = TRUE")
            
            query = text(str(query) + " GROUP BY \"Applicant\" ORDER BY permit_count DESC")
            
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                df = pd.DataFrame(result.fetchall())
                if not df.empty:
                    df.columns = result.keys()
                return df
        except Exception as e:
            logger.error(f"Error in get_summary: {e}")
            return pd.DataFrame()
    
    def get_all_permits(self, date_from, date_to, steel_only=False, applicant_search=None):
        """Get all permits matching the filter criteria"""
        try:
            query = text("""
            SELECT 
                "Applicant",
                "Address",
                "Description",
                "Type",
                "FilingDate",
                "IssueDate",
                "ConstrVal",
                steel_related,
                "ProjectName"
            FROM permits
            WHERE 
                "IssueDate" BETWEEN :date_from AND :date_to
            """
            )
            
            params = {'date_from': date_from, 'date_to': date_to}
            
            if applicant_search:
                query = text(str(query) + " AND LOWER(\"Applicant\") LIKE :applicant")
                params['applicant'] = f'%{applicant_search.lower()}%'
            
            if steel_only:
                query = text(str(query) + " AND steel_related = TRUE")
            
            query = text(str(query) + " ORDER BY \"IssueDate\" DESC")
            
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                df = pd.DataFrame(result.fetchall())
                if not df.empty:
                    df.columns = result.keys()
                return df
        except Exception as e:
            logger.error(f"Error in get_all_permits: {e}")
            return pd.DataFrame()
    
    def get_date_range(self):
        """Get minimum and maximum dates in the database"""
        try:
            query = text("""
            SELECT 
                MIN("IssueDate") as min_date,
                MAX("IssueDate") as max_date
            FROM permits
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query)
                row = result.fetchone()
                if row and row[0] and row[1]:
                    return row[0], row[1]
                else:
                    return None, None
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            return None, None
    
    def get_duplicates(self, permit_numbers):
        """Check for duplicate permits in database"""
        try:
            query = text("""
            SELECT "NumString" FROM permits 
            WHERE "NumString" IN :nums
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"nums": tuple(permit_numbers) if permit_numbers else ('',)})
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return []
