"""
Scheduled outreach worker.

This script is designed to be launched by Windows Task Scheduler, do one small
piece of work, then exit. It does not run as a forever loop.
"""

import argparse
import csv
import json
import math
import os
from datetime import datetime, time

from config import (
    BUSINESS_DAYS,
    BUSINESS_HOURS_END,
    BUSINESS_HOURS_START,
    OUTPUT_DIR,
    REPORT_RECIPIENTS,
    SCHEDULED_ACTIVITY_FILE,
    SCHEDULED_AUTO_REFILL_QUEUE,
    SCHEDULED_DAILY_EMAIL_LIMIT,
    SCHEDULED_INTRA_RUN_DELAY_SECONDS,
    SCHEDULED_MAX_EMAILS_PER_RUN,
    SCHEDULED_OUTREACH_ENABLED,
    SCHEDULED_QUEUE_FILE,
    SCHEDULED_REFILL_LIMIT,
    SCHEDULED_REFILL_MIN_QUEUE,
    SCHEDULED_REPORT_HISTORY_FILE,
    SCHEDULED_TARGET_INDUSTRIES,
    SCHEDULED_TASK_INTERVAL_MINUTES,
    TARGET_LOCATIONS,
)
from email_finder import find_emails
from emailer import load_send_history, send_email, send_outreach, sent_today_count
from scraper import discover_companies, discover_no_website_places
from website_analyzer import analyze_website


ACTIVITY_FIELDNAMES = [
    "date",
    "timestamp",
    "company",
    "email",
    "contact_name",
    "email_type",
    "subject",
    "sent",
    "status",
    "reason",
    "industry",
    "source",
    "website",
    "website_score",
    "website_grade",
    "website_issues",
    "rating",
    "review_count",
    "phone",
    "address",
    "qualification_reason",
]

REPORT_FIELDNAMES = ["date", "timestamp", "recipient", "sent", "reason", "sent_count", "failed_count", "skipped_count"]

WEEKDAY_TOKENS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def output_path(filename: str) -> str:
    ensure_output_dir()
    return os.path.join(OUTPUT_DIR, filename)


def today_string(now: datetime | None = None) -> str:
    return (now or datetime.now()).date().isoformat()


def parse_clock(value: str) -> time:
    return datetime.strptime(value.strip(), "%H:%M").time()


def normalized_business_days() -> set[str]:
    return {day.strip().upper()[:3] for day in BUSINESS_DAYS if day.strip()}


def is_business_day(now: datetime) -> bool:
    return WEEKDAY_TOKENS[now.weekday()] in normalized_business_days()


def in_business_hours(now: datetime) -> bool:
    start = parse_clock(BUSINESS_HOURS_START)
    end = parse_clock(BUSINESS_HOURS_END)
    return start <= now.time() < end


def after_business_hours(now: datetime) -> bool:
    return now.time() >= parse_clock(BUSINESS_HOURS_END)


