"""
🫚 Ginger Universe v3.1 — Web Scraper (Improved)
Multi-URL scraping with multiple extraction strategies:
  1. JSON-LD structured data (best quality — many hospital sites use this)
  2. Meta tags (og:description, description)
  3. Semantic HTML extraction (main, article, content divs)
  4. Full body text fallback
  5. Manual text input support
"""

import requests
from bs4 import BeautifulSoup
import re
import json


# ── User Agents (rotate to avoid blocks) ─────────────────────
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
]


def scrape_multiple_urls(urls, manual_text=''):
    """
    Scrapes multiple URLs and merges all extracted text.
    Also accepts manual_text pasted by the user.
    Returns combined data dict for Claude.
    """
    all_sections = []
    successful_urls = []
    all_titles = []
    errors = []

    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue

        data = scrape_single_url(url, agent_index=i)
        if data and data.get('text') and len(data['text'].strip()) > 50:
            all_sections.append(f"=== SOURCE: {url} ===\n{data['text']}")
            all_titles.append(data.get('title', ''))
            successful_urls.append(url)
        else:
            error_msg = data.get('error', 'No content extracted') if data else 'Request failed'
            errors.append(f"{url}: {error_msg}")

    # Add manual text if provided
    if manual_text and manual_text.strip():
        all_sections.append(f"=== MANUAL INPUT (pasted by user) ===\n{manual_text.strip()}")

    combined_text = '\n\n'.join(all_sections)

    if not combined_text.strip():
        return None

    return {
        'urls': successful_urls,
        'url_count': len(successful_urls),
        'combined_text': combined_text[:15000],
        'titles': [t for t in all_titles if t],
        'errors': errors,
        'has_manual_text': bool(manual_text and manual_text.strip()),
        'total_chars': len(combined_text),
    }


