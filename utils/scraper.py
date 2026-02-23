"""
🫚 GINGER UNIVERSE - Web Scraper
Extracts doctor information from website URLs
"""

import requests
from bs4 import BeautifulSoup
import re

def scrape_doctor_webpage(url):
    """
    Scrapes doctor information from a given URL
    
    Args:
        url: Doctor's webpage URL
        
    Returns:
        dict: Extracted doctor information
    """
    try:
        # Add headers to avoid blocks
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract doctor information
        doctor_data = {
            'url': url,
            'name': extract_name(soup, text_content),
            'specialties': extract_specialties(text_content),
            'qualifications': extract_qualifications(text_content),
            'experience': extract_experience(text_content),
            'hospitals': extract_hospitals(text_content),
            'full_text': text_content[:5000]  # First 5000 chars for analysis
        }
        
        return doctor_data
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def extract_name(soup, text):
    """Extract doctor's name"""
    # Try common patterns
    name_patterns = [
        r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Doctor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    # Try H1, H2 tags
    for tag in ['h1', 'h2', 'title']:
        element = soup.find(tag)
        if element and 'dr' in element.text.lower():
            return element.text.strip()
    
    return "Doctor Name Not Found"

def extract_specialties(text):
    """Extract medical specialties"""
    specialties = []
    
    specialty_keywords = [
        'cardiologist', 'cardiology', 'orthopedic', 'orthopedics',
        'neurologist', 'neurology', 'oncologist', 'oncology',
        'surgeon', 'surgery', 'physician', 'pediatrician',
        'dermatologist', 'dermatology', 'ent', 'gastroenterologist'
    ]
    
    text_lower = text.lower()
    for keyword in specialty_keywords:
        if keyword in text_lower:
            specialties.append(keyword.title())
    
    return list(set(specialties))  # Remove duplicates

def extract_qualifications(text):
    """Extract medical qualifications"""
    qualifications = []
    
    qual_patterns = [
        r'\bMBBS\b', r'\bMD\b', r'\bMS\b', r'\bDM\b', r'\bMCh\b',
        r'\bDNB\b', r'\bFRCS\b', r'\bMRCP\b', r'\bFRCPath\b'
    ]
    
    for pattern in qual_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        qualifications.extend(matches)
    
    return list(set(qualifications))  # Remove duplicates

def extract_experience(text):
    """Extract years of experience"""
    # Look for patterns like "15 years", "15+ years"
    pattern = r'(\d+)\+?\s*years?\s*(?:of\s*)?experience'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return f"{match.group(1)} years of experience"
    
    return None

def extract_hospitals(text):
    """Extract hospital affiliations"""
    hospitals = []
    
    # Common hospital keywords
    hospital_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Hospital',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Medical\s+Center'
    ]
    
    for pattern in hospital_patterns:
        matches = re.findall(pattern, text)
        hospitals.extend(matches)
    
    return list(set(hospitals))[:5]  # Top 5 unique hospitals
