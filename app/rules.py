# # app/rules.py
# import re
# from app.config import (
#     ACCEPTED_ROLES, REQUIRED_TECH, CONDITIONAL_TECH_EXCLUSIONS,
#     HARD_TECH_EXCLUSIONS, HIRING_EXCLUSIONS, EMPLOYMENT_EXCLUSIONS,
#     MIN_EXP_REQUIRED, MAX_EXP_ALLOWED, ALLOW_IMMEDIATE_JOINER
# )


# def evaluate_job_block(text: str, exp_min: int, exp_max: int) -> dict:
#     """
#     Evaluates a specific text block.
#     Returns: { 'status': 'Selected'/'Rejected', 'reason': '...', 'debug_log': [...] }
#     """
#     t = text.lower()
#     logs = []

#     # --- 1. Role Check ---
#     role_match = any(role in t for role in ACCEPTED_ROLES)
#     if not role_match:
#         # Fallback keywords
#         fallback = ["qa", "quality", "test", "sdet"]
#         if any(k in t for k in fallback):
#             logs.append("Role: Matched generic fallback.")
#         else:
#             logs.append("Role: No valid QA role found.")
#             return _reject("Role Mismatch", logs)
#     else:
#         logs.append("Role: Valid QA role found.")

#     # --- 2. Hard Tech Exclusion ---
#     for excl in HARD_TECH_EXCLUSIONS:
#         if excl in t:
#             logs.append(f"Exclusion: Found hard block '{excl}'")
#             return _reject(f"Hard Exclusion ({excl})", logs)

#     # --- 3. Conditional Tech Exclusion ---
#     # Reject "Python" ONLY if no "Java/Selenium/etc" is present
#     has_bad_tech = [excl for excl in CONDITIONAL_TECH_EXCLUSIONS if excl in t]
#     if has_bad_tech:
#         has_good_tech = any(req in t for req in REQUIRED_TECH)
#         if not has_good_tech:
#             logs.append(
#                 f"Exclusion: Found '{has_bad_tech[0]}' without safeguard.")
#             return _reject(f"Tool-Only Exclusion ({has_bad_tech[0]})", logs)
#         else:
#             logs.append(
#                 f"Safeguard: '{has_bad_tech[0]}' allowed due to presence of Required Tech.")

#     # --- 4. Required Tech Check ---
#     # Ensure at least ONE valid tech exists (e.g. dont accept a generic 'QA' job with no skills)
#     if not any(req in t for req in REQUIRED_TECH):
#         logs.append("Tech: No required tech stack found.")
#         return _reject("No Required Tech", logs)

#     # --- 5. Hiring Mode Exclusion (Context Aware) ---
#     # Ignore "Walk-in" if preceded by "No" or "Not"
#     for term in HIRING_EXCLUSIONS:
#         if term in t:
#             # Negative lookbehind regex: matches term ONLY if NOT preceded by "no " or "not "
#             # pattern: (?<!no\s)(?<!not\s)walk-in
#             pattern = fr'(?<!no\s)(?<!not\s){re.escape(term)}'
#             if re.search(pattern, t):
#                 logs.append(f"Exclusion: Found '{term}' (Hiring Mode).")
#                 return _reject(f"Hiring Mode ({term})", logs)
#             else:
#                 logs.append(f"Safeguard: Ignored negated '{term}'.")

#     # --- 6. Employment Type Exclusion ---
#     for excl in EMPLOYMENT_EXCLUSIONS:
#         if excl in t:
#             logs.append(f"Exclusion: Found '{excl}' (Employment Type).")
#             return _reject(f"Employment Type ({excl})", logs)

#     # --- 7. Experience Check (Overlap Logic) ---
#     if exp_min is None:
#         # Strict: Reject if no experience found (often means junk text)
#         logs.append("Exp: None found.")
#         return _reject("No Experience Found", logs)

#     # Reject Freshers (<1 year)
#     effective_max = exp_max if exp_max is not None else exp_min
#     if effective_max < MIN_EXP_REQUIRED:
#         logs.append(
#             f"Exp: Too low ({exp_min}-{effective_max}) < {MIN_EXP_REQUIRED}.")
#         return _reject("Fresher/Low Exp", logs)

#     # Reject Seniors (>5 years start)
#     if exp_min > MAX_EXP_ALLOWED:
#         logs.append(f"Exp: Too high ({exp_min} starts > {MAX_EXP_ALLOWED}).")
#         return _reject("Senior/High Exp", logs)

