import os
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY") or GOOGLE_SEARCH_API_KEY
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_EMAIL", "")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DISABLE_SENDGRID_CLICK_TRACKING = _env_bool("DISABLE_SENDGRID_CLICK_TRACKING", True)

YOUR_NAME = os.getenv("YOUR_NAME", "")
YOUR_COMPANY = os.getenv("YOUR_COMPANY", "Bunz Webby")
YOUR_PHONE = os.getenv("YOUR_PHONE", "")
YOUR_WEBSITE = os.getenv("YOUR_WEBSITE", "")
PAST_PROJECT_NAME = os.getenv("PAST_PROJECT_NAME", "Gulf States Materials")
PAST_PROJECT_URL = os.getenv("PAST_PROJECT_URL", "https://gulfstatesmaterials.com")
PAST_PROJECT_DISPLAY_URL = os.getenv("PAST_PROJECT_DISPLAY_URL", "gulfstatesmaterials.com")

# Human-paced outreach guardrails
MAX_EMAILS_PER_DAY = _env_int("MAX_EMAILS_PER_DAY", 25)
EMAIL_DELAY_MIN_SECONDS = _env_int("EMAIL_DELAY_MIN_SECONDS", 600)
EMAIL_DELAY_MAX_SECONDS = _env_int("EMAIL_DELAY_MAX_SECONDS", 2700)
EMAIL_SEND_HISTORY_FILE = os.getenv("EMAIL_SEND_HISTORY_FILE", "email_send_history.csv")
SKIP_PREVIOUSLY_EMAILED = _env_bool("SKIP_PREVIOUSLY_EMAILED", True)
USE_GUESSED_EMAILS = _env_bool("USE_GUESSED_EMAILS", False)

# Scheduled outreach worker
SCHEDULED_OUTREACH_ENABLED = _env_bool("SCHEDULED_OUTREACH_ENABLED", True)
SCHEDULED_DAILY_EMAIL_LIMIT = _env_int("SCHEDULED_DAILY_EMAIL_LIMIT", 25)
SCHEDULED_MAX_EMAILS_PER_RUN = _env_int("SCHEDULED_MAX_EMAILS_PER_RUN", 2)
SCHEDULED_INTRA_RUN_DELAY_SECONDS = _env_int("SCHEDULED_INTRA_RUN_DELAY_SECONDS", 30)
SCHEDULED_TASK_INTERVAL_MINUTES = _env_int("SCHEDULED_TASK_INTERVAL_MINUTES", 30)
BUSINESS_DAYS = _env_csv("BUSINESS_DAYS", ["MON", "TUE", "WED", "THU", "FRI"])
BUSINESS_HOURS_START = os.getenv("BUSINESS_HOURS_START", "09:00")
BUSINESS_HOURS_END = os.getenv("BUSINESS_HOURS_END", "17:00")
SCHEDULED_QUEUE_FILE = os.getenv("SCHEDULED_QUEUE_FILE", "scheduled_outreach_queue.json")
SCHEDULED_ACTIVITY_FILE = os.getenv("SCHEDULED_ACTIVITY_FILE", "scheduled_outreach_activity.csv")
SCHEDULED_REPORT_HISTORY_FILE = os.getenv("SCHEDULED_REPORT_HISTORY_FILE", "scheduled_report_history.csv")
SCHEDULED_AUTO_REFILL_QUEUE = _env_bool("SCHEDULED_AUTO_REFILL_QUEUE", True)
SCHEDULED_REFILL_MIN_QUEUE = _env_int("SCHEDULED_REFILL_MIN_QUEUE", 10)
SCHEDULED_REFILL_LIMIT = _env_int("SCHEDULED_REFILL_LIMIT", 50)
REPORT_RECIPIENTS = _env_csv("REPORT_RECIPIENTS", ["lucas@iqventoryllc.com", "amoreno@iqventoryllc.com"])
SCHEDULED_TARGET_INDUSTRIES = _env_csv("SCHEDULED_TARGET_INDUSTRIES", [
    "commercial concrete contractor",
    "ready mix concrete",
    "asphalt contractor",
    "excavation contractor",
    "demolition contractor",
    "dump truck service",
    "sand and gravel supplier",
    "metal fabricator",
    "welding shop",
    "machine shop",
    "industrial equipment repair",
    "commercial roofing contractor",
])

