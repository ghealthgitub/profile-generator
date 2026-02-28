"""
🫚 GINGER UNIVERSE v3 — Doctor Profile Generator
Full rebuild: DB auth, multi-URL scraping, editable prompts, profile history
"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from functools import wraps
import os, json
from datetime import datetime

import config
from utils.scraper import scrape_multiple_urls
from utils.prompt_builder import build_prompt
from utils.doc_generator import create_word_document
from utils.db_connector import (
    init_generator_tables, authenticate_user,
    get_treatment_dictionary, get_specialties_list, get_hospitals_list,
    get_active_prompt, get_all_prompts, save_prompt,
    save_profile, update_profile_content, get_recent_profiles,
    get_profile_by_id, get_profile_stats,
    get_destinations_list, get_treatments_for_specialty,
    push_doctor_to_admin, search_existing_doctors
)

# Claude API
CLAUDE_AVAILABLE = False
try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = bool(config.ANTHROPIC_API_KEY)
    print(f"{'✅' if CLAUDE_AVAILABLE else '⚠️'} Claude API: {'ready' if CLAUDE_AVAILABLE else 'no key set'}")
except ImportError:
    print("⚠️  anthropic package not installed")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Initialize generator tables on startup
with app.app_context():
    init_generator_tables()

# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        if session['user'].get('role') != 'super_admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = authenticate_user(email, password)
        if user:
            session['user'] = user
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials or insufficient permissions")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    stats = get_profile_stats()
    recent = get_recent_profiles(10)
    specialties = get_specialties_list()
    return render_template('dashboard.html',
        user=session['user'],
        claude_available=CLAUDE_AVAILABLE,
        stats=stats,
        recent_profiles=recent,
        specialty_count=len(specialties),
        treatment_count=len(get_treatment_dictionary()),
        admin_url=config.ADMIN_URL
    )


@app.route('/push')
@login_required
def push_page():
    profile_id = request.args.get('profile_id', '')
    return render_template('push.html',
        user=session['user'],
        profile_id=profile_id,
        admin_url=config.ADMIN_URL
    )


# ═══════════════════════════════════════════════════════════════
# GENERATE PROFILE
# ═══════════════════════════════════════════════════════════════

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    try:
        urls = request.json.get('urls', [])
        urls = [u.strip() for u in urls if u.strip()]
        manual_text = request.json.get('manual_text', '').strip()

        if not urls and not manual_text:
            return jsonify({'error': 'Provide at least one URL or paste doctor information manually'}), 400

        # Step 1: Scrape all URLs + include manual text
        scraped = scrape_multiple_urls(urls, manual_text=manual_text)
        if not scraped:
            error_msg = 'Could not extract content from the given URL(s). '
            if urls:
                error_msg += 'The website may be JavaScript-rendered (React/Next.js) which blocks automated reading. '
            error_msg += 'Please paste the doctor\'s information manually using the text box below the URL field.'
            return jsonify({'error': error_msg}), 400

        # Step 2: Load treatment dictionary from DB
        treatments = get_treatment_dictionary()

        # Step 3: Get active prompt template
        prompt_data = get_active_prompt()
        prompt_template = prompt_data.get('prompt_text', '') if isinstance(prompt_data, dict) else prompt_data

        # Step 4: Build final prompt
        final_prompt = build_prompt(prompt_template, scraped, treatments)

        # Step 5: Call Claude if available
        if CLAUDE_AVAILABLE:
            try:
                client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": final_prompt}]
                )
                claude_response = message.content[0].text

                # Extract doctor name from response or scraped titles
                doctor_name = extract_doctor_name(scraped, claude_response)

                # Save to history
                profile_id = save_profile(
                    doctor_name, urls, scraped,
                    [], final_prompt, claude_response,
                    session['user']['email']
                )

                return jsonify({
                    'success': True,
                    'automated': True,
                    'profile_id': profile_id,
                    'doctor_name': doctor_name,
                    'scraped_data': scraped,
                    'claude_response': claude_response,
                    'prompt_used': final_prompt,
                    'treatment_count': len(treatments)
                })

            except Exception as e:
                print(f"[Claude Error] {e}")
                return jsonify({
                    'success': True,
                    'automated': False,
                    'scraped_data': scraped,
                    'prompt': final_prompt,
                    'api_error': str(e)
                })
        else:
            return jsonify({
                'success': True,
                'automated': False,
                'scraped_data': scraped,
                'prompt': final_prompt
            })

    except Exception as e:
        print(f"[Generate Error] {e}")
        return jsonify({'error': str(e)}), 500


def extract_doctor_name(scraped, claude_text=''):
    """Try to extract doctor name from scraped titles or Claude response"""
    import re
    titles = scraped.get('titles', [])
    for title in titles:
        match = re.search(r'(?:Dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})', title)
        if match:
            return match.group(0)
    # Try from Claude response first line
    if claude_text:
        first_lines = claude_text[:500]
        match = re.search(r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', first_lines)
        if match:
            return match.group(0)
    return "Doctor Profile"


# ═══════════════════════════════════════════════════════════════
# SAVE / EDIT PROFILE
# ═══════════════════════════════════════════════════════════════

@app.route('/api/profile/<int:profile_id>/save', methods=['POST'])
@login_required
def save_edited_profile(profile_id):
    content = request.json.get('content', '')
    if not content:
        return jsonify({'error': 'No content provided'}), 400
    ok = update_profile_content(profile_id, content, 'edited')
    return jsonify({'success': ok})


@app.route('/api/profile/<int:profile_id>', methods=['GET'])
@login_required
def get_profile(profile_id):
    profile = get_profile_by_id(profile_id)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    # Convert datetime objects to strings for JSON
    for key in ('created_at', 'updated_at'):
        if profile.get(key):
            profile[key] = profile[key].isoformat()
    return jsonify(profile)


# ═══════════════════════════════════════════════════════════════
# DOCUMENT DOWNLOAD
# ═══════════════════════════════════════════════════════════════

@app.route('/create-document', methods=['POST'])
@login_required
def create_doc():
    try:
        doctor_name = request.json.get('doctor_name', 'Doctor')
        content = request.json.get('content', '')
        if not content:
            return jsonify({'error': 'No content'}), 400

        filepath = create_word_document(doctor_name, content)
        safe = "".join(c for c in doctor_name if c.isalnum() or c in ' -_').strip().replace(' ', '_')
        return send_file(filepath, as_attachment=True,
                         download_name=f"{safe}_profile_{datetime.now().strftime('%Y%m%d')}.docx")
    except Exception as e:
        print(f"[Doc Error] {e}")
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# PROMPT MANAGEMENT (admin only)
# ═══════════════════════════════════════════════════════════════

@app.route('/prompts')
@admin_required
def prompts_page():
    all_prompts = get_all_prompts()
    return render_template('prompts.html', user=session['user'], prompts=all_prompts)


@app.route('/api/prompts', methods=['GET'])
@admin_required
def api_get_prompts():
    prompts = get_all_prompts()
    for p in prompts:
        for key in ('created_at', 'updated_at'):
            if p.get(key):
                p[key] = p[key].isoformat()
    return jsonify(prompts)


@app.route('/api/prompts', methods=['POST'])
@admin_required
def api_save_prompt():
    data = request.json
    ok = save_prompt(
        data.get('id'),
        data.get('name', 'Untitled'),
        data.get('prompt_text', ''),
        data.get('set_active', False),
        session['user']['email']
    )
    return jsonify({'success': ok})


# ═══════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════

@app.route('/history')
@login_required
def history_page():
    profiles = get_recent_profiles(50)
    return render_template('history.html', user=session['user'], profiles=profiles)


# ═══════════════════════════════════════════════════════════════
# DB STATS (for dashboard)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/db-stats')
@login_required
def api_db_stats():
    return jsonify({
        'specialties': len(get_specialties_list()),
        'treatments': len(get_treatment_dictionary()),
        'hospitals': len(get_hospitals_list()),
    })


# ═══════════════════════════════════════════════════════════════
# PUSH TO ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route('/api/push-data')
@login_required
def push_data():
    """Returns dropdowns data for the Push to Admin modal"""
    specialties = get_specialties_list()
    hospitals = get_hospitals_list()
    destinations = get_destinations_list()
    return jsonify({
        'specialties': specialties,
        'hospitals': hospitals,
        'destinations': destinations
    })


@app.route('/api/push-treatments/<int:specialty_id>')
@login_required
def push_treatments(specialty_id):
    """Returns treatments for a given specialty (for the treatments checklist)"""
    treatments = get_treatments_for_specialty(specialty_id)
    return jsonify(treatments)


@app.route('/api/auto-extract', methods=['POST'])
@login_required
def auto_extract():
    """
    Uses Claude to extract structured fields from the generated profile.
    Returns JSON with: name, specialty, hospital, city, experience_years,
    qualifications, languages, description, suggested_treatments
    """
    if not CLAUDE_AVAILABLE:
        return jsonify({'error': 'Claude API not available'}), 400

    profile_text = request.json.get('profile_text', '')
    scraped_text = request.json.get('scraped_text', '')

    if not profile_text:
        return jsonify({'error': 'No profile text'}), 400

    # Get available data for context
    specialties = get_specialties_list()
    hospitals = get_hospitals_list()
    destinations = get_destinations_list()

    spec_names = [s['name'] for s in specialties]
    hosp_names = [h['name'] for h in hospitals]
    dest_names = [d['name'] for d in destinations]

    extract_prompt = f"""Extract structured data from this doctor profile. Return ONLY valid JSON, no other text.

