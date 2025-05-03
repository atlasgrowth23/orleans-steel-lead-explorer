import pandas as pd
import re
import os
import sqlite3
import logging
from database import Database

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataProcessor:
    """Process permit data from CSV files"""
    
    # Keywords to identify steel-related projects
    STEEL_KEYWORDS = [
        'metal', 'steel', 'fence', 'gate', 'roof', 'stud', 
        'warehouse', 'barndominium', 'industrial'
    ]
    
    def __init__(self, db_path=None):
        """Initialize with database path"""
        if db_path:
            self.db = Database(db_path)
        else:
            self.db = None
    
    def process_csv(self, csv_path, chunk_size=1000):
        """
        Process CSV file in chunks to handle large files
        
        Args:
            csv_path (str): Path to CSV file
            chunk_size (int): Number of rows to process at once
        
        Returns:
            int: Total number of rows imported or processed
        """
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return 0
        
        total_rows = 0
        processed_data = None  # For returning processed data if no db
        all_chunks = []  # Initialize here to avoid unbound variable
        
        try:
            # Use pandas to read CSV in chunks
            logger.info(f"Processing CSV file: {csv_path}")
            
            for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
                # Preprocess data
                processed_chunk = self._preprocess_data(chunk)
                
                if self.db is None:
                    # Just collect the processed chunk
                    all_chunks.append(processed_chunk)
                    total_rows += len(processed_chunk)
                    logger.info(f"Processed chunk with {len(chunk)} rows (no database insert)")
                else:
                    # Insert into database
                    rows_inserted = self.db.insert_permits(processed_chunk)
                    total_rows += rows_inserted
                    logger.info(f"Processed chunk with {len(chunk)} rows, inserted {rows_inserted}")
            
            if self.db is None and all_chunks:
                # Combine all chunks into a single DataFrame
                processed_data = pd.concat(all_chunks, ignore_index=True)
                logger.info(f"CSV processing complete. Total rows processed: {total_rows} (no database insert)")
                return processed_data
            else:
                logger.info(f"CSV processing complete. Total rows imported: {total_rows}")
                return total_rows
            
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            if self.db is None:
                return pd.DataFrame()  # Return empty DataFrame if no db
            return 0
    
    def _preprocess_data(self, df):
        """
        Preprocess data before inserting into database
        
        Args:
            df (DataFrame): Raw data from CSV
        
        Returns:
            DataFrame: Processed data ready for database insertion
        """
        # Make a copy to avoid modifying the original
        processed_df = df.copy()
        
        # Handle the column named 'Location 1' which might cause issues
        if 'Location 1' in processed_df.columns:
            processed_df.rename(columns={'Location 1': 'Location_1'}, inplace=True)
        
        # Convert dates to proper format
        date_columns = ['FilingDate', 'IssueDate', 'CurrentStatusDate', 'NextStatusDate']
        for col in date_columns:
            if col in processed_df.columns:
                # Convert to datetime format
                try:
                    processed_df[col] = pd.to_datetime(processed_df[col], errors='coerce')
                    # Convert datetime to string in YYYY-MM-DD format for SQLite
                    processed_df[col] = processed_df[col].dt.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"Error converting {col} to datetime: {e}")
        
        # Normalize Applicant field (lowercase, trim)
        if 'Applicant' in processed_df.columns:
            processed_df['Applicant'] = processed_df['Applicant'].astype(str).str.lower().str.strip()
            # Capitalize first letter of each word for display
            processed_df['Applicant'] = processed_df['Applicant'].str.title()
        
        # Convert numeric fields
        numeric_columns = ['ConstrVal', 'BldgArea', 'TotalFees', 'UnpaidFees', 'BondAmount', 
                          'TotalInspections', 'Beds', 'Baths', 'DaysOpen', 'DaysIssued']
        
        for col in numeric_columns:
            if col in processed_df.columns:
                # Replace any non-numeric values with NaN
                processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')
                # Fill NaN with 0 to avoid database issues
                processed_df[col] = processed_df[col].fillna(0)
        
        # Convert boolean column IsClosed to 0/1
        if 'IsClosed' in processed_df.columns:
            processed_df['IsClosed'] = processed_df['IsClosed'].map({'TRUE': 1, 'FALSE': 0, True: 1, False: 0}).fillna(0).astype(int)
        
        # Add steel_related flag
        if 'Description' in processed_df.columns:
            processed_df['steel_related'] = processed_df['Description'].apply(
                lambda x: self._is_steel_related(x) if pd.notna(x) else False
            ).astype(int)  # Convert boolean to 0/1 for SQLite
        
        return processed_df
    
    def _is_steel_related(self, description):
        """
        Check if a description is related to steel construction
        
        Args:
            description (str): Project description
            
        Returns:
            bool: True if steel-related, False otherwise
        """
        if not isinstance(description, str):
            return False
        
        # Convert to lowercase for case-insensitive matching
        desc_lower = description.lower()
        
        # Check for any of the keywords
        for keyword in self.STEEL_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', desc_lower):
                return True
        
        return False
    
    def check_for_duplicates(self, csv_path):
        """
        Check for duplicate permits in a CSV file
        
        Args:
            csv_path (str): Path to CSV file
            
        Returns:
            list: List of NumString values for duplicate permits
        """
        if self.db is None:
            logger.warning("No database connection, cannot check for duplicates")
            return []
            
        try:
            # Get existing permit IDs from database
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT NumString FROM permits")
            existing_nums = set(row[0] for row in cursor.fetchall())
            conn.close()
            
            # Read new permits
            df = pd.read_csv(csv_path)
            new_nums = set(df['NumString'].astype(str))
            
            # Find duplicates
            duplicates = existing_nums.intersection(new_nums)
            logger.info(f"Found {len(duplicates)} duplicate permits")
            
            return list(duplicates)
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return []
