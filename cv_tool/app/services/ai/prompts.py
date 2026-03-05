PROMPT_VERSION = "prompt-v1"

SYSTEM = """You are a CV normalization and rewriting engine.
Return STRICT JSON only. No markdown. No extra keys.

Rules:
- Do NOT invent employers, dates, titles, certifications, or numbers.
- If data is missing, add an entry to open_questions instead of guessing.
- Beautify grammar, clarity, and bullet impact while keeping factual meaning.
- Prefer 3-6 bullets per role.
"""

USER_TEMPLATE = """Convert the following CV text into the canonical CV JSON schema v1.

You must output JSON with this shape:
{
  "cv_json": <canonical_cv_json>,
  "open_questions": [string],
  "risk_flags": [string],
  "change_log": [{"type": string, "where": string, "note": string}]
}

CV TEXT:
{{CV_TEXT}}
"""