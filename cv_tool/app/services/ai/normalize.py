# app/services/ai/normalize.py

import json
import re
from typing import Any

ALLOWED_TECH_GROUP_KEYS = {
    "cicd",
    "databases",
    "etl",
    "operating_system",
    "platforms",
    "programming",
    "reporting",
    "other",
}

TOP_LEVEL_KEYS = [
    "meta",
    "title_block",
    "academic_qualifications",
    "main_skills",
    "languages_spoken",
    "work_experience_compact",
    "technologies",
    "certifications",
    "industries",
    "project_experience",
    "integrity",
]

DATE_RE_YYYY = re.compile(r"^\d{4}$")
DATE_RE_YYYY_MM = re.compile(r"^\d{4}-\d{2}$")

# Basic safety: forbid these keys anywhere if they appear
FORBIDDEN_KEYS = {"email", "phone", "linkedin", "address", "contact", "website"}

def parse_json_strict(text: str) -> dict:
    text = text.strip()
    return json.loads(text)

def _is_valid_date(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return bool(DATE_RE_YYYY.fullmatch(value) or DATE_RE_YYYY_MM.fullmatch(value))

def _walk_and_forbid_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise ValueError(f"Forbidden field '{k}' found at {path or 'root'}")
            _walk_and_forbid_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_and_forbid_keys(item, f"{path}[{i}]")

def ensure_required_shape(obj: dict) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("AI output is not a JSON object")

    for k in ["cv_json", "open_questions", "risk_flags", "change_log"]:
        if k not in obj:
            raise ValueError(f"AI output missing key: {k}")

    cv_json = obj["cv_json"]
    if not isinstance(cv_json, dict):
        raise ValueError("cv_json must be an object")

    # Enforce schema version
    cv_json.setdefault("meta", {})
    cv_json["meta"]["schema_version"] = "cv-json-v1"
    cv_json["meta"].setdefault("language", "en")

    # Enforce top-level keys (must include all; extra keys are not allowed)
    missing = [k for k in TOP_LEVEL_KEYS if k not in cv_json]
    if missing:
        raise ValueError(f"cv_json missing keys: {missing}")

    extra = [k for k in cv_json.keys() if k not in TOP_LEVEL_KEYS]
    if extra:
        raise ValueError(f"cv_json has extra keys not allowed by schema: {extra}")

    # title_block required keys
    tb = cv_json["title_block"]
    if not isinstance(tb, dict):
        raise ValueError("title_block must be an object")
    for k in ["title", "first_name", "last_name", "seniority"]:
        if k not in tb:
            raise ValueError(f"title_block missing key: {k}")
        if tb[k] is None:
            tb[k] = ""
        if not isinstance(tb[k], str):
            raise ValueError(f"title_block.{k} must be a string")

    # academic_qualifications
    aq = cv_json["academic_qualifications"]
    if not isinstance(aq, list):
        raise ValueError("academic_qualifications must be a list")
    for i, item in enumerate(aq):
        if not isinstance(item, dict):
            raise ValueError(f"academic_qualifications[{i}] must be an object")
        if "name" not in item or "achievement_year" not in item:
            raise ValueError(f"academic_qualifications[{i}] must have name and achievement_year")
        if not isinstance(item["name"], str) or not isinstance(item["achievement_year"], str):
            raise ValueError(f"academic_qualifications[{i}] fields must be strings")
        # year can be YYYY only
        if not DATE_RE_YYYY.fullmatch(item["achievement_year"]):
            raise ValueError(f"academic_qualifications[{i}].achievement_year must be YYYY")

    # main_skills, industries
    for arr_key in ["main_skills", "industries"]:
        arr = cv_json[arr_key]
        if not isinstance(arr, list) or any(not isinstance(x, str) for x in arr):
            raise ValueError(f"{arr_key} must be a list of strings")

    # languages_spoken
    ls = cv_json["languages_spoken"]
    if not isinstance(ls, list):
        raise ValueError("languages_spoken must be a list")
    for i, item in enumerate(ls):
        if not isinstance(item, dict):
            raise ValueError(f"languages_spoken[{i}] must be an object")
        if "language" not in item or "level" not in item:
            raise ValueError(f"languages_spoken[{i}] must have language and level")
        if not isinstance(item["language"], str) or not isinstance(item["level"], str):
            raise ValueError(f"languages_spoken[{i}] fields must be strings")

    # work_experience_compact
    we = cv_json["work_experience_compact"]
    if not isinstance(we, list):
        raise ValueError("work_experience_compact must be a list")
    for i, item in enumerate(we):
        if not isinstance(item, dict):
            raise ValueError(f"work_experience_compact[{i}] must be an object")
        for k in ["company", "job_title"]:
            if k not in item or not isinstance(item[k], str):
                raise ValueError(f"work_experience_compact[{i}].{k} must be a string")
        # Optional but recommended machine dates
        for dk in ["start_date", "end_date"]:
            if dk in item and not _is_valid_date(item[dk]):
                raise ValueError(f"work_experience_compact[{i}].{dk} must be YYYY or YYYY-MM or null")
        if "period_label" in item and item["period_label"] is not None and not isinstance(item["period_label"], str):
            raise ValueError(f"work_experience_compact[{i}].period_label must be a string if present")

    # technologies
    tech = cv_json["technologies"]
    if not isinstance(tech, list):
        raise ValueError("technologies must be a list")
    for i, g in enumerate(tech):
        if not isinstance(g, dict):
            raise ValueError(f"technologies[{i}] must be an object")
        if "group_key" not in g or "group_label" not in g or "items" not in g:
            raise ValueError(f"technologies[{i}] must have group_key, group_label, items")
        if g["group_key"] not in ALLOWED_TECH_GROUP_KEYS:
            raise ValueError(f"technologies[{i}].group_key must be one of {sorted(ALLOWED_TECH_GROUP_KEYS)}")
        if not isinstance(g["group_label"], str):
            raise ValueError(f"technologies[{i}].group_label must be a string")
        if not isinstance(g["items"], list) or any(not isinstance(x, str) for x in g["items"]):
            raise ValueError(f"technologies[{i}].items must be a list of strings")

    # certifications
    certs = cv_json["certifications"]
    if not isinstance(certs, list):
        raise ValueError("certifications must be a list")
    for i, c in enumerate(certs):
        if not isinstance(c, dict):
            raise ValueError(f"certifications[{i}] must be an object")
        if "name" not in c or "achievement_date" not in c:
            raise ValueError(f"certifications[{i}] must have name and achievement_date")
        if not isinstance(c["name"], str):
            raise ValueError(f"certifications[{i}].name must be a string")
        if not _is_valid_date(c["achievement_date"]):
            raise ValueError(f"certifications[{i}].achievement_date must be YYYY or YYYY-MM or null")

    # project_experience
    pe = cv_json["project_experience"]
    if not isinstance(pe, list):
        raise ValueError("project_experience must be a list")
    for i, p in enumerate(pe):
        if not isinstance(p, dict):
            raise ValueError(f"project_experience[{i}] must be an object")
        for k in ["period_label", "project_name"]:
            if k not in p or not isinstance(p[k], str):
                raise ValueError(f"project_experience[{i}].{k} must be a string")
        for dk in ["project_start", "project_end"]:
            if dk in p and not _is_valid_date(p[dk]):
                raise ValueError(f"project_experience[{i}].{dk} must be YYYY or YYYY-MM or null")
        if "industry" in p:
            if not isinstance(p["industry"], list) or any(not isinstance(x, str) for x in p["industry"]):
                raise ValueError(f"project_experience[{i}].industry must be list of strings")
        if "project_target" in p:
            if not isinstance(p["project_target"], dict) or "description" not in p["project_target"]:
                raise ValueError(f"project_experience[{i}].project_target must be object with description")
        if "responsibilities" in p:
            if not isinstance(p["responsibilities"], list) or any(not isinstance(x, str) for x in p["responsibilities"]):
                raise ValueError(f"project_experience[{i}].responsibilities must be list of strings")
        for arr_key in ["roles", "skills"]:
            if arr_key in p:
                if not isinstance(p[arr_key], list) or any(not isinstance(x, str) for x in p[arr_key]):
                    raise ValueError(f"project_experience[{i}].{arr_key} must be list of strings")

    # integrity
    integ = cv_json["integrity"]
    if not isinstance(integ, dict):
        raise ValueError("integrity must be an object")
    for k in ["open_questions", "risk_flags", "no_hallucination_policy"]:
        if k not in integ:
            raise ValueError(f"integrity missing key: {k}")
    if not isinstance(integ["open_questions"], list) or any(not isinstance(x, str) for x in integ["open_questions"]):
        raise ValueError("integrity.open_questions must be list of strings")
    if not isinstance(integ["risk_flags"], list) or any(not isinstance(x, str) for x in integ["risk_flags"]):
        raise ValueError("integrity.risk_flags must be list of strings")
    if integ["no_hallucination_policy"] is not True:
        # enforce true for safety
        integ["no_hallucination_policy"] = True

    # Deep forbid keys (defense in depth)
    _walk_and_forbid_keys(cv_json)

    return obj
