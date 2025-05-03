import os
from data_processor import DataProcessor

def import_sample_data():
    """Import sample data from the attached CSV file"""
    csv_path = "attached_assets/9 - last_7_days.csv"
    
    if not os.path.exists(csv_path):
        print(f"CSV file not found at {csv_path}")
        return False
    
    # Initialize data processor with database path
    processor = DataProcessor("permits.db")
    
    # Process the CSV file
    rows_imported = processor.process_csv(csv_path)
    
    print(f"Successfully imported {rows_imported} permits from {csv_path}")
    return rows_imported > 0

if __name__ == "__main__":
    import_sample_data()
