"""
🫚 Ginger Universe v3 — Database Connector
Connects to shared Ginger Healthcare PostgreSQL database
Handles: auth, treatments/specialties lookup, prompt storage, profile history
"""

import psycopg2
import psycopg2.extras
import config
import bcrypt
import json
from datetime import datetime


def get_conn():
    if not config.DATABASE_URL:
        return None
    try:
        return psycopg2.connect(config.DATABASE_URL)
    except Exception as e:
        print(f"[DB Error] {e}")
        return None


# ── Bootstrap (create generator-specific tables) ─────────────

def init_generator_tables():
    """Create tables specific to the profile generator (won't touch existing schema)"""
    conn = get_conn()
    if not conn:
        print("⚠️  No DB — running without generator tables")
        return
    try:
        with conn.cursor() as cur:
            # Prompt templates (admin-editable)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generator_prompts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    prompt_text TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT false,
                    created_by VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Generated profiles history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generator_profiles (
                    id SERIAL PRIMARY KEY,
                    doctor_name VARCHAR(300),
                    source_urls TEXT[],
                    scraped_data JSONB,
                    matched_procedures JSONB,
                    prompt_used TEXT,
                    generated_content TEXT,
                    edited_content TEXT,
                    status VARCHAR(30) DEFAULT 'generated',
                    created_by VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Check if default prompt exists
            cur.execute("SELECT COUNT(*) FROM generator_prompts WHERE is_active = true")
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("""
                    INSERT INTO generator_prompts (name, prompt_text, is_active, created_by)
                    VALUES ('Default Profile Generator', %s, true, 'system')
                """, [DEFAULT_PROMPT])
            conn.commit()
        print("✅ Generator tables ready")
    except Exception as e:
        print(f"[DB Init Error] {e}")
        conn.rollback()
    finally:
        conn.close()


# ── Auth (uses existing ginger-admin users table) ────────────

def authenticate_user(email, password):
    """
    Authenticate against the shared users table (same as ginger-admin).
    Returns user dict or None.
    Only super_admin and editor roles are allowed.
    """
    # First check env-var admin
    if email == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
        return {
            'id': 0,
            'name': 'Admin',
            'email': email,
            'role': 'super_admin',
            'source': 'env'
        }

    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, email, password, role, is_active
                FROM users
                WHERE email = %s AND is_active = true
            """, [email])
            user = cur.fetchone()
            if user and user['role'] in ('super_admin', 'editor'):
                if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    return {
                        'id': user['id'],
                        'name': user['name'],
                        'email': user['email'],
                        'role': user['role'],
                        'source': 'db'
                    }
    except Exception as e:
        print(f"[Auth Error] {e}")
    finally:
        conn.close()
    return None


# ── Treatment Dictionary ─────────────────────────────────────

def get_treatment_dictionary():
    """
    Returns the FULL treatment dictionary for Claude prompt injection.
    Format: list of { name, specialty, category, slug, description }
    """
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT t.name, t.slug, t.description,
                       t.duration, t.recovery_time, t.success_rate, t.cost_range_usd,
                       s.name AS specialty, s.category AS specialty_category
                FROM treatments t
                LEFT JOIN specialties s ON s.id = t.specialty_id
                WHERE t.status = 'published'
                ORDER BY s.name, t.name
            """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] get_treatment_dictionary: {e}")
        return []
    finally:
        conn.close()


def get_specialties_list():
    """Returns all published specialties for reference"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, slug, icon, category,
                       (SELECT COUNT(*) FROM treatments t WHERE t.specialty_id = s.id AND t.status='published') as treatment_count
                FROM specialties s
                WHERE s.status = 'published'
                ORDER BY s.display_order, s.name
            """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


def get_hospitals_list():
    """Returns all published hospitals"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT h.id, h.name, h.slug, h.city, h.country,
                       d.name AS destination_name
                FROM hospitals h
                LEFT JOIN destinations d ON d.id = h.destination_id
                WHERE h.status = 'published'
                ORDER BY h.name
            """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


# ── Prompt Management ────────────────────────────────────────

def get_active_prompt():
    """Returns the currently active prompt template"""
    conn = get_conn()
    if not conn:
        return DEFAULT_PROMPT
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM generator_prompts WHERE is_active = true ORDER BY updated_at DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else {'id': 0, 'name': 'Default', 'prompt_text': DEFAULT_PROMPT}
    except Exception as e:
        print(f"[DB Error] {e}")
        return {'id': 0, 'name': 'Default', 'prompt_text': DEFAULT_PROMPT}
    finally:
        conn.close()


def get_all_prompts():
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM generator_prompts ORDER BY is_active DESC, updated_at DESC")
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