def scrape_single_url(url, agent_index=0):
    """
    Scrapes a single URL using multiple extraction strategies.
    Returns dict with 'text', 'title', 'method' or None on failure.
    """
    try:
        headers = {
            'User-Agent': USER_AGENTS[agent_index % len(USER_AGENTS)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)

        if response.status_code != 200:
            return {'text': '', 'title': '', 'error': f'HTTP {response.status_code}'}

        # Force UTF-8 if needed
        if response.encoding and response.encoding.lower() != 'utf-8':
            response.encoding = response.apparent_encoding or 'utf-8'

        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        # Get page title
        title = ''
        h1 = soup.find('h1')
        title_tag = soup.find('title')
        if h1:
            title = h1.get_text(strip=True)
        elif title_tag:
            title = title_tag.get_text(strip=True)

        # ── Strategy 1: JSON-LD structured data ──────────────
        jsonld_text = extract_jsonld(soup)
        if jsonld_text and len(jsonld_text) > 100:
            # Still try to get semantic content to supplement JSON-LD
            semantic_text = extract_semantic_content(soup)
            combined = f"[Page: {title}]\n\n--- Structured Data ---\n{jsonld_text}"
            if semantic_text and len(semantic_text) > 100:
                combined += f"\n\n--- Page Content ---\n{semantic_text}"
            return {
                'text': combined[:8000],
                'title': title,
                'method': 'json-ld'
            }

        # ── Strategy 2: Meta tags ────────────────────────────
        meta_text = extract_meta_tags(soup)

        # ── Strategy 3: Semantic HTML content ────────────────
        semantic_text = extract_semantic_content(soup)

        if semantic_text and len(semantic_text) > 200:
            full_text = f"[Page: {title}]\n"
            if meta_text:
                full_text += f"\n{meta_text}\n"
            full_text += f"\n{semantic_text}"
            return {
                'text': full_text[:8000],
                'title': title,
                'method': 'semantic'
            }

        # ── Strategy 4: Full body text fallback ──────────────
        body_text = extract_body_text(soup)

        if body_text and len(body_text) > 100:
            full_text = f"[Page: {title}]\n"
            if meta_text:
                full_text += f"\n{meta_text}\n"
            full_text += f"\n{body_text}"
            return {
                'text': full_text[:8000],
                'title': title,
                'method': 'body-text'
            }

        # ── Strategy 5: Last resort — meta only ─────────────
        if meta_text:
            return {
                'text': f"[Page: {title}]\n\n{meta_text}",
                'title': title,
                'method': 'meta-only'
            }

        return {
            'text': f"[Page: {title}]\n\n(Page appears to be JavaScript-rendered. Content could not be extracted automatically. Please paste the doctor's information manually using the text box below.)",
            'title': title,
            'error': 'JavaScript-rendered page — use manual input'
        }

    except requests.exceptions.Timeout:
        return {'text': '', 'title': '', 'error': 'Request timed out (20s)'}
    except requests.exceptions.ConnectionError as e:
        return {'text': '', 'title': '', 'error': f'Connection failed: {str(e)[:100]}'}
    except Exception as e:
        print(f"[Scrape Error] {url}: {e}")
        return {'text': '', 'title': '', 'error': str(e)[:200]}


# ═══════════════════════════════════════════════════════════════
# EXTRACTION STRATEGIES
# ═══════════════════════════════════════════════════════════════

def extract_jsonld(soup):
    """
    Extract structured data from JSON-LD scripts.
    Many hospital websites include Physician/MedicalBusiness schema.
    """
    texts = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw)

            # Handle @graph arrays
            items = data if isinstance(data, list) else [data]
            if isinstance(data, dict) and '@graph' in data:
                items = data['@graph']

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = item.get('@type', '')

                # Doctor/Physician profiles
                if item_type in ('Physician', 'Person', 'MedicalBusiness', 'LocalBusiness',
                                 'Hospital', 'MedicalOrganization', 'IndividualPhysician'):
                    parts = []
                    if item.get('name'):
                        parts.append(f"Name: {item['name']}")
                    if item.get('jobTitle'):
                        parts.append(f"Title: {item['jobTitle']}")
                    if item.get('description'):
                        parts.append(f"Description: {item['description']}")
                    if item.get('medicalSpecialty'):
                        spec = item['medicalSpecialty']
                        if isinstance(spec, list):
                            parts.append(f"Specialties: {', '.join(str(s) for s in spec)}")
                        else:
                            parts.append(f"Specialty: {spec}")
                    if item.get('qualification'):
                        quals = item['qualification']
                        if isinstance(quals, list):
                            parts.append(f"Qualifications: {', '.join(str(q.get('name','') if isinstance(q,dict) else q) for q in quals)}")
                        else:
                            parts.append(f"Qualification: {quals}")
                    if item.get('alumniOf'):
                        edu = item['alumniOf']
                        if isinstance(edu, list):
                            parts.append(f"Education: {', '.join(str(e.get('name','') if isinstance(e,dict) else e) for e in edu)}")
                        else:
                            parts.append(f"Education: {edu}")
                    if item.get('worksFor'):
                        org = item['worksFor']
                        if isinstance(org, dict):
                            parts.append(f"Hospital: {org.get('name', '')}")
                        elif isinstance(org, str):
                            parts.append(f"Hospital: {org}")
                    if item.get('address'):
                        addr = item['address']
                        if isinstance(addr, dict):
                            loc_parts = [addr.get('addressLocality',''), addr.get('addressRegion',''), addr.get('addressCountry','')]
                            parts.append(f"Location: {', '.join(p for p in loc_parts if p)}")
                    if item.get('memberOf'):
                        m = item['memberOf']
                        if isinstance(m, list):
                            parts.append(f"Memberships: {', '.join(str(x.get('name','') if isinstance(x,dict) else x) for x in m)}")
                        else:
                            parts.append(f"Memberships: {m}")
                    if item.get('knowsAbout'):
                        parts.append(f"Expertise: {item['knowsAbout']}")
                    if item.get('hasCredential'):
                        creds = item['hasCredential']
                        if isinstance(creds, list):
                            parts.append(f"Credentials: {', '.join(str(c.get('name','') if isinstance(c,dict) else c) for c in creds)}")

                    if parts:
                        texts.append('\n'.join(parts))

                # Also grab any item with substantial description
                elif item.get('description') and len(str(item['description'])) > 50:
                    texts.append(f"[{item_type}] {item.get('name','')}: {item['description']}")

        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    return '\n\n'.join(texts)


