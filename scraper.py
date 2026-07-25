"""
University of Cumberlands Web Scraper
Crawls all pages from ucumberlands.edu and stores content hierarchically.
"""

import os
import re
import json
import time
import hashlib
import logging
from urllib.parse import urljoin, urlparse, urldefrag
from collections import deque
from datetime import datetime

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.ucumberlands.edu/"
DOMAIN = "www.ucumberlands.edu"
OUTPUT_DIR = "scraped_data"
DELAY_BETWEEN_REQUESTS = 0.1
MAX_PAGES = 5000
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

SKIP_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".tar", ".gz",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp4", ".mp3", ".avi", ".mov", ".wmv",
    ".css", ".js", ".xml", ".rss",
}

SKIP_PATTERNS = [
    r"/wp-admin/",
    r"/wp-content/uploads/",
    r"/feed/",
    r"\?replytocom=",
    r"#comment",
    r"/tag/",
    r"/page/\d+",
]


def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "UCumberlandsRAGBot/1.0 (Educational Research Project)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session


def is_valid_url(url):
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != DOMAIN:
        return False
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return False
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, url):
            return False
    return True


def normalize_url(url):
    url, _ = urldefrag(url)
    url = url.rstrip("/")
    if url == "https://www.ucumberlands.edu":
        url = "https://www.ucumberlands.edu/"
    return url


def url_to_filepath(url):
    """Convert URL to a hierarchical file path for storage."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    path = re.sub(r"[^\w/\-]", "_", path)
    parts = path.split("/")
    return os.path.join(OUTPUT_DIR, "pages", *parts) + ".json"


def extract_content(soup, url):
    """Extract structured content from a page."""
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_description = meta_tag.get("content", "")

    breadcrumbs = []
    breadcrumb_el = soup.find(class_=re.compile(r"breadcrumb", re.I))
    if breadcrumb_el:
        breadcrumbs = [a.get_text(strip=True) for a in breadcrumb_el.find_all("a")]

    headings = []
    seen_headings = set()
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            key = (level, text)
            if text and key not in seen_headings:
                seen_headings.add(key)
                headings.append({"level": level, "text": text})

    main_content = soup.find("main") or soup.find(id="content") or soup.find(class_="content") or soup.find("article")
    if not main_content:
        main_content = soup.find("body")

    paragraphs = []
    if main_content:
        seen_texts = set()
        for p in main_content.find_all(["p", "li", "td", "h1", "h2", "h3", "h4", "h5", "h6"], recursive=True):
            if p.find(["p", "li", "td", "h1", "h2", "h3", "h4", "h5", "h6"]):
                continue
            text = p.get_text(separator=" ", strip=True)
            if text and len(text) > 20 and text not in seen_texts:
                seen_texts.add(text)
                paragraphs.append(text)

    full_text = ""
    if main_content:
        full_text = main_content.get_text(separator="\n", strip=True)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    links = []
    if main_content:
        for a in main_content.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            if link_text:
                links.append({"text": link_text, "href": a["href"]})

    tables = []
    if main_content:
        for table in main_content.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)

    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    category = path_parts[0] if path_parts else "home"

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "category": category,
        "breadcrumbs": breadcrumbs,
        "headings": headings,
        "paragraphs": paragraphs,
        "full_text": full_text,
        "links": links,
        "tables": tables,
        "path_hierarchy": path_parts,
        "scraped_at": datetime.now().isoformat(),
    }


def fetch_page(session, url):
    """Fetch a page with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, verify=False)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    return response.text
            elif response.status_code == 429:
                wait = 2 ** (attempt + 2)
                logger.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
            else:
                logger.debug(f"HTTP {response.status_code} for {url}")
                return None
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    return None


def extract_links(soup, current_url):
    """Extract all valid internal links from a page."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(current_url, href)
        full_url = normalize_url(full_url)
        if is_valid_url(full_url):
            links.add(full_url)
    return links


def save_page_data(data):
    """Save extracted page data to a JSON file in hierarchical structure."""
    filepath = url_to_filepath(data["url"])
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def fetch_sitemap_urls(session):
    """Fetch all URLs from the sitemap."""
    logger.info("Fetching sitemap...")
    response = session.get(f"{BASE_URL}sitemap.xml", timeout=REQUEST_TIMEOUT, verify=False)
    if response.status_code != 200:
        logger.error(f"Failed to fetch sitemap: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "lxml-xml")
    urls = [loc.text.strip() for loc in soup.find_all("loc")]

    # Filter to valid URLs only
    valid = [u for u in urls if is_valid_url(u)]
    logger.info(f"Sitemap: {len(urls)} total, {len(valid)} valid after filtering")
    return valid


def crawl():
    """Main crawl using sitemap for complete coverage."""
    logger.info(f"Starting sitemap-based crawl of {BASE_URL}")
    logger.info(f"Delay: {DELAY_BETWEEN_REQUESTS}s per page")

    os.makedirs(os.path.join(OUTPUT_DIR, "pages"), exist_ok=True)

    session = get_session()
    urls = fetch_sitemap_urls(session)

    if not urls:
        logger.error("No URLs found. Exiting.")
        return

    scraped_count = 0
    failed_count = 0
    category_counts = {}

    progress = tqdm(total=len(urls), desc="Scraping pages", unit="page")

    for url in urls:
        html = fetch_page(session, url)
        if not html:
            failed_count += 1
            progress.update(1)
            continue

        soup = BeautifulSoup(html, "lxml")
        data = extract_content(soup, url)

        if not data["full_text"].strip():
            failed_count += 1
            progress.update(1)
            continue

        save_page_data(data)
        scraped_count += 1

        cat = data["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        progress.update(1)
        progress.set_postfix({"scraped": scraped_count, "failed": failed_count})

        time.sleep(DELAY_BETWEEN_REQUESTS)

    progress.close()

    summary = {
        "base_url": BASE_URL,
        "total_pages_scraped": scraped_count,
        "total_urls_in_sitemap": len(urls),
        "failed": failed_count,
        "categories": category_counts,
        "completed_at": datetime.now().isoformat(),
    }

    summary_path = os.path.join(OUTPUT_DIR, "scrape_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Crawl complete: {scraped_count} pages scraped, {failed_count} failed")
    logger.info(f"Categories: {json.dumps(category_counts, indent=2)}")

    return summary


if __name__ == "__main__":
    crawl()
