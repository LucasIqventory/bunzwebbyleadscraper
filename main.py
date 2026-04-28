"""
Bunz Webby Lead Scraper — Fully Automated Pipeline

Finds massive companies in high-revenue industries with bad/no websites,
then previews outreach by default. Use --send to send at a human-paced rate.

Just run it:
    python main.py              # Discover, analyze, find emails, preview outreach
    python main.py --send       # Actually send, capped at 10/day by default
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime

from config import (
    EMAIL_DELAY_MAX_SECONDS,
    EMAIL_DELAY_MIN_SECONDS,
    ENABLE_NO_WEBSITE_PLACES,
    MAX_EMAILS_PER_DAY,
    OUTPUT_DIR,
    TARGET_LOCATIONS,
)
from scraper import scrape_leads
from website_analyzer import analyze_website
from email_finder import find_emails
from emailer import send_outreach, log_results


def save_leads_csv(leads: list[dict], filename: str = "leads.csv"):
    """Save all lead data to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    if not leads:
        print("[!] No leads to save.")
        return

    fieldnames = [
        "name", "domain", "industry",
        "website", "has_website",
        "website_score", "website_grade", "website_is_bad", "website_reachable", "website_issues",
        "rating", "review_count", "lead_priority_score",
        "best_email", "best_name", "contact_emails", "public_emails",
        "phone", "address", "place_id", "google_maps_url", "source", "qualification_reason", "search_snippet",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\n[*] Leads saved to {filepath}")


def save_leads_json(leads: list[dict], filename: str = "leads.json"):
    """Save full lead data to JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, default=str)

    print(f"[*] Full data saved to {filepath}")


def compute_lead_priority(lead: dict) -> int:
    """Prioritize no-website and higher-reputation leads before sending."""
    priority = 0

    if not lead.get("has_website", True):
        priority += 100

    if lead.get("website_is_bad"):
        priority += max(0, 100 - int(lead.get("website_score") or 0))

    try:
        priority += int(float(lead.get("rating") or 0) * 10)
    except (TypeError, ValueError):
        pass

    try:
        priority += min(int(lead.get("review_count") or 0), 500) // 10
    except (TypeError, ValueError):
        pass

    return priority


def run_pipeline(
    dry_run: bool = True,
    skip_pagespeed: bool = False,
    delay_seconds: int | None = None,
    max_emails_per_day: int = MAX_EMAILS_PER_DAY,
    min_delay_seconds: int = EMAIL_DELAY_MIN_SECONDS,
    max_delay_seconds: int = EMAIL_DELAY_MAX_SECONDS,
    include_places: bool = ENABLE_NO_WEBSITE_PLACES,
    locations: list[str] | None = None,
    industries: list[str] | None = None,
    places_only: bool = False,
):
    """
    Fully automated pipeline. No arguments needed.
    Discovers → Analyzes → Finds emails → Sends.
    """

    mode = "DRY RUN (no emails sent)" if dry_run else "LIVE — EMAILS WILL BE SENT"

    print("=" * 60)
    print(f"  BUNZ WEBBY LEAD SCRAPER")
    print(f"  Mode: {mode}")
    print("=" * 60)

    # ── Step 1: Discover companies ──
    print("\n" + "─" * 40)
    print("STEP 1: Discovering companies across all industries...")
    print("─" * 40)
    leads = scrape_leads(
        industries=industries,
        include_places=include_places,
        locations=locations,
        include_organic=not places_only,
    )

    if not leads:
        print("[!] No leads found. Check your API key or internet connection.")
        return

    # ── Step 2: Analyze websites ──
    print("\n" + "─" * 40)
    print(f"STEP 2: Analyzing {len(leads)} websites...")
    print("─" * 40)

    for lead in leads:
        print(f"\n  [{lead['name']}]")
        analysis = analyze_website(lead["website"], use_pagespeed=not skip_pagespeed)
        lead["website_score"] = analysis["score"]
        lead["website_grade"] = analysis["grade"]
        lead["website_is_bad"] = analysis["is_bad"]
        lead["website_issues"] = analysis.get("issues", [])
        lead["website_reachable"] = analysis["reachable"]

        status = "BAD" if analysis["is_bad"] else "OK"
        print(f"    Score: {analysis['score']}/100 (Grade: {analysis['grade']}) — {status}")
        if analysis["issues"]:
            for issue in analysis["issues"][:3]:
                print(f"      - {issue}")

        time.sleep(0.5)

    # ── Step 3: Find emails ──
    print("\n" + "─" * 40)
    print("STEP 3: Finding owner/contact emails...")
    print("─" * 40)

    for lead in leads:
        print(f"\n  [{lead['name']}]")
        email_data = find_emails(lead["name"], lead.get("website", ""), lead.get("address", ""))
        lead["best_email"] = email_data["best_email"]
        lead["best_name"] = email_data.get("best_name")
        lead["contact_emails"] = ", ".join(email_data.get("contact_emails", []))
        lead["public_emails"] = ", ".join(email_data.get("public_emails", []))
        lead["owner_emails"] = email_data.get("owner_emails", [])

        if email_data["best_email"]:
            name_part = f" ({email_data['best_name']})" if email_data.get("best_name") else ""
            print(f"    Email: {email_data['best_email']}{name_part}")
        else:
            print(f"    No email found")

        time.sleep(0.3)

    # ── Step 4: Filter leads worth emailing ──
    for lead in leads:
        lead["lead_priority_score"] = compute_lead_priority(lead)

    hot_leads = sorted([
        l for l in leads
        if l.get("best_email") and l.get("website_is_bad")
    ], key=compute_lead_priority, reverse=True)

    no_website_reputation_leads = [
        l for l in leads
        if not l.get("has_website", True) and l.get("rating") and l.get("review_count")
    ]

    print("\n" + "─" * 40)
    print(f"RESULTS")
    print("─" * 40)
    print(f"  Total companies found:  {len(leads)}")
    print(f"  Bad website (< 50):     {sum(1 for l in leads if l.get('website_is_bad'))}")
    print(f"  Rated/no website:       {len(no_website_reputation_leads)}")
    print(f"  Good website:           {sum(1 for l in leads if not l.get('website_is_bad'))}")
    print(f"  Emails found:           {sum(1 for l in leads if l.get('best_email'))}")
    print(f"  QUALIFIED LEADS:        {len(hot_leads)}")

    # ── Step 5: Save data ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_leads_csv(leads, f"leads_{timestamp}.csv")
    save_leads_json(leads, f"leads_{timestamp}.json")

    # ── Step 6: Send emails ──
    if hot_leads:
        sending = not dry_run
        print("\n" + "─" * 40)
        print(f"STEP 6: {'SENDING' if sending else 'Previewing'} emails to {len(hot_leads)} qualified leads...")
        if sending:
            delay_description = f"fixed {delay_seconds}s" if delay_seconds is not None else f"random {min_delay_seconds}-{max_delay_seconds}s"
            print(f"  Human pace: max {max_emails_per_day}/day, {delay_description} between sends")
        print("─" * 40)

        results = send_outreach(
            hot_leads,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
            max_per_day=max_emails_per_day,
            min_delay_seconds=min_delay_seconds,
            max_delay_seconds=max_delay_seconds,
        )
        log_results(results, f"email_log_{timestamp}.csv")

        status_to_count = "sent" if sending else "previewed"
        completed_count = sum(1 for r in results if r.get("status") == status_to_count)
        print(f"\n  Emails {status_to_count}: {completed_count}/{len(results)}")
    else:
        print("\n[!] No qualified leads to email this run.")

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Bunz Webby Lead Scraper — fully automated")
    parser.add_argument("--send", action="store_true", help="Actually send emails. Default is preview only.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only. Kept for explicitness; this is the default.")
    parser.add_argument("--skip-pagespeed", action="store_true", help="Skip PageSpeed analysis (faster)")
    parser.add_argument("--delay", type=int, default=None, help="Fixed seconds between live emails. Overrides min/max delay jitter.")
    parser.add_argument("--min-delay", type=int, default=EMAIL_DELAY_MIN_SECONDS, help="Minimum random seconds between live emails")
    parser.add_argument("--max-delay", type=int, default=EMAIL_DELAY_MAX_SECONDS, help="Maximum random seconds between live emails")
    parser.add_argument("--daily-limit", type=int, default=MAX_EMAILS_PER_DAY, help="Maximum live emails per day")
    parser.add_argument("--no-places", action="store_true", help="Skip Google Places no-website lead discovery")
    parser.add_argument("--places-only", action="store_true", help="Only search Google Places for rated businesses with no website")
    parser.add_argument("--location", action="append", dest="locations", help="Google Places location to search. Can be used multiple times.")
    parser.add_argument("--industry", action="append", dest="industries", help="Industry query to search. Can be used multiple times.")
    args = parser.parse_args()

    dry_run = not args.send or args.dry_run

    run_pipeline(
        dry_run=dry_run,
        skip_pagespeed=args.skip_pagespeed,
        delay_seconds=args.delay,
        max_emails_per_day=args.daily_limit,
        min_delay_seconds=args.min_delay,
        max_delay_seconds=args.max_delay,
        include_places=ENABLE_NO_WEBSITE_PLACES and not args.no_places,
        locations=args.locations or TARGET_LOCATIONS,
        industries=args.industries,
        places_only=args.places_only,
    )


if __name__ == "__main__":
    main()