def save_prompt(prompt_id, name, prompt_text, set_active, user_email):
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            if set_active:
                cur.execute("UPDATE generator_prompts SET is_active = false")
            if prompt_id:
                cur.execute("""
                    UPDATE generator_prompts
                    SET name=%s, prompt_text=%s, is_active=%s, updated_at=NOW()
                    WHERE id=%s
                """, [name, prompt_text, set_active, prompt_id])
            else:
                cur.execute("""
                    INSERT INTO generator_prompts (name, prompt_text, is_active, created_by)
                    VALUES (%s, %s, %s, %s)
                """, [name, prompt_text, set_active, user_email])
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB Error] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# ── Profile History ──────────────────────────────────────────

def save_profile(doctor_name, source_urls, scraped_data, matched_procs, prompt_used, content, user_email):
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO generator_profiles
                    (doctor_name, source_urls, scraped_data, matched_procedures,
                     prompt_used, generated_content, edited_content, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'generated', %s)
                RETURNING id
            """, [
                doctor_name, source_urls,
                json.dumps(scraped_data), json.dumps(matched_procs),
                prompt_used, content, content, user_email
            ])
            conn.commit()
            return cur.fetchone()[0]
    except Exception as e:
        print(f"[DB Error] save_profile: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_profile_content(profile_id, edited_content, status='edited'):
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE generator_profiles
                SET edited_content=%s, status=%s, updated_at=NOW()
                WHERE id=%s
            """, [edited_content, status, profile_id])
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB Error] {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_recent_profiles(limit=20):
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, doctor_name, source_urls, status, created_by, created_at
                FROM generator_profiles
                ORDER BY created_at DESC LIMIT %s
            """, [limit])
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


def get_profile_by_id(profile_id):
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM generator_profiles WHERE id = %s", [profile_id])
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB Error] {e}")
        return None
    finally:
        conn.close()


def get_profile_stats():
    conn = get_conn()
    if not conn:
        return {'total': 0, 'today': 0, 'week': 0}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS today,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') AS week
                FROM generator_profiles
            """)
            return dict(cur.fetchone())
    except Exception as e:
        print(f"[DB Error] {e}")
        return {'total': 0, 'today': 0, 'week': 0}
    finally:
        conn.close()


# ── Push to Admin (doctors table) ─────────────────────────────

def get_destinations_list():
    """Returns all published destinations for the push modal"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, slug, flag
                FROM destinations
                WHERE status = 'published'
                ORDER BY display_order, name
            """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


def get_treatments_for_specialty(specialty_id):
    """Returns treatments belonging to a specialty (for junction table linking)"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, slug
                FROM treatments
                WHERE specialty_id = %s AND status = 'published'
                ORDER BY name
            """, [specialty_id])
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


def check_doctor_slug_exists(slug):
    """Check if a doctor slug already exists"""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM doctors WHERE slug = %s", [slug])
            return cur.fetchone() is not None
    except Exception as e:
        print(f"[DB Error] {e}")
        return False
    finally:
        conn.close()