# Google Places targeting for businesses with strong reputation but no website
ENABLE_NO_WEBSITE_PLACES = _env_bool("ENABLE_NO_WEBSITE_PLACES", True)
TARGET_LOCATIONS = _env_csv("TARGET_LOCATIONS", ["Houston TX"])
MIN_GOOGLE_RATING = _env_float("MIN_GOOGLE_RATING", 4.2)
MIN_GOOGLE_REVIEW_COUNT = _env_int("MIN_GOOGLE_REVIEW_COUNT", 25)
PLACES_RESULTS_PER_QUERY = _env_int("PLACES_RESULTS_PER_QUERY", 8)

# ── Target Industries ──
# Only massive-money industries. Every one of these is the kind of company
# doing $5M-$500M+/year in revenue. These are the sectors where companies
# are too busy making money to care about their website.
TARGET_INDUSTRIES = [
    # Mining, quarrying, aggregates — $10M-$1B+ companies
    "mining corporation",
    "gold mining company",
    "coal mining corporation",
    "copper mining company",
    "quarry operator",
    "sand and gravel producer",
    "aggregate mining company",
    "mineral exploration company",
    "lithium mining company",
    "phosphate mining company",
    # Oil, gas, energy — $50M-$100B+ companies
    "oilfield services corporation",
    "oil drilling contractor",
    "pipeline construction company",
    "natural gas company",
    "offshore drilling company",
    "petroleum company",
    "refinery services company",
    "midstream oil and gas company",
    # Heavy civil / infrastructure — $10M-$1B+ companies
    "heavy civil construction company",
    "bridge construction company",
    "highway construction contractor",
    "dam construction company",
    "tunnel construction company",
    "marine construction contractor",
    "railroad construction company",
    # Commercial / industrial construction — $20M-$500M+ companies
    "commercial general contractor",
    "industrial construction company",
    "power plant construction contractor",
    "refinery construction contractor",
    "data center construction company",
    # Steel, metals, foundries — $10M-$500M+ companies
    "steel manufacturing company",
    "structural steel fabricator",
    "steel service center",
    "aluminum manufacturer",
    "iron foundry",
    "metal stamping company",
    "steel pipe manufacturer",
    "steel distributor",
    # Concrete, asphalt, materials — $10M-$200M+ companies
    "ready mix concrete company",
    "precast concrete manufacturer",
    "asphalt producer",
    "cement manufacturer",
    "building materials manufacturer",
    # Heavy equipment & fleet — $20M-$500M+ companies
    "heavy equipment rental company",
    "crane rental company",
    "earthmoving company",
    "fleet management company",
    # Trucking & freight — $10M-$1B+ companies
    "trucking corporation",
    "freight carrier company",
    "heavy haul transportation",
    "bulk carrier trucking",
    "tanker trucking company",
    "flatbed trucking company",
    # Waste, environmental, recycling — $10M-$500M+ companies
    "waste management corporation",
    "industrial waste services",
    "scrap metal recycling company",
    "hazardous waste disposal company",
    "demolition and environmental company",
    # Industrial manufacturing — $10M-$1B+ companies
    "industrial manufacturer",
    "chemical manufacturer",
    "plastics manufacturer",
    "paper mill company",
    "glass manufacturer",
    "lumber mill company",
    "packaging manufacturer",
    # Agriculture at scale — $10M-$500M+ companies
    "grain elevator corporation",
    "agricultural commodity company",
    "feed mill corporation",
    "fertilizer company",
    "seed company",
    "livestock company",
    # Utilities & infrastructure — $50M-$10B+ companies
    "electric utility company",
    "water utility company",
    "telecommunications infrastructure company",
    "fiber optic construction company",
]

# Website quality thresholds
WEBSITE_SCORE_THRESHOLD = 50  # Out of 100 — below this is "bad"

OUTPUT_DIR = "leads_output"