AVAILABLE SPECIALTIES (pick the best match):
{', '.join(spec_names)}

AVAILABLE HOSPITALS (pick the best match):
{', '.join(hosp_names)}

AVAILABLE DESTINATIONS (countries):
{', '.join(dest_names)}

DOCTOR PROFILE:
{profile_text[:4000]}

{('ADDITIONAL SCRAPED DATA:' + scraped_text[:2000]) if scraped_text else ''}

Return JSON with these exact keys:
{{
  "name": "Doctor full name without Dr./Prof. prefix",
  "title": "Dr." or "Prof." etc,
  "designation": "Their role/position e.g. Senior Consultant, Director, Group Chairman, Head of Department etc.",
  "specialty": "Best matching specialty from the list above (exact name)",
  "hospital": "Best matching hospital from the list above (exact name)",
  "destination": "Best matching destination from the list above (exact name)",
  "city": "City name",
  "experience_years": number or null,
  "qualifications": ["MBBS", "MS", "MCh", "FRCS", etc],
  "languages": ["English", "Hindi", etc],
  "description": "One-line summary under 150 chars for listing cards",
  "suggested_treatments": ["ALL treatment/procedure names mentioned in the profile — be comprehensive, list every single one"]
}}

CRITICAL INSTRUCTIONS:
1. QUALIFICATIONS: Look very carefully for degree abbreviations like MBBS, MD, MS, MCh, DNB, DM, FRCS, FACS, FIMSA, MRCS, MNAMS, PhD, Diploma, Fellowship etc. These appear in the profile text, in scraped data, in credential lists, after the doctor's name, or in education sections. Extract ALL of them. Do NOT leave this empty if any degrees are mentioned anywhere.
2. EXPERIENCE: If experience_years is not directly stated, calculate it: find the year of MBBS/MD/MS graduation or "practicing since" year. Subtract from 2026. For example, MBBS 1985 → 2026-1985 = 41 years. If only a career start year is mentioned (e.g. "career spanning 3 decades since 1990"), calculate from that.
3. TREATMENTS: List EVERY procedure, surgery, and treatment mentioned anywhere in the profile. Be exhaustive — include all specific procedures (e.g. "total knee replacement", "ACL reconstruction", "arthroscopy", "robotic surgery" etc).
4. For specialty, hospital, and destination — ONLY use names from the lists provided above. Pick the closest match.