def generate_doctor_slug(name):
    """Generate a unique slug for a doctor"""
    import re
    base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = base
    counter = 1
    while check_doctor_slug_exists(slug):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def push_doctor_to_admin(data, profile_id=None, user_email=''):
    """
    Inserts or updates a doctor record in the main doctors table.
    Also links treatments via doctor_treatments junction table.

    data keys:
        name, title, specialty_id, hospital_id, destination_id,
        experience_years, qualifications[], languages[],
        description (short), long_description (full profile),
        city, country, treatments[] (list of treatment IDs),
        meta_title, meta_description, status
    """
    conn = get_conn()
    if not conn:
        return {'success': False, 'error': 'Database not connected'}

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            name = data.get('name', '').strip()
            if not name:
                return {'success': False, 'error': 'Doctor name is required'}

            slug = data.get('slug') or generate_doctor_slug(name)
            title = data.get('title', 'Dr.')
            specialty_id = data.get('specialty_id')
            hospital_id = data.get('hospital_id')
            destination_id = data.get('destination_id')
            experience_years = data.get('experience_years')
            qualifications = data.get('qualifications', [])
            languages = data.get('languages', [])
            description = data.get('description', '')
            long_description = data.get('long_description', '')
            city = data.get('city', '')
            country = data.get('country', '')
            meta_title = data.get('meta_title', '')
            meta_description = data.get('meta_description', '')
            status = data.get('status', 'draft')
            treatment_ids = data.get('treatment_ids', [])

            # Get legacy text values for backward compat columns
            specialty_text = ''
            if specialty_id:
                cur.execute("SELECT name FROM specialties WHERE id = %s", [specialty_id])
                row = cur.fetchone()
                if row:
                    specialty_text = row['name']

            # Check if doctor already exists (by slug)
            existing_id = data.get('existing_doctor_id')
            if existing_id:
                # UPDATE existing doctor
                cur.execute("""
                    UPDATE doctors SET
                        name=%s, title=%s, slug=%s,
                        specialty=%s, specialty_id=%s,
                        hospital_id=%s, destination_id=%s,
                        country=%s, city=%s,
                        experience_years=%s, qualifications=%s,
                        description=%s, long_description=%s,
                        languages=%s,
                        meta_title=%s, meta_description=%s,
                        status=%s, updated_at=NOW()
                    WHERE id=%s
                    RETURNING id
                """, [
                    name, title, slug,
                    specialty_text, specialty_id,
                    hospital_id, destination_id,
                    country, city,
                    experience_years, qualifications,
                    description, long_description,
                    languages,
                    meta_title, meta_description,
                    status, existing_id
                ])
                doctor_id = existing_id
            else:
                # INSERT new doctor
                cur.execute("""
                    INSERT INTO doctors
                        (name, title, slug, specialty, specialty_id,
                         hospital_id, destination_id, country, city,
                         experience_years, qualifications,
                         description, long_description, languages,
                         meta_title, meta_description, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, [
                    name, title, slug, specialty_text, specialty_id,
                    hospital_id, destination_id, country, city,
                    experience_years, qualifications,
                    description, long_description, languages,
                    meta_title, meta_description, status
                ])
                doctor_id = cur.fetchone()['id']

            # Link treatments via junction table
            if treatment_ids and doctor_id:
                # Clear existing links
                cur.execute("DELETE FROM doctor_treatments WHERE doctor_id = %s", [doctor_id])
                for tid in treatment_ids:
                    try:
                        cur.execute("""
                            INSERT INTO doctor_treatments (doctor_id, treatment_id)
                            VALUES (%s, %s) ON CONFLICT DO NOTHING
                        """, [doctor_id, tid])
                    except Exception:
                        pass  # Skip if junction insert fails

            # Update generator_profiles status to 'pushed'
            if profile_id:
                cur.execute("""
                    UPDATE generator_profiles
                    SET status='pushed', updated_at=NOW()
                    WHERE id=%s
                """, [profile_id])

            conn.commit()

            # Build the doctor's public URL
            dest_slug = ''
            if destination_id:
                cur.execute("SELECT slug FROM destinations WHERE id = %s", [destination_id])
                dest_row = cur.fetchone()
                if dest_row:
                    dest_slug = dest_row['slug']

            public_url = f"/destinations/{dest_slug}/doctors/{slug}/" if dest_slug else ''

            return {
                'success': True,
                'doctor_id': doctor_id,
                'slug': slug,
                'public_url': public_url,
                'is_update': bool(existing_id)
            }

    except Exception as e:
        print(f"[DB Error] push_doctor_to_admin: {e}")
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()


def search_existing_doctors(query=''):
    """Search existing doctors for the 'update existing' feature"""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if query:
                cur.execute("""
                    SELECT id, name, slug, specialty, city, country, status
                    FROM doctors
                    WHERE LOWER(name) LIKE %s OR LOWER(slug) LIKE %s
                    ORDER BY name LIMIT 20
                """, [f'%{query.lower()}%', f'%{query.lower()}%'])
            else:
                cur.execute("""
                    SELECT id, name, slug, specialty, city, country, status
                    FROM doctors
                    ORDER BY created_at DESC LIMIT 20
                """)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] {e}")
        return []
    finally:
        conn.close()


# ── Default Prompt ───────────────────────────────────────────

DEFAULT_PROMPT = """You are a professional medical content writer for Ginger Healthcare (ginger.healthcare), a medical tourism platform.

TASK: Create a comprehensive, professional doctor profile using ONLY the information provided below.

═══════════════════════════════════════════════════
DOCTOR INFORMATION (scraped from source URLs):
═══════════════════════════════════════════════════
{scraped_data}

═══════════════════════════════════════════════════
TREATMENT DICTIONARY (from our database):
These are the ONLY treatments/procedures you may reference.
Match the doctor to procedures from this list based on their specialty.
═══════════════════════════════════════════════════
{treatment_dictionary}

═══════════════════════════════════════════════════
INSTRUCTIONS:
═══════════════════════════════════════════════════

Write a professional doctor profile with these sections:

**PROFESSIONAL SUMMARY**
2-3 paragraphs introducing the doctor. Highlight specializations, experience, achievements. Warm, professional tone for international patients.

**SPECIALIZATIONS**
Bullet list of main medical specialties (use the specialty names from our treatment dictionary above)

**PROCEDURES & EXPERTISE**
Bullet list of 8-12 specific procedures this doctor performs. ONLY use procedures that exist in our treatment dictionary AND match the doctor's actual specialty. Do NOT include procedures from unrelated specialties.

**EDUCATION & QUALIFICATIONS**
Bullet list of degrees, certifications, fellowships.

**PROFESSIONAL EXPERIENCE**
2-3 sentences about career journey, key positions, years of experience.

**HOSPITAL AFFILIATIONS**
Bullet list of hospitals/medical centers.

**AWARDS & RECOGNITION**
Bullet list if available, otherwise write "Information not available from provided sources."

CRITICAL RULES:
1. ONLY include information verifiable from the provided scraped data
2. ONLY reference procedures from our treatment dictionary
3. Do NOT invent qualifications, awards, or experience not in the source data
4. Do NOT include procedures from unrelated specialties
5. Keep tone warm, professional, patient-friendly
6. Total length: 500-700 words
7. If information is missing, say "Information not available" — do NOT guess"""
