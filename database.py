import sqlite3
import os
import pandas as pd
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    """Database management for permits data"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.initialize_db()
    
    def initialize_db(self):
        """Initialize the database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            logger.info(f"Creating new database at {self.db_path}")
            self.create_tables()
        else:
            logger.info(f"Database already exists at {self.db_path}")
    
    def create_tables(self):
        """Create the necessary tables"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create permits table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS permits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Address TEXT,
                Owner TEXT,
                Description TEXT,
                NumString TEXT,
                IsClosed BOOLEAN,
                Type TEXT,
                Code TEXT,
                Division TEXT,
                M_S TEXT,
                FilingDate DATETIME,
                IssueDate DATETIME,
                CurrentStatus TEXT,
                NextStatus TEXT,
                CurrentStatusDate DATETIME,
                NextStatusDate DATETIME,
                LandUse TEXT,
                LandUseShort TEXT,
                ProjectName TEXT,
                UnpaidFees REAL,
                TotalFees REAL,
                BldgArea REAL,
                ConstrVal REAL,
                BondAmount REAL,
                OpenComments INTEGER,
                Applicant TEXT,
                TotalInspections INTEGER,
                Contractors TEXT,
                PIN TEXT,
                Beds INTEGER,
                Baths INTEGER,
                HeatType TEXT,
                SecondFloo TEXT,
                BasementAr TEXT,
                DaysOpen INTEGER,
                DaysIssued INTEGER,
                LeadAgency TEXT,
                ExitReason TEXT,
                Subdivision TEXT,
                CouncilDist TEXT,
                Zoning TEXT,
                HistoricDistrict TEXT,
                Location_1 TEXT,
                steel_related BOOLEAN DEFAULT 0,
                UNIQUE(NumString)
            )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_applicant ON permits(Applicant)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_issue_date ON permits(IssueDate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_steel_related ON permits(steel_related)')
            
            conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def insert_permits(self, permits_df, batch_size=1000):
        """
        Insert permits data in batches
        
        Args:
            permits_df (DataFrame): DataFrame containing permits data
            batch_size (int): Number of records to insert in each batch
        
        Returns:
            int: Number of records inserted
        """
        conn = None
        records_inserted = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Process in batches to handle large datasets
            for i in range(0, len(permits_df), batch_size):
                batch = permits_df.iloc[i:i+batch_size]
                
                # Make a safe copy with only the columns we need
                safe_batch = batch.copy()
                
                # Get all columns from the table schema
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(permits)")
                table_columns = [row[1] for row in cursor.fetchall()]
                
                # Filter DataFrame to only include columns that exist in the table
                valid_columns = [col for col in safe_batch.columns if col in table_columns]
                safe_batch = safe_batch[valid_columns]
                
                # Convert to safe SQL with placeholders
                placeholders = ', '.join(['?'] * len(valid_columns))
                column_names = ', '.join(["`" + col + "`" for col in valid_columns])
                
                # Create insert query with ON CONFLICT clause to handle duplicates
                query = f'''
                INSERT OR IGNORE INTO permits ({column_names})
                VALUES ({placeholders})
                '''
                
                # Convert DataFrame to list of tuples for insertion
                data_to_insert = [tuple(row) for row in safe_batch.to_numpy()]
                
                # Execute batch insert
                conn.executemany(query, data_to_insert)
                conn.commit()
                
                records_inserted += len(data_to_insert)
                logger.info(f"Inserted batch of {len(data_to_insert)} records. Total: {records_inserted}")
            
            logger.info(f"Total records inserted: {records_inserted}")
        except sqlite3.Error as e:
            logger.error(f"Database error during insert: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return records_inserted
    
    def get_total_permits(self):
        """Get the total number of permits in the database"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM permits")
            result = cursor.fetchone()[0]
            return result
        except sqlite3.Error as e:
            logger.error(f"Error getting total permits: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_summary(self, date_from, date_to, steel_only=False, applicant_search=None):
        """
        Get summary data for the dashboard
        
        Args:
            date_from (str): Start date in YYYY-MM-DD format
            date_to (str): End date in YYYY-MM-DD format
            steel_only (bool): Filter for steel-related permits only
            applicant_search (str): Filter by applicant name
            
        Returns:
            DataFrame: Summary data grouped by applicant
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
            SELECT 
                Applicant, 
                COUNT(*) as permit_count, 
                SUM(ConstrVal) as total_construction_value,
                MAX(IssueDate) as last_permit_date,
                SUM(CASE WHEN steel_related = 1 THEN 1 ELSE 0 END) as steel_related_count
            FROM permits
            WHERE 
                IssueDate BETWEEN ? AND ?
            """
            
            params = [date_from, date_to]
            
            if applicant_search:
                query += " AND LOWER(Applicant) LIKE ?"
                params.append(f'%{applicant_search.lower()}%')
            
            if steel_only:
                query += " AND steel_related = 1"
            
            query += " GROUP BY Applicant ORDER BY permit_count DESC"
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except sqlite3.Error as e:
            logger.error(f"Error in get_summary: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
