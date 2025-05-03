# Orleans Steel Lead Explorer

A Streamlit-based permit data explorer that helps identify potential construction leads for Orleans Steel with filtering, visualization, and data management capabilities.

## Features

- Interactive dashboard for exploring building permit data
- Filtering capabilities by date range, applicant name, and steel-related projects
- Data visualization showing top applicants by permit count
- PostgreSQL database integration for improved scalability
- Support for importing CSV data from various sources
- Automatic detection of steel-related construction projects
- Cached queries for improved performance

## Technology Stack

- Python 3.11
- Streamlit for the web interface
- Pandas for data manipulation
- Plotly for interactive visualizations
- PostgreSQL for scalable data storage
- SQLite as a fallback database option

## Getting Started

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `streamlit run app.py`
4. Import permit data from CSV files via the user interface

## Environment Setup

Create a `.env` file with PostgreSQL connection details (optional):

```
DATABASE_URL=postgresql://username:password@host:port/database
```

## License

MIT

## Sample Data

The repository includes truncated sample data in the `sample_data` directory. This data can be used to test the application before connecting to your own data source.
