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
