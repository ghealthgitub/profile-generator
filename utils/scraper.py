"""
🫚 Ginger Universe v3 — Web Scraper
Scrapes doctor info from multiple URLs, merges data intelligently
"""

import requests
from bs4 import BeautifulSoup
import re


def scrape_multiple_urls(urls):
    """
    Scrapes multiple URLs and merges all extracted text.
    Returns a single combined data dict for Claude to analyze.
    """
    all_text = []
    all_titles = []
    successful_urls = []

    for url in urls:
        url = url.strip()
        if not url:
            continue
        data = scrape_single_url(url)
        if data:
            all_text.append(data['text'])
            all_titles.append(data.get('title', ''))
            successful_urls.append(url)

    if not all_text:
        return None

    combined_text = '\n\n---SOURCE BREAK---\n\n'.join(all_text)

    return {
        'urls': successful_urls,
        'url_count': len(successful_urls),
        'combined_text': combined_text[:12000],  # Generous limit for Claude
        'titles': [t for t in all_titles if t],
    }


def scrape_single_url(url):
    """Scrapes a single URL and returns cleaned text content"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove noise elements
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe',
                                   'noscript', 'svg', 'button', 'form']):
            tag.decompose()

        # Try to find main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=re.compile(r'content|main|doctor|profile|detail', re.I)) or
            soup.find('div', id=re.compile(r'content|main|doctor|profile|detail', re.I)) or
            soup.body or soup
        )

        # Get page title
        title = ''
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Also grab h1
        h1 = soup.find('h1')
        h1_text = h1.get_text(strip=True) if h1 else ''

        # Extract structured text with basic formatting preserved
        text_parts = []
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'td', 'span', 'div']):
            text = element.get_text(separator=' ', strip=True)
            if text and len(text) > 2:
                if element.name in ('h1', 'h2', 'h3', 'h4'):
                    text_parts.append(f"\n## {text}")
                elif element.name == 'li':
                    text_parts.append(f"• {text}")
                else:
                    text_parts.append(text)

        # Deduplicate while preserving order
        seen = set()
        unique_parts = []
        for part in text_parts:
            clean = part.strip()
            if clean and clean not in seen and len(clean) > 5:
                seen.add(clean)
                unique_parts.append(clean)

        clean_text = '\n'.join(unique_parts)

        # If structured extraction is too short, fall back to full text
        if len(clean_text) < 200:
            clean_text = main_content.get_text(separator='\n', strip=True)

        return {
            'url': url,
            'title': h1_text or title,
            'text': clean_text[:6000]
        }

    except Exception as e:
        print(f"[Scrape Error] {url}: {e}")
        return None