Return ONLY the JSON object."""

    try:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": extract_prompt}]
        )
        raw = message.content[0].text.strip()

        # Clean JSON from markdown fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith('json'):
            raw = raw[4:].strip()

        import json as json_mod
        extracted = json_mod.loads(raw)

        # Match to IDs
        spec_match = next((s for s in specialties if s['name'] == extracted.get('specialty')), None)
        hosp_match = next((h for h in hospitals if h['name'] == extracted.get('hospital')), None)
        dest_match = next((d for d in destinations if d['name'] == extracted.get('destination')), None)

        extracted['specialty_id'] = spec_match['id'] if spec_match else None
        extracted['hospital_id'] = hosp_match['id'] if hosp_match else None
        extracted['destination_id'] = dest_match['id'] if dest_match else None
        extracted['hospital_city'] = hosp_match.get('city', '') if hosp_match else ''

        return jsonify(extracted)

    except Exception as e:
        print(f"[Extract Error] {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/push-doctor', methods=['POST'])
@login_required
def push_doctor():
    """Push a generated profile into the doctors table"""
    try:
        data = request.json
        profile_id = data.pop('profile_id', None)
        result = push_doctor_to_admin(data, profile_id, session['user']['email'])
        return jsonify(result)
    except Exception as e:
        print(f"[Push Error] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search-doctors')
@login_required
def api_search_doctors():
    """Search existing doctors for 'update existing' mode"""
    q = request.args.get('q', '')
    doctors = search_existing_doctors(q)
    return jsonify(doctors)


# ═══════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '3.0',
        'claude_available': CLAUDE_AVAILABLE,
        'db_connected': bool(config.DATABASE_URL),
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
