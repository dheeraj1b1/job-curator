# app/refiner.py
import re
from datetime import datetime
from app.config import (
    IGNORE_DOMAINS, ACCEPTED_ROLES, PREFIXES_TO_STRIP,
    INDIAN_CITIES, FOREIGN_LOCATIONS
)


def refine_job_batch(raw_jobs: list) -> list:
    """
    Stage 2: Transforms raw blocks into Final Master Tracker rows.
    """
    refined = []

    for job in raw_jobs:
        if job.get("status") != "Selected":
            continue

        raw_text = job.get("Raw_Text", "")

        # 1. Email Extraction & Filtering
        valid_email = extract_valid_email(raw_text)

        # 2. Company Extraction (Priority Logic)
        company = extract_company(raw_text, valid_email)

        # 3. Role Normalization
        role = extract_role(raw_text)

        # 4. Location & Mode
        location = extract_location(raw_text)
        mode = extract_mode(raw_text, location)

        entry = {
            "S.No": len(refined) + 1,
            "Company": company,
            "Role": role,
            "Exp": f"{job.get('Exp_Min')} - {job.get('Exp_Max', '?')} yrs",
            "Location": location,
            "Mode": mode,
            "Email": valid_email,
            "Source_PDF": job.get("Source_PDF"),
            "Notes": generate_tech_notes(raw_text),
            "Domain": extract_domain(raw_text),
            "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        refined.append(entry)

    return refined

# --- HELPERS ---


def extract_valid_email(text: str) -> str:
    """
    Extracts the best contact email based on priority rules.
    Priority 1: Corporate/Company Domain (Immediate Return)
    Priority 2: Allowed Generic (Gmail/Outlook) - (Fallback)
    Priority 3: Blocked (JobCurator/Telegram/WhatsApp) - (Ignored)
    """
    # Regex to find all potential email addresses
    emails = re.findall(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)

    fallback_candidates = []

    # Priority 3: Strictly Blocked Patterns (never use)
    blocked_keywords = ["jobcurator", "telegram",
                        "whatsapp", "noreply", "donotreply"]

    # Priority 2: Allowed Generic Domains (use only if no corporate email exists)
    allowed_generic_domains = {
        "gmail.com", "outlook.com", "yahoo.com",
        "hotmail.com", "rediffmail.com", "icloud.com"
    }

    for email in emails:
        domain = email.split('@')[1].lower()

        # 1. CHECK PRIORITY 3 (BLOCKED)
        if any(keyword in domain for keyword in blocked_keywords):
            continue

        # 2. CHECK PRIORITY 2 (ALLOWED GENERIC)
        if domain in allowed_generic_domains:
            fallback_candidates.append(email)
            continue

        # 3. CHECK PRIORITY 1 (CORPORATE)
        # If it's not blocked and not generic, we assume it's a priority corporate email.
        # We prefer the first corporate email found.
        return email

    # 4. FALLBACK SELECTION
    if fallback_candidates:
        return fallback_candidates[0]

    return "Apply via Company Portal"


def extract_company(text: str, email: str) -> str:
    # Priority 1: From Valid Email Domain
    if email != "Apply via Company Portal":
        domain = email.split('@')[1]
        name = domain.split('.')[0]
        # Cleanup (e.g., 'careers' -> invalid, but usually domain is company name)
        if len(name) > 2:
            return name.title()

    # Priority 2: Regex Patterns in Text
    patterns = [
        r"(?:Hiring for|Client[:\-])\s*([A-Z][a-z0-9]+(?:\s[A-Z][a-z0-9]+)*)",
        r"([A-Z][a-z0-9]+)\s+is hiring"
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()

    # Priority 3: Fallback
    return "Confidential / Client via Consultancy"


def extract_role(text: str) -> str:
    text_lower = text.lower()

    # Find longest matching role
    best_match = ""
    for role in ACCEPTED_ROLES:
        if role in text_lower:
            if len(role) > len(best_match):
                best_match = role

    if not best_match:
        return "QA / SDET"

    # Strip prefixes from the FOUND role context?
    # Actually, we map the accepted keyword to a Title Case string.
    # But if text says "Senior QA Engineer", best_match is "QA Engineer".
    # The prompt says "Strip prefixes". So if we found "QA Engineer", we just return that.
    # We DO NOT prepend "Senior".

    return best_match.title()


def extract_location(text: str) -> str:
    t = text.lower()
    locs = set()

    # Check Foreign
    for f_loc in FOREIGN_LOCATIONS:
        if f_loc.lower() in t:
            locs.add(f_loc)

    # Check Indian Cities
    for city in INDIAN_CITIES:
        if city.lower() in t:
            locs.add(city)

    if "pan india" in t:
        locs.add("Pan India")
    elif "remote" in t and not locs:
        locs.add("Remote")

    if not locs:
        return "Not Specified"

    return ", ".join(sorted(locs))


def extract_mode(text: str, location_str: str) -> str:
    t = text.lower()
    if "remote" in t and "hybrid" not in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "wfo" in t or "work from office" in t or "on-site" in t:
        return "Work From Office"

    # Heuristic: If location is "Remote", mode is Remote
    if "Remote" in location_str:
        return "Remote"

    return "Full-time"


def extract_domain(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["bank", "fintech", "payment", "financial"]):
        return "FinTech"
    if any(k in t for k in ["health", "medical", "pharma"]):
        return "Healthcare"
    if any(k in t for k in ["ecommerce", "retail", "shopping"]):
        return "E-commerce"
    if "saas" in t:
        return "SaaS"
    return "IT Services"


def generate_tech_notes(text: str) -> str:
    """
    Extracts top 4 skills based on strict priority order.
    Returns 'Skill1 + Skill2...' or 'QA Role' if none found.
    """
    t = text.lower()

    # Priority Order: (Output Format, Search Keyword)
    # The order of this list enforces the priority requirement.
    priority_map = [
        ("Java", "java"),
        ("Python", "python"),
        ("Selenium", "selenium"),
        ("API", "api"),
        ("Manual", "manual"),
        ("SQL", "sql"),
        ("Appium", "appium"),
        ("Playwright", "playwright")
    ]

    found_skills = []

    for display_name, keyword in priority_map:
        if keyword in t:
            found_skills.append(display_name)

            # STRICT REQUIREMENT: Max 4 skills
            if len(found_skills) >= 4:
                break

    if not found_skills:
        return "QA Role"

    return " + ".join(found_skills)
