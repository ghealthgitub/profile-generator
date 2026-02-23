"""
🫚 GINGER UNIVERSE - Doctor Profile Generator
Main Application File - FULL AUTOMATION ACTIVATED! 🚀
"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from functools import wraps
import os
from datetime import datetime
import secrets

# Import utilities
from utils.scraper import scrape_doctor_webpage
from utils.dictionary_matcher import match_procedures
from utils.prompt_generator import generate_claude_prompt
from utils.doc_generator import create_word_document
from utils.sheets_connector import get_procedures_from_sheets
import config

# Import Anthropic for Claude API
try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = bool(config.CLAUDE_API_KEY)
except ImportError:
    CLAUDE_AVAILABLE = False
    print("⚠️  Anthropic package not installed. Run: pip install anthropic")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Secure session key

# Configuration from config.py
GOOGLE_SHEETS_URL = config.GOOGLE_SHEETS_URL
ADMIN_USERNAME = config.ADMIN_USERNAME
ADMIN_PASSWORD = config.ADMIN_PASSWORD

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('username'))

@app.route('/generate', methods=['POST'])
@login_required
def generate_profile():
    try:
        doctor_url = request.json.get('doctor_url')
        
        if not doctor_url:
            return jsonify({'error': 'Doctor URL is required'}), 400
        
        # Step 1: Scrape doctor webpage
        doctor_data = scrape_doctor_webpage(doctor_url)
        
        if not doctor_data:
            return jsonify({'error': 'Could not extract data from URL'}), 400
        
        # Step 2: Get procedures from Google Sheets
        procedures_db = get_procedures_from_sheets(GOOGLE_SHEETS_URL)
        
        # Step 3: Match doctor to procedures
        matched_procedures = match_procedures(doctor_data, procedures_db)
        
        # Step 4: Generate Claude prompt
        prompt = generate_claude_prompt(doctor_data, matched_procedures)
        
        # Step 5: FULL AUTOMATION - Call Claude API directly! 🚀
        if CLAUDE_AVAILABLE and config.CLAUDE_API_KEY:
            try:
                client = Anthropic(api_key=config.CLAUDE_API_KEY)
                
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                claude_response = message.content[0].text
                
                # Return automated response!
                return jsonify({
                    'success': True,
                    'automated': True,
                    'doctor_data': doctor_data,
                    'matched_procedures': matched_procedures,
                    'claude_response': claude_response,
                    'claude_prompt': prompt  # For reference
                })
                
            except Exception as api_error:
                # If API fails, fall back to manual mode
                return jsonify({
                    'success': True,
                    'automated': False,
                    'doctor_data': doctor_data,
                    'matched_procedures': matched_procedures,
                    'claude_prompt': prompt,
                    'api_error': str(api_error)
                })
        else:
            # Manual mode (no API key)
            return jsonify({
                'success': True,
                'automated': False,
                'doctor_data': doctor_data,
                'matched_procedures': matched_procedures,
                'claude_prompt': prompt
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-document', methods=['POST'])
@login_required
def create_document():
    try:
        doctor_data = request.json.get('doctor_data')
        claude_response = request.json.get('claude_response')
        
        # Generate Word document
        doc_path = create_word_document(doctor_data, claude_response)
        
        return send_file(
            doc_path,
            as_attachment=True,
            download_name=f"doctor_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # For development
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    # For production, use: gunicorn app:app