def runs_left_today(now: datetime) -> int:
    end = parse_clock(BUSINESS_HOURS_END)
    end_dt = datetime.combine(now.date(), end)
    minutes_left = max(0, int((end_dt - now).total_seconds() // 60))
    return max(1, math.ceil(minutes_left / max(1, SCHEDULED_TASK_INTERVAL_MINUTES)))


def load_queue() -> list[dict]:
    filepath = output_path(SCHEDULED_QUEUE_FILE)
    if not os.path.exists(filepath):
        return []
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_queue(queue: list[dict]) -> None:
    filepath = output_path(SCHEDULED_QUEUE_FILE)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, default=str)


def lead_key(lead: dict) -> str:
    email = (lead.get("best_email") or lead.get("email") or "").strip().lower()
    place_id = (lead.get("place_id") or "").strip().lower()
    domain = (lead.get("domain") or "").strip().lower()
    name = (lead.get("name") or "").strip().lower()
    address = (lead.get("address") or "").strip().lower()
    return email or place_id or domain or f"{name}|{address}"


def pending_queue(queue: list[dict]) -> list[dict]:
    return [lead for lead in queue if lead.get("status", "queued") == "queued" and lead.get("best_email")]


def compute_lead_priority(lead: dict) -> int:
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


def queued_keys(queue: list[dict]) -> set[str]:
    return {lead_key(lead) for lead in queue if lead_key(lead)}


def build_queue_item(lead: dict) -> dict:
    lead["status"] = "queued"
    lead["queued_at"] = datetime.now().isoformat()
    lead["lead_priority_score"] = compute_lead_priority(lead)
    return lead


def prepare_website_lead(company: dict) -> dict | None:
    lead = {
        "name": company.get("name", ""),
        "website": company.get("website", ""),
        "domain": company.get("domain", ""),
        "has_website": True,
        "industry": company.get("industry_query", ""),
        "source": "google_search",
        "search_snippet": company.get("search_snippet", ""),
        "phone": "",
        "address": "",
        "qualification_reason": "Website found via Google Search",
    }

    analysis = analyze_website(lead["website"], use_pagespeed=False)
    lead["website_score"] = analysis["score"]
    lead["website_grade"] = analysis["grade"]
    lead["website_is_bad"] = analysis["is_bad"]
    lead["website_issues"] = analysis.get("issues", [])
    lead["website_reachable"] = analysis["reachable"]
    if not lead["website_is_bad"]:
        return None

    email_data = find_emails(lead["name"], lead["website"], lead.get("address", ""))
    lead["best_email"] = email_data.get("best_email")
    lead["best_name"] = email_data.get("best_name")
    lead["contact_emails"] = ", ".join(email_data.get("contact_emails", []))
    lead["public_emails"] = ", ".join(email_data.get("public_emails", []))
    if not lead["best_email"]:
        return None

    return build_queue_item(lead)


def prepare_places_lead(place: dict) -> dict | None:
    lead = {
        "name": place.get("name", ""),
        "website": "",
        "domain": "",
        "has_website": False,
        "industry": place.get("industry_query", ""),
        "source": place.get("source", "google_places_no_website"),
        "phone": place.get("phone", ""),
        "address": place.get("address", ""),
        "place_id": place.get("place_id", ""),
        "rating": place.get("rating", ""),
        "review_count": place.get("review_count", ""),
        "google_maps_url": place.get("google_maps_url", ""),
        "qualification_reason": place.get("qualification_reason", "No website listed on Google Places"),
    }

    analysis = analyze_website("", use_pagespeed=False)
    lead["website_score"] = analysis["score"]
    lead["website_grade"] = analysis["grade"]
    lead["website_is_bad"] = analysis["is_bad"]
    lead["website_issues"] = analysis.get("issues", [])
    lead["website_reachable"] = analysis["reachable"]

    email_data = find_emails(lead["name"], "", lead.get("address", ""))
    lead["best_email"] = email_data.get("best_email")
    lead["best_name"] = email_data.get("best_name")
    lead["contact_emails"] = ", ".join(email_data.get("contact_emails", []))
    lead["public_emails"] = ", ".join(email_data.get("public_emails", []))
    if not lead["best_email"]:
        return None

    return build_queue_item(lead)


def refill_marker_path(now: datetime | None = None) -> str:
    return output_path(f"scheduled_refill_{today_string(now)}.done")


def refill_already_attempted(now: datetime | None = None) -> bool:
    return os.path.exists(refill_marker_path(now))


def mark_refill_attempted(now: datetime | None = None) -> None:
    with open(refill_marker_path(now), "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat())


def refill_queue(queue: list[dict], force: bool = False) -> int:
    if not force and len(pending_queue(queue)) >= SCHEDULED_REFILL_MIN_QUEUE:
        return 0
    if not force and refill_already_attempted():
        return 0

    print("[scheduled] Refilling outreach queue...")
    keys = queued_keys(queue)
    added = 0

    for location in TARGET_LOCATIONS:
        for industry in SCHEDULED_TARGET_INDUSTRIES:
            if added >= SCHEDULED_REFILL_LIMIT:
                break

            website_query = f"{industry} {location}"
            for company in discover_companies(website_query)[:8]:
                if added >= SCHEDULED_REFILL_LIMIT:
                    break
                company["industry_query"] = website_query
                candidate_key = lead_key(company)
                if candidate_key in keys:
                    continue
                lead = prepare_website_lead(company)
                if not lead:
                    continue
                keys.add(lead_key(lead))
                queue.append(lead)
                added += 1
                print(f"[scheduled] Queued {lead['name']} <{lead['best_email']}>")

            for place in discover_no_website_places(industry, location):
                if added >= SCHEDULED_REFILL_LIMIT:
                    break
                candidate_key = lead_key(place)
                if candidate_key in keys:
                    continue
                lead = prepare_places_lead(place)
                if not lead:
                    continue
                keys.add(lead_key(lead))
                queue.append(lead)
                added += 1
                print(f"[scheduled] Queued {lead['name']} <{lead['best_email']}>")

        if added >= SCHEDULED_REFILL_LIMIT:
            break

    mark_refill_attempted()
    save_queue(queue)
    print(f"[scheduled] Queue refill added {added} lead(s).")
    return added


def append_activity(rows: list[dict]) -> None:
    if not rows:
        return
    filepath = output_path(SCHEDULED_ACTIVITY_FILE)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ACTIVITY_FIELDNAMES, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def activity_for_date(date_text: str) -> list[dict]:
    filepath = output_path(SCHEDULED_ACTIVITY_FILE)
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row.get("date") == date_text]


def report_already_sent(date_text: str) -> bool:
    filepath = output_path(SCHEDULED_REPORT_HISTORY_FILE)
    if not os.path.exists(filepath):
        return False
    with open(filepath, newline="", encoding="utf-8") as f:
        return any(row.get("date") == date_text and row.get("sent") == "True" for row in csv.DictReader(f))


def append_report_history(rows: list[dict]) -> None:
    filepath = output_path(SCHEDULED_REPORT_HISTORY_FILE)
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def format_company_rundown(row: dict, number: int) -> str:
    issues = row.get("website_issues") or ""
    if isinstance(issues, list):
        issues = "; ".join(issues)
    return "\n".join([
        f"{number}. {row.get('company', '')}",
        f"   To: {row.get('email', '')}",
        f"   Status: {row.get('status', '')}",
        f"   Type: {row.get('email_type', '')}",
        f"   Industry: {row.get('industry', '')}",
        f"   Why: {row.get('qualification_reason', '')}",
        f"   Website: {row.get('website', '') or 'No website listed'}",
        f"   Website score: {row.get('website_score', '')} ({row.get('website_grade', '')})",
        f"   Issues: {issues}",
        f"   Google rating: {row.get('rating', '')} / Reviews: {row.get('review_count', '')}",
        f"   Phone: {row.get('phone', '')}",
        f"   Address: {row.get('address', '')}",
        f"   Subject: {row.get('subject', '')}",
    ])


def build_report_body(date_text: str, rows: list[dict], reason: str) -> str:
    sent_rows = [row for row in rows if row.get("sent") == "True" or row.get("status") == "sent"]
    failed_rows = [row for row in rows if row.get("status") == "failed"]
    skipped_rows = [row for row in rows if row.get("status") == "skipped"]

    lines = [
        f"Daily outreach report for {date_text}",
        "",
        f"Reason: {reason}",
        f"Sent: {len(sent_rows)}",
        f"Failed: {len(failed_rows)}",
        f"Skipped: {len(skipped_rows)}",
        f"Daily cap: {SCHEDULED_DAILY_EMAIL_LIMIT}",
        "",
    ]

    if not rows:
        lines.append("No outreach activity was recorded today.")
        return "\n".join(lines)

    lines.append("Company rundown:")
    lines.append("")
    for index, row in enumerate(rows, start=1):
        lines.append(format_company_rundown(row, index))
        lines.append("")
    return "\n".join(lines).strip()


def send_daily_report(reason: str, dry_run: bool = False, force: bool = False) -> bool:
    date_text = today_string()
    if not force and report_already_sent(date_text):
        print(f"[scheduled] Report already sent for {date_text}.")
        return True

    rows = activity_for_date(date_text)
    sent_count = sum(1 for row in rows if row.get("sent") == "True" or row.get("status") == "sent")
    failed_count = sum(1 for row in rows if row.get("status") == "failed")
    skipped_count = sum(1 for row in rows if row.get("status") == "skipped")
    subject = f"Bunz Webby outreach report - {date_text}"
    body = build_report_body(date_text, rows, reason)

    history_rows = []
    all_sent = True
    for recipient in REPORT_RECIPIENTS:
        if dry_run:
            print(f"[DRY RUN] Would send report to {recipient}: {subject}")
            success = True
        else:
            success = send_email(recipient, subject, body, dry_run=False)
            history_rows.append({
                "date": date_text,
                "timestamp": datetime.now().isoformat(),
                "recipient": recipient,
                "sent": str(success),
                "reason": reason,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
            })
        all_sent = all_sent and success

    if history_rows:
        append_report_history(history_rows)
    return all_sent


def activity_row_from_result(lead: dict, result: dict) -> dict:
    return {
        "date": today_string(),
        "timestamp": result.get("timestamp", datetime.now().isoformat()),
        "company": lead.get("name", result.get("company", "")),
        "email": result.get("email", lead.get("best_email", "")),
        "contact_name": result.get("contact_name", lead.get("best_name", "")) or "",
        "email_type": result.get("email_type", ""),
        "subject": result.get("subject", ""),
        "sent": str(result.get("sent", False)),
        "status": result.get("status", ""),
        "reason": result.get("reason", ""),
        "industry": lead.get("industry", ""),
        "source": lead.get("source", ""),
        "website": lead.get("website", ""),
        "website_score": lead.get("website_score", ""),
        "website_grade": lead.get("website_grade", ""),
        "website_issues": "; ".join(lead.get("website_issues", [])) if isinstance(lead.get("website_issues"), list) else lead.get("website_issues", ""),
        "rating": lead.get("rating", ""),
        "review_count": lead.get("review_count", ""),
        "phone": lead.get("phone", ""),
        "address": lead.get("address", ""),
        "qualification_reason": lead.get("qualification_reason", ""),
    }


def update_queue_from_result(queue: list[dict], result: dict) -> None:
    result_email = (result.get("email") or "").strip().lower()
    for lead in queue:
        if (lead.get("best_email") or "").strip().lower() != result_email:
            continue
        if result.get("status") == "sent":
            lead["status"] = "sent"
            lead["sent_at"] = result.get("timestamp")
        elif result.get("status") == "skipped":
            lead["status"] = "skipped"
            lead["skipped_at"] = result.get("timestamp")
            lead["skip_reason"] = result.get("reason", "")
        elif result.get("status") == "failed":
            lead["status"] = "failed"
            lead["failed_at"] = result.get("timestamp")
        return


def run_scheduled_once(dry_run: bool = False) -> None:
    now = datetime.now()
    print(f"[scheduled] Run started at {now.isoformat(timespec='seconds')}")

    if not SCHEDULED_OUTREACH_ENABLED:
        print("[scheduled] Scheduled outreach is disabled.")
        return

    if not is_business_day(now):
        print("[scheduled] Outside configured business days. Exiting.")
        return

    if after_business_hours(now):
        send_daily_report("business day ended", dry_run=dry_run)
        return

    if not in_business_hours(now):
        print("[scheduled] Outside configured business hours. Exiting.")
        return

    queue = load_queue()
    if SCHEDULED_AUTO_REFILL_QUEUE:
        refill_queue(queue)

    pending = sorted(pending_queue(queue), key=compute_lead_priority, reverse=True)
    if not pending:
        print("[scheduled] No queued leads with email addresses. Exiting.")
        save_queue(queue)
        return

    already_sent = sent_today_count(load_send_history())
    remaining_today = max(0, SCHEDULED_DAILY_EMAIL_LIMIT - already_sent)
    if remaining_today <= 0:
        print("[scheduled] Daily cap reached. Sending report if needed.")
        send_daily_report("daily cap reached", dry_run=dry_run)
        return

    target_this_run = min(
        SCHEDULED_MAX_EMAILS_PER_RUN,
        remaining_today,
        len(pending),
        max(1, math.ceil(remaining_today / runs_left_today(now))),
    )
    selected = pending[:target_this_run]
    print(f"[scheduled] Sending {len(selected)} outreach email(s). Remaining daily capacity: {remaining_today}.")

    if dry_run:
        results = send_outreach(selected, dry_run=True, max_per_day=SCHEDULED_DAILY_EMAIL_LIMIT)
    else:
        results = send_outreach(
            selected,
            dry_run=False,
            delay_seconds=SCHEDULED_INTRA_RUN_DELAY_SECONDS,
            max_per_day=SCHEDULED_DAILY_EMAIL_LIMIT,
        )

    activity_rows = []
    leads_by_email = {(lead.get("best_email") or "").strip().lower(): lead for lead in selected}
    for result in results:
        lead = leads_by_email.get((result.get("email") or "").strip().lower(), {})
        activity_rows.append(activity_row_from_result(lead, result))
        if not dry_run:
            update_queue_from_result(queue, result)

    if not dry_run:
        append_activity(activity_rows)
        save_queue(queue)

    sent_now = sum(1 for result in results if result.get("status") == "sent")
    if already_sent + sent_now >= SCHEDULED_DAILY_EMAIL_LIMIT:
        send_daily_report("daily cap reached", dry_run=dry_run)

    print("[scheduled] Run complete. Exiting.")


def print_status() -> None:
    now = datetime.now()
    queue = load_queue()
    print(f"Scheduled outreach enabled: {SCHEDULED_OUTREACH_ENABLED}")
    print(f"Now: {now.isoformat(timespec='seconds')}")
    print(f"Business days: {', '.join(sorted(normalized_business_days()))}")
    print(f"Business hours: {BUSINESS_HOURS_START}-{BUSINESS_HOURS_END}")
    print(f"In send window: {is_business_day(now) and in_business_hours(now)}")
    print(f"Daily cap: {SCHEDULED_DAILY_EMAIL_LIMIT}")
    print(f"Sent today: {sent_today_count(load_send_history())}")
    print(f"Pending queued leads: {len(pending_queue(queue))}")
    print(f"Report recipients: {', '.join(REPORT_RECIPIENTS)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduled outreach worker")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one scheduled send pass and exit")
    run_parser.add_argument("--dry-run", action="store_true", help="Preview scheduled sends without modifying queue or sending email")

    refill_parser = subparsers.add_parser("refill", help="Refill the outreach queue now")
    refill_parser.add_argument("--force", action="store_true", help="Refill even if today's refill was already attempted")

    report_parser = subparsers.add_parser("report", help="Send today's report now")
    report_parser.add_argument("--dry-run", action="store_true", help="Preview report send")
    report_parser.add_argument("--force", action="store_true", help="Send even if a report was already sent today")
    report_parser.add_argument("--reason", default="manual report", help="Reason line for the report")

    subparsers.add_parser("status", help="Print scheduler status")

    args = parser.parse_args()
    command = args.command or "status"

    if command == "run":
        run_scheduled_once(dry_run=args.dry_run)
    elif command == "refill":
        queue = load_queue()
        refill_queue(queue, force=args.force)
    elif command == "report":
        send_daily_report(args.reason, dry_run=args.dry_run, force=args.force)
    else:
        print_status()


if __name__ == "__main__":
    main()