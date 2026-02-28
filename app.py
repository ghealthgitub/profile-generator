"""
🫚 GINGER UNIVERSE — Doctor Profile Generator
Main Application — v2.0 (Integrated with Ginger Healthcare DB)
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
from utils.db_connector import get_procedures_from_db
from utils.sheets_connector import get_procedures_from_sheets
import config

# Import Anthropic for Claude API
CLAUDE_AVAILABLE = False
try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = bool(config.ANTHROPIC_API_KEY)
    if CLAUDE_AVAILABLE:
        print("✅ Claude API ready (fully automated mode)")
    else:
        print("⚠️  No ANTHROPIC_API_KEY set — running in manual mode")
except ImportError:
    print("⚠️  Anthropic package not installed. Run: pip install anthropic")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ── Auth ─────────────────────────────────────────────────────

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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
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
    return render_template('dashboard.html',
                           username=session.get('username'),
                           claude_available=CLAUDE_AVAILABLE)

# ── Profile Generation ───────────────────────────────────────

def load_procedures():
    """Load procedures from Postgres DB first, fall back to Google Sheets"""
    if config.DATABASE_URL:
        procedures = get_procedures_from_db()
        if procedures:
            return procedures
        print("⚠️  DB returned empty, falling back to Google Sheets")

    if config.GOOGLE_SHEETS_URL:
        return get_procedures_from_sheets(config.GOOGLE_SHEETS_URL)

    print("⚠️  No procedure source available")
    return []


@app.route('/generate', methods=['POST'])
@login_required
def generate_profile():
    try:
        doctor_url = request.json.get('doctor_url', '').strip()

        if not doctor_url:
            return jsonify({'error': 'Doctor URL is required'}), 400

        # Step 1: Scrape doctor webpage
        doctor_data = scrape_doctor_webpage(doctor_url)
        if not doctor_data:
            return jsonify({'error': 'Could not extract data from that URL. Check the link and try again.'}), 400

        # Step 2: Load procedures (DB first, then Sheets fallback)
        procedures_db = load_procedures()

        # Step 3: Match doctor to procedures
        matched_procedures = match_procedures(doctor_data, procedures_db)

        # Step 4: Generate Claude prompt
        prompt = generate_claude_prompt(doctor_data, matched_procedures)

        # Step 5: If Claude API is available, generate automatically
        if CLAUDE_AVAILABLE:
            try:
                client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                claude_response = message.content[0].text

                return jsonify({
                    'success': True,
                    'automated': True,
                    'doctor_data': doctor_data,
                    'matched_procedures': matched_procedures,
                    'claude_response': claude_response,
                    'claude_prompt': prompt
                })

            except Exception as api_error:
                print(f"[Claude API Error] {api_error}")
                # Fall back to manual mode
                return jsonify({
                    'success': True,
                    'automated': False,
                    'doctor_data': doctor_data,
                    'matched_procedures': matched_procedures,
                    'claude_prompt': prompt,
                    'api_error': str(api_error)
                })
        else:
            # Manual mode
            return jsonify({
                'success': True,
                'automated': False,
                'doctor_data': doctor_data,
                'matched_procedures': matched_procedures,
                'claude_prompt': prompt
            })

    except Exception as e:
        print(f"[Generate Error] {e}")
        return jsonify({'error': str(e)}), 500

# ── Document Creation ────────────────────────────────────────

@app.route('/create-document', methods=['POST'])
@login_required
def create_document():
    try:
        doctor_data = request.json.get('doctor_data')
        claude_response = request.json.get('claude_response')

        if not claude_response:
            return jsonify({'error': 'No profile content to create document from'}), 400

        doc_path = create_word_document(doctor_data, claude_response)

        doctor_name = (doctor_data or {}).get('name', 'doctor')
        safe_name = "".join(c for c in doctor_name if c.isalnum() or c in ' -_').strip().replace(' ', '_')
        filename = f"{safe_name}_profile_{datetime.now().strftime('%Y%m%d')}.docx"

        return send_file(
            doc_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"[Document Error] {e}")
        return jsonify({'error': str(e)}), 500

# ── Health Check ─────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'claude_available': CLAUDE_AVAILABLE,
        'db_connected': bool(config.DATABASE_URL),
        'timestamp': datetime.now().isoformat()
    })

# ── Run ──────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
