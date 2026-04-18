"""
Lead Scraper — Finds massive companies by industry.
Searches Google for companies in high-revenue sectors (mining, oil & gas,
steel, heavy construction, manufacturing, etc.) and collects their websites.
Fully automated — just run it.
"""

import re
import time
import requests
from urllib.parse import urlparse, quote_plus
from config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CX, TARGET_INDUSTRIES


GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

# Skip these domains — they're directories/social, not actual company sites
BLACKLISTED_DOMAINS = [
    "wikipedia.org", "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "yelp.com", "glassdoor.com", "indeed.com",
    "linkedin.com", "bbb.org", "manta.com", "dnb.com", "zoominfo.com",
    "bloomberg.com", "thomasnet.com", "google.com", "mapquest.com",
    "yellowpages.com", "whitepages.com", "angi.com", "homeadvisor.com",
    "pinterest.com", "tiktok.com", "reddit.com", "crunchbase.com",
    "sec.gov", "opencorporates.com", "buzzfile.com", "owler.com",
    "hoovers.com", "comparably.com", "guidestar.org", "macroaxis.com",
    "globaldata.com", "ibisworld.com", "marketwatch.com", "wsj.com",
    "reuters.com", "nytimes.com", "forbes.com", "inc.com",
]


def _is_company_website(url: str) -> bool:
    """Check if a URL looks like an actual company website (not a directory)."""
    if not url:
        return False
    domain = urlparse(url).netloc.lower().replace("www.", "")
    return not any(bl in domain for bl in BLACKLISTED_DOMAINS)


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.netloc or "").lower().replace("www.", "")


def _clean_company_name(title: str) -> str:
    """Extract a clean company name from a search result title."""
    # Remove everything after common separators
    name = re.sub(r'\s*[-|–—:].+$', '', title).strip()
    # Remove trailing junk like "... - Home" or "Official Site"
    name = re.sub(r'\s*(Home|Official Site|Homepage|Welcome)\s*$', '', name, flags=re.IGNORECASE).strip()
    return name or title.strip()


def google_search(query: str, num_results: int = 10, start: int = 1) -> list[dict]:
    """Search via Google Custom Search API."""
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX:
        return []

    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "q": query,
        "num": min(num_results, 10),
        "start": start,
    }

    try:
        resp = requests.get(GOOGLE_CSE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
    except Exception as e:
        print(f"    [!] Google Search error: {e}")
        return []


def scrape_google_organic(query: str, num_pages: int = 2) -> list[dict]:
    """Fallback: scrape Google directly (no API key needed)."""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for page in range(num_pages):
        start = page * 10
        url = f"https://www.google.com/search?q={quote_plus(query)}&start={start}&num=10"

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"    [!] Google returned {resp.status_code} (may be rate-limited)")
                break

            html = resp.text
            url_pattern = re.findall(r'/url\?q=(https?://[^&"]+)', html)
            title_pattern = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)

            for i, found_url in enumerate(url_pattern):
                title = title_pattern[i] if i < len(title_pattern) else ""
                title = re.sub(r'<[^>]+>', '', title).strip()
                results.append({"title": title, "link": found_url, "snippet": ""})

        except Exception as e:
            print(f"    [!] Scrape error: {e}")
            break

        time.sleep(2)

    return results


def discover_companies(query: str) -> list[dict]:
    """Find companies for a single industry query. Returns company dicts."""
    raw_results = []
    search_query = f'{query} -site:wikipedia.org -site:youtube.com -site:linkedin.com'

    if GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX:
        page1 = google_search(search_query, num_results=10, start=1)
        raw_results.extend(page1)
        if len(page1) >= 10:
            time.sleep(0.5)
            page2 = google_search(search_query, num_results=10, start=11)
            raw_results.extend(page2)
    else:
        raw_results = scrape_google_organic(search_query, num_pages=2)

    seen_domains = set()
    companies = []

    for item in raw_results:
        link = item.get("link", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")

        if not link:
            continue

        domain = _extract_domain(link)
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)

        if not _is_company_website(link):
            continue

        companies.append({
            "name": _clean_company_name(title),
            "website": f"https://{domain}",
            "domain": domain,
            "search_snippet": snippet,
            "industry_query": query,
        })

    return companies


def scrape_leads(industries: list[str] | None = None) -> list[dict]:
    """
    Fully automated. Searches every target industry and collects unique
    company leads. No manual filtering needed — the industry list itself
    guarantees these are big-money sectors.
    """
    if industries is None:
        industries = TARGET_INDUSTRIES

    seen_domains = set()
    all_leads = []

    for i, industry in enumerate(industries):
        print(f"\n[{i+1}/{len(industries)}] Searching: '{industry}'...")
        companies = discover_companies(industry)
        new_count = 0

        for co in companies:
            domain = co["domain"]
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            lead = {
                "name": co["name"],
                "website": co["website"],
                "domain": domain,
                "has_website": True,
                "industry": industry,
                "search_snippet": co["search_snippet"],
                "phone": "",
                "address": "",
            }
            all_leads.append(lead)
            new_count += 1
            print(f"    + {co['name'][:60]} | {co['website']}")

        print(f"    → {new_count} new leads")
        time.sleep(1)

    print(f"\n[*] Total unique leads: {len(all_leads)}")
    return all_leads
