import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import os
import logging
from database import Database  # SQLite database (legacy)
from pg_database import PostgresDatabase  # PostgreSQL database (new)
from data_processor import DataProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Orleans Steel Lead Explorer",
    page_icon="🏗️",
    layout="wide",
)

# Global variable to track which database is in use
use_postgres = False

# Initialize PostgreSQL database
try:
    db = PostgresDatabase()
    use_postgres = True
    logger.info("Using PostgreSQL database")
except Exception as e:
    logger.warning(f"Could not connect to PostgreSQL, falling back to SQLite: {e}")
    db = Database("permits.db")
    use_postgres = False

# Function to load data from database
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_data_from_db(date_from, date_to, steel_only=False, applicant_search=""):
    """Load filtered data from the database"""
    try:
        if use_postgres:
            return db.get_summary(date_from, date_to, steel_only, applicant_search)
        else:
            # Legacy SQLite code
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
                AND (? = '' OR LOWER(Applicant) LIKE ?)
            """
            
            params = [date_from, date_to, applicant_search, f'%{applicant_search.lower()}%']
            
            if steel_only:
                query += " AND steel_related = 1"
            
            query += " GROUP BY Applicant ORDER BY permit_count DESC"
            
            with sqlite3.connect("permits.db") as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_all_permits(date_from, date_to, steel_only=False, applicant_search=""):
    """Get raw permit data for debugging"""
    try:
        if use_postgres:
            return db.get_all_permits(date_from, date_to, steel_only, applicant_search)
        else:
            # Legacy SQLite code
            query = """
            SELECT 
                Applicant,
                Address,
                Description,
                Type,
                FilingDate,
                IssueDate,
                ConstrVal,
                steel_related,
                ProjectName
            FROM permits
            WHERE 
                IssueDate BETWEEN ? AND ?
                AND (? = '' OR LOWER(Applicant) LIKE ?)
            """
            
            params = [date_from, date_to, applicant_search, f'%{applicant_search.lower()}%']
            
            if steel_only:
                query += " AND steel_related = 1"
            
            with sqlite3.connect("permits.db") as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
    except Exception as e:
        logger.error(f"Error loading raw permit data: {e}")
        st.error(f"Error loading raw permit data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_date_range():
    """Get minimum and maximum dates in the database"""
    today = datetime.now().date()  # Use date() to get just the date portion
    one_week_ago = today - timedelta(days=7)
    
    try:
        if use_postgres:
            # Use PostgreSQL
            min_date, max_date = db.get_date_range()
            
            if not min_date or not max_date:
                logger.warning("No date range found in PostgreSQL database")
                return one_week_ago, today
                
            # If dates are valid but min > max, swap them
            if min_date > max_date:
                min_date, max_date = max_date, min_date
            
            # If max date is in the future, limit to today
            if max_date > today:
                max_date = today
                
            # Ensure min date isn't too far in the past (limit to 1 year ago)
            if min_date < today - timedelta(days=365):
                min_date = today - timedelta(days=365)
            
            return min_date, max_date
        else:
            # Legacy SQLite code
            with sqlite3.connect("permits.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(IssueDate), MAX(IssueDate) FROM permits")
                result = cursor.fetchone()
                
                if not result or None in result:
                    # No data in database
                    return one_week_ago, today
                    
                min_date_str, max_date_str = result
                
                # Ensure we have valid date strings
                if not min_date_str or not max_date_str:
                    return one_week_ago, today
                
                # Convert to datetime objects, handling any format issues
                try:
                    # Split in case there's a time component and take just the date part
                    min_date_parts = min_date_str.split()[0].split('-')
                    max_date_parts = max_date_str.split()[0].split('-')
                    
                    # Validate that we have at least 3 parts for year-month-day
                    if len(min_date_parts) >= 3 and len(max_date_parts) >= 3:
                        min_date = datetime(int(min_date_parts[0]), int(min_date_parts[1]), int(min_date_parts[2])).date()
                        max_date = datetime(int(max_date_parts[0]), int(max_date_parts[1]), int(max_date_parts[2])).date()
                        
                        # If dates are valid but min > max, swap them
                        if min_date > max_date:
                            min_date, max_date = max_date, min_date
                            
                        # If max date is in the future, limit to today
                        if max_date > today:
                            max_date = today
                            
                        # Ensure min date isn't too far in the past (limit to 1 year ago)
                        if min_date < today - timedelta(days=365):
                            min_date = today - timedelta(days=365)
                        
                        return min_date, max_date
                except (ValueError, IndexError) as e:
                    # If any parsing error occurs, use default dates
                    st.warning(f"Error parsing date values: {e}")
                    
                # Default fallback
                return one_week_ago, today
    except Exception as e:
        logger.error(f"Error getting date range: {e}")
        st.error(f"Error getting date range: {e}")
        return one_week_ago, today

def fallback_to_sqlite():
    """Helper function to fallback to SQLite when PostgreSQL fails"""
    global use_postgres
    use_postgres = False
    global db
    db = Database("permits.db")
    
def main():
    global use_postgres, db  # Declare we'll use the global variables
    st.title("Orleans Steel Lead Explorer")
    
    # Check if database has data
    db_needs_data = False
    
    try:
        if use_postgres:
            # Check PostgreSQL database
            count = db.get_total_permits()
            if count == 0:
                st.warning("PostgreSQL database is empty. Loading sample data...")
                db_needs_data = True
            else:
                st.info(f"Using PostgreSQL database with {count} permits")
        else:
            # Check SQLite database
            if not os.path.exists("permits.db"):
                st.warning("SQLite database not initialized. Initializing now...")
                db_needs_data = True
            else:
                # Check if database has permits
                try:
                    with sqlite3.connect("permits.db") as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM permits")
                        count = cursor.fetchone()[0]
                        if count == 0:
                            st.warning("SQLite database is empty. Loading sample data...")
                            db_needs_data = True
                        else:
                            st.info(f"Using SQLite database with {count} permits")
                except Exception as e:
                    logger.error(f"Error checking SQLite database: {e}")
                    st.error(f"Error checking database: {e}")
                    db_needs_data = True
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        st.error(f"Error checking database: {e}")
        db_needs_data = True
    
    # If we need to load data
    if db_needs_data:
        # First check for sample data in attached_assets
        sample_path = "attached_assets/9 - last_7_days.csv"
        if os.path.exists(sample_path):
            st.info(f"Loading sample data from {sample_path}. This may take a moment...")
            
            if use_postgres:
                # Load data into PostgreSQL directly
                try:
                    # First process with the DataProcessor to normalize the data
                    df = pd.read_csv(sample_path)
                    processor = DataProcessor(None)  # We don't need the SQLite path
                    processed_df = processor._preprocess_data(df)
                    
                    # Then insert into PostgreSQL
                    rows_imported = db.insert_permits(processed_df)
                    
                    if rows_imported > 0:
                        st.success(f"Successfully imported {rows_imported} permits into PostgreSQL database!")
                        st.info("Refreshing application...")
                        st.rerun()
                    else:
                        st.error("Failed to import sample data to PostgreSQL. Trying SQLite fallback.")
                        fallback_to_sqlite()
                except Exception as e:
                    logger.error(f"Error importing to PostgreSQL: {e}")
                    st.error(f"Error importing to PostgreSQL: {e}")
                    st.info("Falling back to SQLite database...")
                    fallback_to_sqlite()
            
            if not use_postgres:  # Either PostgreSQL failed or we're using SQLite
                # Process the sample file with SQLite
                processor = DataProcessor("permits.db")
                rows_imported = processor.process_csv(sample_path)
                
                if rows_imported > 0:
                    st.success(f"Successfully imported {rows_imported} permits into SQLite database!")
                    st.info("Refreshing application...")
                    st.rerun()
                else:
                    st.error("Failed to import sample data. Please upload a CSV file.")
        
        # If no sample data, allow file upload
        uploaded_file = st.file_uploader("Upload permits CSV file", type=["csv"])
        if uploaded_file is not None:
            st.info("Processing CSV file and creating database. This may take a moment...")
            
            # Save the uploaded file temporarily
            with open("temp_upload.csv", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            if use_postgres:
                # Load data into PostgreSQL directly
                try:
                    # First process with the DataProcessor to normalize the data
                    df = pd.read_csv("temp_upload.csv")
                    processor = DataProcessor(None)  # We don't need the SQLite path
                    processed_df = processor._preprocess_data(df)
                    
                    # Then insert into PostgreSQL
                    rows_imported = db.insert_permits(processed_df)
                    
                    if rows_imported > 0:
                        st.success(f"Successfully imported {rows_imported} permits into PostgreSQL database!")
                        st.info("Refreshing application...")
                        st.rerun()
                    else:
                        st.error("Failed to import uploaded data to PostgreSQL. Trying SQLite fallback.")
                        fallback_to_sqlite()
                except Exception as e:
                    logger.error(f"Error importing to PostgreSQL: {e}")
                    st.error(f"Error importing to PostgreSQL: {e}")
                    st.info("Falling back to SQLite database...")
                    fallback_to_sqlite()
                    
            if not use_postgres:  # Either PostgreSQL failed or we're using SQLite
                # Process the uploaded file with SQLite
                processor = DataProcessor("permits.db")
                rows_imported = processor.process_csv("temp_upload.csv")
                
                if rows_imported > 0:
                    st.success(f"Successfully imported {rows_imported} permits into SQLite database!")
                    st.info("Refreshing application...")
                    st.rerun()
                else:
                    st.error("Failed to import data from uploaded file.")
        
        return

    # Get date range from database
    min_date, max_date = get_date_range()
    logger.info(f"Date range from database: {min_date} to {max_date}")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range picker
    col1, col2 = st.sidebar.columns(2)
    
    # Make sure the default dates are within the valid range
    default_from_date = max_date - timedelta(days=7)
    if default_from_date < min_date:
        default_from_date = min_date
        
    with col1:
        date_from = st.date_input("From", 
                                 value=default_from_date,
                                 min_value=min_date,
                                 max_value=max_date)
    with col2:
        date_to = st.date_input("To", 
                               value=max_date,
                               min_value=min_date,
                               max_value=max_date)
    
    # Convert date objects to strings
    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")
    
    # Applicant search
    applicant_search = st.sidebar.text_input("Search Applicant", "")
    
    # Steel-related filter
    steel_only = st.sidebar.checkbox("Show steel-related permits only")
    
    # Load data based on filters
    data = load_data_from_db(date_from_str, date_to_str, steel_only, applicant_search)
    
    if data.empty:
        st.warning("No data found for the selected filters.")
        return
    
    # Display summary stats
    st.subheader("Summary Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Applicants", len(data))
    with col2:
        st.metric("Total Permits", data['permit_count'].sum())
    with col3:
        st.metric("Total Construction Value", f"${data['total_construction_value'].sum():,.2f}")
    
    # Display top 10 applicants chart
    st.subheader("Top 10 Applicants by Permit Count")
    
    # Get top 10 applicants
    top_10_data = data.head(10)
    
    # Create bar chart
    fig = px.bar(
        top_10_data,
        x='Applicant',
        y='permit_count',
        title="Top 10 Applicants by Permit Count",
        labels={'permit_count': 'Number of Permits', 'Applicant': 'Applicant Name'},
        color='total_construction_value',
        color_continuous_scale=px.colors.sequential.Blues,
    )
    
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display applicant table
    st.subheader("Applicant Data")
    
    # Format the data for display
    display_data = data.copy()
    display_data['total_construction_value'] = display_data['total_construction_value'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    display_data['last_permit_date'] = pd.to_datetime(display_data['last_permit_date']).dt.strftime('%Y-%m-%d')
    display_data.rename(columns={
        'Applicant': 'Applicant',
        'permit_count': 'Permit Count',
        'total_construction_value': 'Total Construction Value',
        'last_permit_date': 'Last Permit Date',
        'steel_related_count': 'Steel-Related Permits'
    }, inplace=True)
    
    st.dataframe(display_data, use_container_width=True)
    
    # Raw permits data (for debugging)
    with st.expander("View Raw Permit Data"):
        permits_data = get_all_permits(date_from_str, date_to_str, steel_only, applicant_search)
        if not permits_data.empty:
            st.dataframe(permits_data, use_container_width=True)
        else:
            st.info("No raw permit data available.")

if __name__ == "__main__":
    main()
