#!/usr/bin/env python3
"""
Script to fetch new permits data and update the database.
This script is designed to be run daily to keep the database up-to-date.
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from data_processor import DataProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetch_permits.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def process_new_permits(csv_path, db_path="permits.db"):
    """
    Process new permits from a CSV file and update the database
    
    Args:
        csv_path (str): Path to the CSV file with new permits
        db_path (str): Path to the database file
    
    Returns:
        dict: Statistics about the import process
    """
    logger.info(f"Starting to process new permits from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return {"error": "CSV file not found", "file": csv_path}
    
    try:
        # Initialize data processor
        processor = DataProcessor(db_path)
        
        # Check for duplicates
        duplicates = processor.check_for_duplicates(csv_path)
        
        # Process the CSV file
        rows_imported = processor.process_csv(csv_path)
        
        logger.info(f"Successfully processed {rows_imported} new permits")
        logger.info(f"Skipped {len(duplicates)} duplicate permits")
        
        # Return statistics
        return {
            "timestamp": datetime.now().isoformat(),
            "file_processed": csv_path,
            "rows_imported": rows_imported,
            "duplicates_skipped": len(duplicates),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error processing new permits: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "file_processed": csv_path,
            "status": "error",
            "error_message": str(e)
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch and process new permits data')
    parser.add_argument('csv_path', help='Path to the CSV file with new permits')
    parser.add_argument('--db', default='permits.db', help='Path to the database file (default: permits.db)')
    
    args = parser.parse_args()
    
    result = process_new_permits(args.csv_path, args.db)
    
    if result.get("status") == "success":
        logger.info(f"Successfully processed {result['rows_imported']} new permits")
        logger.info(f"Skipped {result['duplicates_skipped']} duplicate permits")
    else:
        logger.error(f"Error: {result.get('error_message', 'Unknown error')}")
        sys.exit(1)