def extract_meta_tags(soup):
    """Extract useful meta tag content"""
    parts = []
    seen_content = set()

    meta_names = {
        'description': 'Description',
        'keywords': 'Keywords',
        'og:description': 'Description',
        'og:title': 'Title',
        'twitter:description': 'Description',
        'dc.description': 'Description',
    }

    for meta in soup.find_all('meta'):
        name = (meta.get('name', '') or meta.get('property', '')).lower()
        content = meta.get('content', '')
        if name in meta_names and content and len(content) > 10:
            if content not in seen_content:
                seen_content.add(content)
                parts.append(f"[{meta_names[name]}]: {content}")

    return '\n'.join(parts)


def extract_semantic_content(soup):
    """
    Extract text from semantic HTML elements.
    Removes noise first, then extracts from main content areas.
    """
    from copy import copy
    work = BeautifulSoup(str(soup), 'html.parser')

    # Remove noise elements
    noise_tags = ['script', 'style', 'nav', 'footer', 'header', 'iframe',
                  'noscript', 'svg', 'button', 'form', 'aside', 'figure']
    for tag in work.find_all(noise_tags):
        tag.decompose()

    # Remove by class/id patterns (common noise)
    noise_patterns = re.compile(
        r'(cookie|consent|popup|modal|banner|advert|sidebar|widget|social|share|comment|related|'
        r'newsletter|subscribe|breadcrumb|pagination|menu|nav-|foot|header|toolbar|sticky|overlay)',
        re.I
    )
    for el in work.find_all(class_=noise_patterns):
        el.decompose()
    for el in work.find_all(id=noise_patterns):
        el.decompose()

    # Try to find main content area (priority order)
    content_el = None
    for selector_tag, selector_attrs in [
        ('main', {}),
        ('article', {}),
        ('div', {'role': 'main'}),
        ('div', {'class': re.compile(r'(content|main|doctor|profile|detail|about|bio|description)', re.I)}),
        ('div', {'id': re.compile(r'(content|main|doctor|profile|detail|about|bio|description)', re.I)}),
        ('section', {'class': re.compile(r'(content|main|doctor|profile|detail|about|bio)', re.I)}),
    ]:
        found = work.find(selector_tag, selector_attrs)
        if found and len(found.get_text(strip=True)) > 150:
            content_el = found
            break

    if not content_el:
        content_el = work.find('body') or work

    # Extract with structure preserved
    text_parts = []
    seen = set()

    for element in content_el.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'li', 'td', 'th', 'dd', 'dt', 'blockquote']):
        # Skip elements that are parents of other block elements (avoid duplication)
        if element.name in ('div', 'section', 'td') and element.find(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
            continue

        text = element.get_text(separator=' ', strip=True)

        # Skip too short
        if not text or len(text) < 5:
            continue

        # Deduplicate
        text_clean = re.sub(r'\s+', ' ', text).strip()
        if text_clean in seen:
            continue
        seen.add(text_clean)

        # Format based on tag type
        if element.name in ('h1', 'h2', 'h3', 'h4', 'h5'):
            text_parts.append(f"\n## {text_clean}")
        elif element.name == 'li':
            text_parts.append(f"• {text_clean}")
        elif element.name == 'dt':
            text_parts.append(f"\n**{text_clean}**")
        elif element.name == 'dd':
            text_parts.append(f"  {text_clean}")
        else:
            text_parts.append(text_clean)

    return '\n'.join(text_parts)


def extract_body_text(soup):
    """Last resort: extract all visible text from body"""
    work = BeautifulSoup(str(soup), 'html.parser')

    for tag in work.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'svg']):
        tag.decompose()

    body = work.find('body') or work
    text = body.get_text(separator='\n', strip=True)

    # Clean up
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # Remove very short lines (likely nav items) unless they look like list items
    lines = [l for l in lines if len(l) > 10 or l.startswith(('•', '-', '*', '–'))]

    return '\n'.join(lines)
