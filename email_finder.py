"""
Email Finder — Attempts to find owner/decision-maker emails for a company.
Uses multiple strategies:
  1. Hunter.io API (if key provided)
    2. Scraping contact pages for mailto: links
    3. Public web search for no-website leads
    4. Optional common email pattern guessing from domain
"""

import re
import requests
from urllib.parse import urlparse
from config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CX, HUNTER_API_KEY, USE_GUESSED_EMAILS


GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)
JUNK_EMAIL_PATTERNS = [
    "example.com", "sentry.io", "wixpress.com", "wordpress.com",
    "placeholder", "email.com", "domain.com", "yoursite.com",
    ".png", ".jpg", ".gif", ".js", ".css", "noreply@",
]


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    if not url:
        return ""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().replace("www.", "")
    return domain


def clean_emails(emails: list[str]) -> list[str]:
    """Normalize and remove obvious junk addresses while preserving order."""
    cleaned = []
    seen = set()
    for email in emails:
        email_lower = email.lower().strip().strip(".,;:()[]{}<>")
        if any(junk in email_lower for junk in JUNK_EMAIL_PATTERNS):
            continue
        if email_lower in seen:
            continue
        seen.add(email_lower)
        cleaned.append(email_lower)
    return cleaned


def extract_emails_from_text(text: str) -> list[str]:
    return clean_emails(EMAIL_PATTERN.findall(text or ""))


def hunter_domain_search(domain: str) -> list[dict]:
    """Use Hunter.io to find emails associated with a domain."""
    if not HUNTER_API_KEY or not domain:
        return []

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 10,
        "type": "personal",  # personal emails, not generic
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        emails = data.get("data", {}).get("emails", [])

        results = []
        for e in emails:
            results.append({
                "email": e.get("value", ""),
                "first_name": e.get("first_name", ""),
                "last_name": e.get("last_name", ""),
                "position": e.get("position", ""),
                "confidence": e.get("confidence", 0),
                "source": "hunter.io",
            })

        # Sort by seniority — prioritize owners, presidents, CEOs
        owner_keywords = ["owner", "president", "ceo", "founder", "director", "principal", "partner"]
        results.sort(key=lambda x: (
            -1 if any(kw in (x.get("position") or "").lower() for kw in owner_keywords) else 0,
            -x.get("confidence", 0),
        ))

        return results
    except Exception:
        return []


def hunter_email_verify(email: str) -> str:
    """Verify an email via Hunter.io. Returns 'valid', 'invalid', or 'unknown'."""
    if not HUNTER_API_KEY or not email:
        return "unknown"

    url = "https://api.hunter.io/v2/email-verifier"
    params = {"email": email, "api_key": HUNTER_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return "unknown"
        data = resp.json()
        return data.get("data", {}).get("status", "unknown")
    except Exception:
        return "unknown"


def scrape_contact_emails(website_url: str) -> list[str]:
    """Scrape the company website for email addresses on contact/about pages."""
    if not website_url:
        return []

    emails_found = set()
    pages_to_check = [
        website_url,
        website_url.rstrip("/") + "/contact",
        website_url.rstrip("/") + "/contact-us",
        website_url.rstrip("/") + "/about",
        website_url.rstrip("/") + "/about-us",
    ]

    for page_url in pages_to_check:
        try:
            resp = requests.get(page_url, timeout=10, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code != 200:
                continue

            for email in extract_emails_from_text(resp.text):
                emails_found.add(email)
        except Exception:
            continue

    return list(emails_found)


def search_public_web_for_emails(company_name: str, address: str = "") -> list[str]:
    """Search public web results for contact emails when the company has no website."""
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX or not company_name:
        return []

    query = f'"{company_name}" email OR contact'
    if address:
        query = f'{query} "{address.split(",")[0]}"'

    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "q": query,
        "num": 5,
    }

    emails_found = []
    try:
        resp = requests.get(GOOGLE_CSE_URL, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"    [!] Public email search error: {e}")
        return []

    for item in items:
        searchable_text = " ".join([
            item.get("title", ""),
            item.get("snippet", ""),
            item.get("htmlSnippet", ""),
        ])
        emails_found.extend(extract_emails_from_text(searchable_text))

        link = item.get("link", "")
        if not link:
            continue

        try:
            page_resp = requests.get(link, timeout=10, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if page_resp.status_code == 200:
                emails_found.extend(extract_emails_from_text(page_resp.text))
        except Exception:
            continue

        if len(emails_found) >= 5:
            break

    return clean_emails(emails_found)[:5]


def guess_owner_emails(domain: str, company_name: str) -> list[str]:
    """Generate common owner email patterns."""
    if not domain:
        return []

    # Common patterns for small/medium business owner emails
    patterns = [
        f"info@{domain}",
        f"contact@{domain}",
        f"owner@{domain}",
        f"admin@{domain}",
        f"sales@{domain}",
    ]
    return patterns


def find_emails(company_name: str, website_url: str, address: str = "") -> dict:
    """
    Main email-finding function. Tries all strategies and returns best results.
    """
    domain = extract_domain(website_url)

    result = {
        "domain": domain,
        "owner_emails": [],       # Personal emails (best)
        "contact_emails": [],     # From website scraping
        "public_emails": [],      # From public search results for no-website leads
        "guessed_emails": [],     # Pattern-based guesses
        "best_email": None,
        "best_name": None,
    }

    # Strategy 1: Hunter.io
    if HUNTER_API_KEY and domain:
        print(f"    Searching Hunter.io for {domain}...")
        hunter_results = hunter_domain_search(domain)
        for h in hunter_results:
            result["owner_emails"].append(h)

    # Strategy 2: Scrape website
    if website_url:
        print(f"    Scraping contact pages for {domain}...")
        scraped = scrape_contact_emails(website_url)
        result["contact_emails"] = scraped
    else:
        print("    Searching public web results for contact emails...")
        result["public_emails"] = search_public_web_for_emails(company_name, address)

    # Strategy 3: Pattern guessing
    if domain:
        result["guessed_emails"] = guess_owner_emails(domain, company_name)

    # Pick the best email
    if result["owner_emails"]:
        best = result["owner_emails"][0]
        result["best_email"] = best["email"]
        fname = best.get("first_name", "")
        lname = best.get("last_name", "")
        if fname or lname:
            result["best_name"] = f"{fname} {lname}".strip()
    elif result["contact_emails"]:
        # Prefer non-generic emails
        generic = {"info@", "contact@", "admin@", "support@", "sales@", "hello@"}
        personal = [e for e in result["contact_emails"] if not any(e.startswith(g) for g in generic)]
        if personal:
            result["best_email"] = personal[0]
        else:
            result["best_email"] = result["contact_emails"][0]
    elif result["public_emails"]:
        result["best_email"] = result["public_emails"][0]
    elif USE_GUESSED_EMAILS and result["guessed_emails"]:
        result["best_email"] = result["guessed_emails"][0]

    return result
