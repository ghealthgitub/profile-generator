"""
🫚 GINGER UNIVERSE - Google Sheets Connector
Fetches procedure data from Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests

def get_procedures_from_sheets(sheets_url):
    """
    Fetches procedures from Google Sheets
    
    Args:
        sheets_url: Public Google Sheets URL
        
    Returns:
        list: List of procedures with details
    """
    try:
        # Extract sheet ID from URL
        sheet_id = extract_sheet_id(sheets_url)
        
        # Use public CSV export (no auth needed!)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        
        # Fetch data
        response = requests.get(csv_url)
        response.raise_for_status()
        
        # Parse CSV
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        # Convert to list of dicts
        procedures = df.to_dict('records')
        
        print(f"✅ Loaded {len(procedures)} procedures from Google Sheets")
        
        return procedures
        
    except Exception as e:
        print(f"Error loading Google Sheets: {str(e)}")
        # Return empty list if fails
        return []

def extract_sheet_id(url):
    """Extract sheet ID from Google Sheets URL"""
    import re
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None
