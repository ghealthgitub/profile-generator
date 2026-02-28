"""
🫚 Ginger Universe — Google Sheets Connector
LEGACY FALLBACK — used only if DATABASE_URL is not set
Fetches procedure data from public Google Sheets via CSV export
"""

import re
import requests
import pandas as pd
from io import StringIO


def get_procedures_from_sheets(sheets_url):
    """
    Fetches procedures from Google Sheets (public, no auth needed).
    Returns list of dicts with keys: Entity_Name, Top_Specialty, Sub_Specialty, Complexity_Level
    """
    try:
        sheet_id = extract_sheet_id(sheets_url)
        if not sheet_id:
            print("⚠️  Could not extract Sheet ID from URL")
            return []

        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

        response = requests.get(csv_url, timeout=15)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text))
        procedures = df.to_dict('records')

        print(f"✅ Loaded {len(procedures)} procedures from Google Sheets (fallback)")
        return procedures

    except Exception as e:
        print(f"[Sheets Error] {e}")
        return []


def extract_sheet_id(url):
    """Extract sheet ID from Google Sheets URL"""
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None