#     logs.append(
#         f"Exp: Valid ({exp_min}-{exp_max}) overlaps {MIN_EXP_REQUIRED}-{MAX_EXP_ALLOWED}.")

#     return {"status": "Selected", "reason": "Matches Criteria", "debug_log": logs}


# def _reject(reason, logs):
#     return {"status": "Rejected", "reason": reason, "debug_log": logs}


# app/rules.py
import re
from app.config import (
    ACCEPTED_ROLES, REQUIRED_TECH, CONDITIONAL_TECH_EXCLUSIONS,
    HARD_TECH_EXCLUSIONS, HIRING_EXCLUSIONS, EMPLOYMENT_EXCLUSIONS,
    MIN_EXP_REQUIRED, MAX_START_EXP_ALLOWED
)


def evaluate_job_block(text: str, exp_min: int, exp_max: int) -> dict:
    t = text.lower()
    logs = []

    # --- 1. ROLE CHECK ---
    # We accept if ANY accepted role keyword is present.
    # Refiner will normalize the title later.
    if not any(role in t for role in ACCEPTED_ROLES):
        # Fallback for generic QA terms
        if not any(k in t for k in ["qa", "quality", "test", "sdet"]):
            logs.append("Role: No valid QA/SDET role found.")
            return _reject("Role Mismatch", logs)
    logs.append("Role: Valid keyword found.")

    # --- 2. HARD TECH EXCLUSION ---
    for excl in HARD_TECH_EXCLUSIONS:
        if excl in t:
            logs.append(f"Exclusion: Found hard block '{excl}'")
            return _reject(f"Hard Exclusion ({excl})", logs)

    # --- 3. CONDITIONAL TECH EXCLUSION ---
    # Reject "Python" ONLY if no safe tech (Selenium/Java/Manual) is present
    bad_techs = [excl for excl in CONDITIONAL_TECH_EXCLUSIONS if excl in t]
    if bad_techs:
        has_safeguard = any(req in t for req in REQUIRED_TECH)
        if not has_safeguard:
            logs.append(
                f"Exclusion: '{bad_techs[0]}' found without safeguards.")
            return _reject(f"Tool-Only Exclusion ({bad_techs[0]})", logs)
        else:
            logs.append(
                f"Safeguard: '{bad_techs[0]}' allowed due to required tech.")

    # --- 4. HIRING MODE (Context Aware) ---
    # Reject "Walk-in" only if NOT negated ("No Walk-in")
    for term in HIRING_EXCLUSIONS:
        if term in t:
            # Negative lookbehind: matches term if NOT preceded by "no " or "not "
            pattern = fr'(?<!no\s)(?<!not\s){re.escape(term)}'
            if re.search(pattern, t):
                logs.append(f"Exclusion: Found '{term}'.")
                return _reject(f"Hiring Mode ({term})", logs)

    # --- 5. EMPLOYMENT TYPE ---
    for excl in EMPLOYMENT_EXCLUSIONS:
        if excl in t:
            logs.append(f"Exclusion: Found '{excl}'.")
            return _reject(f"Employment Type ({excl})", logs)

    # --- 6. EXPERIENCE LOGIC (STRICT) ---
    if exp_min is None:
        logs.append("Exp: None found.")
        return _reject("No Experience Found", logs)

    # Rule A: Reject Freshers
    if exp_min < MIN_EXP_REQUIRED:
        logs.append(f"Exp: Too low ({exp_min} < {MIN_EXP_REQUIRED}).")
        return _reject("Fresher/Low Exp", logs)

    # Rule B: Reject Senior Starts
    # We only care about the START of the range.
    # 4-9 years -> Start is 4. 4 <= 5. ACCEPT.
    # 6-10 years -> Start is 6. 6 > 5. REJECT.
    if exp_min > MAX_START_EXP_ALLOWED:
        logs.append(
            f"Exp: Starts too high ({exp_min} > {MAX_START_EXP_ALLOWED}).")
        return _reject("Senior/High Exp", logs)

    logs.append(f"Exp: Valid ({exp_min}-{exp_max}).")
    return {"status": "Selected", "reason": "Matches Criteria", "debug_log": logs}


def _reject(reason, logs):
    return {"status": "Rejected", "reason": reason, "debug_log": logs}
