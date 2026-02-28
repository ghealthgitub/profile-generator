"""
🫚 Ginger Universe — Database Connector
Connects to the shared Ginger Healthcare PostgreSQL database
Reads treatments + specialties directly (replaces Google Sheets dependency)
"""

import psycopg2
import psycopg2.extras
import config


def get_db_connection():
    """Get a connection to the shared PostgreSQL database"""
    if not config.DATABASE_URL:
        return None
    try:
        conn = psycopg2.connect(config.DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[DB Error] Could not connect: {e}")
        return None


def get_procedures_from_db():
    """
    Fetches treatments + specialties from the Ginger Healthcare database.
    Returns list of dicts matching the format the dictionary_matcher expects:
        { Entity_Name, Top_Specialty, Sub_Specialty, Complexity_Level }
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    t.id,
                    t.name              AS "Entity_Name",
                    t.slug,
                    s.name              AS "Top_Specialty",
                    s.category          AS "Sub_Specialty",
                    t.duration,
                    t.recovery_time,
                    t.success_rate,
                    t.cost_range_usd,
                    t.description
                FROM treatments t
                LEFT JOIN specialties s ON s.id = t.specialty_id
                WHERE t.status = 'published'
                ORDER BY s.name, t.name
            """)
            rows = cur.fetchall()

        # Convert RealDictRow objects to plain dicts
        procedures = []
        for row in rows:
            procedures.append({
                'Entity_Name': row.get('Entity_Name', ''),
                'Top_Specialty': row.get('Top_Specialty', ''),
                'Sub_Specialty': row.get('Sub_Specialty', '') or '',
                'Complexity_Level': '',  # Not in DB schema yet, safe default
                'slug': row.get('slug', ''),
                'duration': row.get('duration', ''),
                'recovery_time': row.get('recovery_time', ''),
                'success_rate': row.get('success_rate', ''),
                'cost_range_usd': row.get('cost_range_usd', ''),
                'description': row.get('description', ''),
            })

        print(f"✅ Loaded {len(procedures)} procedures from PostgreSQL database")
        return procedures

    except Exception as e:
        print(f"[DB Error] Failed to load procedures: {e}")
        return []
    finally:
        conn.close()


def get_specialties_from_db():
    """Fetches list of published specialties for dropdown / reference"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, slug, icon, category
                FROM specialties
                WHERE status = 'published'
                ORDER BY display_order, name
            """)
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] Failed to load specialties: {e}")
        return []
    finally:
        conn.close()


def get_hospitals_from_db():
    """Fetches list of published hospitals for reference"""
    conn = get_db_connection()
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
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"[DB Error] Failed to load hospitals: {e}")
        return []
    finally:
        conn.close()
