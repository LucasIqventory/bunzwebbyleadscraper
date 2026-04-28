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
from config import (
    ENABLE_NO_WEBSITE_PLACES,
    GOOGLE_PLACES_API_KEY,
    GOOGLE_SEARCH_API_KEY,
    GOOGLE_SEARCH_CX,
    MIN_GOOGLE_RATING,
    MIN_GOOGLE_REVIEW_COUNT,
    PLACES_RESULTS_PER_QUERY,
    TARGET_INDUSTRIES,
    TARGET_LOCATIONS,
)


GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
GOOGLE_PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

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


def google_places_text_search(query: str, max_results: int = PLACES_RESULTS_PER_QUERY) -> list[dict]:
    """Search Google Places for local businesses matching a query."""
    if not GOOGLE_PLACES_API_KEY:
        return []

    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "query": query,
    }

    try:
        resp = requests.get(GOOGLE_PLACES_TEXT_SEARCH_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status not in {"OK", "ZERO_RESULTS"}:
            print(f"    [!] Google Places search returned {status}: {data.get('error_message', '')}")
            return []
        return data.get("results", [])[:max_results]
    except Exception as e:
        print(f"    [!] Google Places search error: {e}")
        return []


def google_place_details(place_id: str) -> dict:
    """Fetch details needed to verify whether a Google Places result has a website."""
    if not GOOGLE_PLACES_API_KEY or not place_id:
        return {}

    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "place_id": place_id,
        "fields": ",".join([
            "business_status",
            "formatted_address",
            "formatted_phone_number",
            "international_phone_number",
            "name",
            "place_id",
            "rating",
            "url",
            "user_ratings_total",
            "website",
        ]),
    }

    try:
        resp = requests.get(GOOGLE_PLACES_DETAILS_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status != "OK":
            print(f"    [!] Google Places details returned {status}: {data.get('error_message', '')}")
            return {}
        return data.get("result", {})
    except Exception as e:
        print(f"    [!] Google Places details error: {e}")
        return {}


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


def discover_no_website_places(industry: str, location: str) -> list[dict]:
    """Find well-reviewed businesses on Google Maps that do not list a website."""
    search_query = f"{industry} in {location}"
    raw_results = google_places_text_search(search_query)
    companies = []

    for place in raw_results:
        if place.get("business_status") and place.get("business_status") != "OPERATIONAL":
            continue

        rating = float(place.get("rating") or 0)
        review_count = int(place.get("user_ratings_total") or 0)
        if rating < MIN_GOOGLE_RATING or review_count < MIN_GOOGLE_REVIEW_COUNT:
            continue

        details = google_place_details(place.get("place_id", ""))
        time.sleep(0.2)
        if not details:
            continue

        website = (details.get("website") or "").strip()
        if website:
            continue

        name = (details.get("name") or place.get("name") or "").strip()
        address = details.get("formatted_address") or place.get("formatted_address") or ""
        phone = details.get("formatted_phone_number") or details.get("international_phone_number") or ""
        google_maps_url = details.get("url") or f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id', '')}"
        place_id = details.get("place_id") or place.get("place_id", "")

        if not name:
            continue

        companies.append({
            "name": name,
            "website": "",
            "domain": "",
            "place_id": place_id,
            "rating": rating,
            "review_count": review_count,
            "google_maps_url": google_maps_url,
            "address": address,
            "phone": phone,
            "industry_query": industry,
            "location": location,
            "source": "google_places_no_website",
            "qualification_reason": f"{rating:.1f} rating, {review_count} reviews, no website listed",
        })

    return companies


def scrape_leads(
    industries: list[str] | None = None,
    include_places: bool = ENABLE_NO_WEBSITE_PLACES,
    locations: list[str] | None = None,
    include_organic: bool = True,
) -> list[dict]:
    """
    Fully automated. Searches every target industry and collects unique
    company leads. No manual filtering needed — the industry list itself
    guarantees these are big-money sectors.
    """
    if industries is None:
        industries = TARGET_INDUSTRIES
    if locations is None:
        locations = TARGET_LOCATIONS

    seen_domains = set()
    seen_places = set()
    all_leads = []

    places_enabled = include_places and bool(GOOGLE_PLACES_API_KEY) and bool(locations)
    if include_places and not GOOGLE_PLACES_API_KEY:
        print("\n[!] Google Places discovery skipped: set GOOGLE_PLACES_API_KEY to find rated businesses with no website.")

    for i, industry in enumerate(industries):
        if include_organic:
            print(f"\n[{i+1}/{len(industries)}] Searching websites: '{industry}'...")
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
                    "source": "google_search",
                    "rating": "",
                    "review_count": "",
                    "google_maps_url": "",
                    "qualification_reason": "Website found via Google Search",
                }
                all_leads.append(lead)
                new_count += 1
                print(f"    + {co['name'][:60]} | {co['website']}")

            print(f"    -> {new_count} new website leads")

        if places_enabled:
            for location in locations:
                print(f"\n[{i+1}/{len(industries)}] Searching rated no-website businesses: '{industry}' in {location}...")
                places = discover_no_website_places(industry, location)
                new_places_count = 0

                for co in places:
                    place_key = co.get("place_id") or f"{co['name'].lower()}|{co.get('address', '').lower()}"
                    if place_key in seen_places:
                        continue
                    seen_places.add(place_key)

                    lead = {
                        "name": co["name"],
                        "website": "",
                        "domain": "",
                        "has_website": False,
                        "industry": industry,
                        "search_snippet": "",
                        "phone": co.get("phone", ""),
                        "address": co.get("address", ""),
                        "place_id": co.get("place_id", ""),
                        "rating": co.get("rating", ""),
                        "review_count": co.get("review_count", ""),
                        "google_maps_url": co.get("google_maps_url", ""),
                        "source": co.get("source", "google_places_no_website"),
                        "qualification_reason": co.get("qualification_reason", "No website listed on Google Places"),
                    }
                    all_leads.append(lead)
                    new_places_count += 1
                    print(f"    + {co['name'][:60]} | {co['rating']:.1f} stars | {co['review_count']} reviews | no website")

                print(f"    -> {new_places_count} new no-website leads")

        time.sleep(1)

    print(f"\n[*] Total unique leads: {len(all_leads)}")
    return all_leads
