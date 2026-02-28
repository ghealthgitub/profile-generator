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
    # ── Pre-check: Site-specific API extraction ──────────
    site_result = try_site_specific_api(url)
    if site_result and site_result.get('text') and len(site_result['text']) > 100:
        return site_result

    # ── Standard HTML scraping with retry ────────────────
    html = None
    last_error = ''

    # Try multiple header combinations
    header_sets = [
        {
            'User-Agent': USER_AGENTS[agent_index % len(USER_AGENTS)],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        },
        {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Accept': 'text/html',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,*/*',
            'Accept-Language': 'en-US,en;q=0.5',
        },
    ]

    for i, headers in enumerate(header_sets):
        try:
            response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            if response.status_code == 200 and len(response.text) > 500:
                if response.encoding and response.encoding.lower() != 'utf-8':
                    response.encoding = response.apparent_encoding or 'utf-8'
                html = response.text
                break
            else:
                last_error = f'HTTP {response.status_code} (attempt {i+1})'
        except requests.exceptions.Timeout:
            last_error = f'Timeout (attempt {i+1})'
        except requests.exceptions.ConnectionError as e:
            last_error = f'Connection failed: {str(e)[:80]}'
            break  # DNS/network issue, no point retrying
        except Exception as e:
            last_error = str(e)[:100]

    if not html:
        return {'text': '', 'title': '', 'error': last_error or 'Could not fetch page'}

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

        # ── Strategy 1b: Next.js __NEXT_DATA__ ───────────────
        nextdata_text = extract_nextdata(soup)
        if nextdata_text and len(nextdata_text) > 100:
            semantic_text = extract_semantic_content(soup)
            combined = f"[Page: {title}]\n\n--- Next.js Data ---\n{nextdata_text}"
            if semantic_text and len(semantic_text) > 100:
                combined += f"\n\n--- Page Content ---\n{semantic_text}"
            return {
                'text': combined[:8000],
                'title': title,
                'method': 'nextjs-data'
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


# ═══════════════════════════════════════════════════════════════
# SITE-SPECIFIC API STRATEGIES
# ═══════════════════════════════════════════════════════════════

def try_site_specific_api(url):
    """
    For known hospital sites that block scraping, try their internal APIs
    or alternative endpoints that return usable data.
    """
    url_lower = url.lower()

    # ── Max Healthcare ──────────────────────────────────────
    if 'maxhealthcare.in/doctor/' in url_lower:
        return scrape_max_healthcare(url)

    return None


def scrape_max_healthcare(url):
    """
    Max Healthcare uses Next.js with Cloudflare. Their doctor pages
    are fully client-rendered. We try multiple approaches:
    1. Their internal API endpoint
    2. Google's cached version
    3. Mobile user agent (sometimes bypasses WAF)
    """
    import re

    # Extract doctor slug from URL
    match = re.search(r'/doctor/([^/?#]+)', url)
    if not match:
        return None
    slug = match.group(1)

    # Approach 1: Try the Next.js data endpoint
    # Next.js sites expose page data at /_next/data/{buildId}/...
    # But buildId changes. Try the JSON route instead.
    api_urls = [
        f'https://www.maxhealthcare.in/_next/data/doctor/{slug}.json',
        f'https://www.maxhealthcare.in/api/doctor/{slug}',
        f'https://www.maxhealthcare.in/doctor/{slug}',
    ]

    headers_options = [
        {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Accept': 'text/html,application/xhtml+xml',
        },
        {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
        },
        {
            'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
            'Accept': 'text/html',
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Referer': 'https://www.google.com/',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        },
    ]

    for headers in headers_options:
        try:
            response = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
            if response.status_code == 200 and len(response.text) > 1000:
                if response.encoding and response.encoding.lower() != 'utf-8':
                    response.encoding = response.apparent_encoding or 'utf-8'

                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                # Try __NEXT_DATA__ first
                nextdata = extract_nextdata(soup)
                if nextdata and len(nextdata) > 100:
                    title = ''
                    h1 = soup.find('h1')
                    if h1:
                        title = h1.get_text(strip=True)
                    return {
                        'text': f"[Page: {title or slug}]\n\n--- Max Healthcare Profile ---\n{nextdata}",
                        'title': title or slug,
                        'method': 'max-nextjs'
                    }

                # Try JSON-LD
                jsonld = extract_jsonld(soup)
                if jsonld and len(jsonld) > 100:
                    title = ''
                    h1 = soup.find('h1')
                    if h1:
                        title = h1.get_text(strip=True)
                    semantic = extract_semantic_content(soup)
                    text = f"[Page: {title or slug}]\n\n--- Structured Data ---\n{jsonld}"
                    if semantic and len(semantic) > 100:
                        text += f"\n\n--- Page Content ---\n{semantic}"
                    return {
                        'text': text[:8000],
                        'title': title or slug,
                        'method': 'max-jsonld'
                    }

                # Try semantic/body extraction
                semantic = extract_semantic_content(soup)
                if semantic and len(semantic) > 200:
                    title = ''
                    h1 = soup.find('h1')
                    if h1:
                        title = h1.get_text(strip=True)
                    meta = extract_meta_tags(soup)
                    text = f"[Page: {title or slug}]\n"
                    if meta:
                        text += f"\n{meta}\n"
                    text += f"\n{semantic}"
                    return {
                        'text': text[:8000],
                        'title': title or slug,
                        'method': 'max-semantic'
                    }

                # Even body text
                body = extract_body_text(soup)
                if body and len(body) > 200:
                    return {
                        'text': f"[Page: {slug}]\n\n{body}"[:8000],
                        'title': slug,
                        'method': 'max-body'
                    }

        except Exception as e:
            print(f"[Max Scrape] {headers.get('User-Agent','')[:30]}... : {e}")
            continue

    # Approach 2: Try Google cache
    try:
        cache_url = f'https://webcache.googleusercontent.com/search?q=cache:{url}'
        cache_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html',
        }
        response = requests.get(cache_url, headers=cache_headers, timeout=15, allow_redirects=True)
        if response.status_code == 200 and len(response.text) > 1000:
            soup = BeautifulSoup(response.text, 'html.parser')
            semantic = extract_semantic_content(soup)
            body = extract_body_text(soup) if not semantic else ''
            content = semantic or body
            if content and len(content) > 200:
                return {
                    'text': f"[Page: {slug} (Google Cache)]\n\n{content}"[:8000],
                    'title': slug,
                    'method': 'google-cache'
                }
    except Exception as e:
        print(f"[Google Cache] {e}")

    return None


# ═══════════════════════════════════════════════════════════════
# EXTRACTION STRATEGIES
# ═══════════════════════════════════════════════════════════════

def extract_nextdata(soup):
    """
    Extract data from Next.js __NEXT_DATA__ script tag.
    Sites like maxhealthcare.in, many modern hospital sites use Next.js
    which embeds all page props as JSON in a script tag.
    """
    script = soup.find('script', id='__NEXT_DATA__')
    if not script or not script.string:
        return ''

    try:
        data = json.loads(script.string)
        props = data.get('props', {}).get('pageProps', {})
        if not props:
            return ''

        parts = []

        # Recursively extract text values from nested dicts/lists
        def extract_strings(obj, prefix='', depth=0):
            if depth > 6:
                return
            if isinstance(obj, str):
                cleaned = obj.strip()
                # Skip very short strings, URLs, IDs, HTML tags
                if (len(cleaned) > 20 and
                    not cleaned.startswith('http') and
                    not cleaned.startswith('/') and
                    not cleaned.startswith('<') and
                    not cleaned.startswith('{') and
                    'image' not in prefix.lower() and
                    'url' not in prefix.lower() and
                    'slug' not in prefix.lower() and
                    'id' != prefix.lower() and
                    '_id' not in prefix.lower()):
                    parts.append(cleaned)
                elif 5 < len(cleaned) <= 20 and prefix.lower() in (
                    'name', 'title', 'designation', 'qualification',
                    'degree', 'specialty', 'city', 'hospital', 'department',
                    'experience', 'language', 'jobtitle', 'position'
                ):
                    parts.append(f"{prefix}: {cleaned}")
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    extract_strings(v, k, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:50]:  # Cap at 50 items
                    extract_strings(item, prefix, depth + 1)

        # Look for doctor-specific keys first
        doctor_keys = ['doctor', 'doctorDetail', 'doctorData', 'profileData',
                       'doctorProfile', 'data', 'pageData', 'detail',
                       'doctorInfo', 'profile']
        target_data = None
        for key in doctor_keys:
            if key in props and props[key]:
                target_data = props[key]
                break

        if target_data:
            extract_strings(target_data)
        else:
            # Fallback: extract from all props
            extract_strings(props)

        # Deduplicate while preserving order
        seen = set()
        unique_parts = []
        for p in parts:
            normalized = p.lower().strip()
            if normalized not in seen and len(normalized) > 3:
                seen.add(normalized)
                unique_parts.append(p)

        return '\n'.join(unique_parts[:100])  # Cap at 100 entries

    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f"[Next.js Parse Error] {e}")
        return ''


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
