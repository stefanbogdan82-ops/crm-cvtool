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
    if value.strip() == "":
        return True
    return bool(DATE_RE_YYYY.fullmatch(value) or DATE_RE_YYYY_MM.fullmatch(value))


def _normalize_date(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if value == "":
        return ""
    if DATE_RE_YYYY.fullmatch(value) or DATE_RE_YYYY_MM.fullmatch(value):
        return value
    return ""


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y"}:
            return True
        if v in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _string_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _ensure_list(value):
        if item is None:
            continue
        if isinstance(item, str):
            s = item.strip()
            if s:
                out.append(s)
            continue
        if isinstance(item, dict):
            s = _to_str(item.get("name") or item.get("title") or item.get("value"))
            if s:
                out.append(s)
            continue
        s = _to_str(item)
        if s:
            out.append(s)
    return out


def _walk_and_forbid_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise ValueError(f"Forbidden field '{k}' found at {path or 'root'}")
            _walk_and_forbid_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_and_forbid_keys(item, f"{path}[{i}]")


def _normalize_title_block(value: Any) -> dict:
    if not isinstance(value, dict):
        value = {}

    full_name = _to_str(value.get("full_name"))
    first_name = _to_str(value.get("first_name"))
    last_name = _to_str(value.get("last_name"))

    if full_name and not first_name and not last_name:
        parts = full_name.split()
        if len(parts) == 1:
            first_name = parts[0]
        elif len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])

    return {
        "title": _to_str(value.get("title")),
        "first_name": first_name,
        "last_name": last_name,
        "seniority": _to_str(value.get("seniority")),
    }


def _normalize_academic_qualifications(value: Any) -> list[dict]:
    out: list[dict] = []

    for item in _ensure_list(value):
        if isinstance(item, str):
            out.append({
                "name": item.strip(),
                "achievement_year": "",
            })
            continue

        if not isinstance(item, dict):
            item = {}

        out.append({
            "name": _to_str(item.get("name") or item.get("degree") or item.get("title")),
            "achievement_year": _normalize_date(
                item.get("achievement_year") or item.get("year") or item.get("graduation_year")
            ),
        })

    return out


def _normalize_languages_spoken(value: Any) -> list[dict]:
    out: list[dict] = []

    for item in _ensure_list(value):
        if isinstance(item, str):
            out.append({
                "language": item.strip(),
                "level": "",
            })
            continue

        if not isinstance(item, dict):
            item = {}

        out.append({
            "language": _to_str(item.get("language") or item.get("name")),
            "level": _to_str(item.get("level") or item.get("proficiency")),
        })

    return out


def _normalize_work_experience_compact(value: Any) -> list[dict]:
    out: list[dict] = []

    for item in _ensure_list(value):
        if isinstance(item, str):
            out.append({
                "company": "",
                "job_title": item.strip(),
                "start_date": "",
                "end_date": "",
                "period_label": "",
            })
            continue

        if not isinstance(item, dict):
            item = {}

        out.append({
            "company": _to_str(item.get("company") or item.get("employer")),
            "job_title": _to_str(item.get("job_title") or item.get("title") or item.get("role")),
            "start_date": _normalize_date(item.get("start_date") or item.get("from")),
            "end_date": _normalize_date(item.get("end_date") or item.get("to")),
            "period_label": _to_str(item.get("period_label")),
        })

    return out


def _normalize_technologies(value: Any) -> list[dict]:
    """
    Canonical schema:
    [
      {
        "group_key": "...",
        "group_label": "...",
        "items": ["..."]
      }
    ]

    Accepts:
    - canonical grouped list
    - flat list of strings -> one "other" group
    - dict of groups -> converted to canonical list
    """
    if value is None:
        return []

    # Case 1: dict keyed by group
    if isinstance(value, dict):
        out: list[dict] = []
        for group_key, group_items in value.items():
            key = _to_str(group_key).lower()
            if key not in ALLOWED_TECH_GROUP_KEYS:
                key = "other"

            items = _string_list(group_items)
            if items:
                out.append({
                    "group_key": key,
                    "group_label": key.replace("_", " ").title(),
                    "items": items,
                })
        return out

    # Case 2: flat list of strings/dicts -> pack into "other"
    if isinstance(value, list):
        if all(not isinstance(x, dict) for x in value):
            items = _string_list(value)
            return [{
                "group_key": "other",
                "group_label": "Other",
                "items": items,
            }] if items else []

        out: list[dict] = []
        for item in value:
            if isinstance(item, dict):
                group_key = _to_str(item.get("group_key")).lower()
                if group_key not in ALLOWED_TECH_GROUP_KEYS:
                    group_key = "other"

                out.append({
                    "group_key": group_key,
                    "group_label": _to_str(item.get("group_label")) or group_key.replace("_", " ").title(),
                    "items": _string_list(item.get("items")),
                })
            elif isinstance(item, str):
                s = item.strip()
                if s:
                    out.append({
                        "group_key": "other",
                        "group_label": "Other",
                        "items": [s],
                    })
        return out

    # Case 3: single scalar
    s = _to_str(value)
    if not s:
        return []
    return [{
        "group_key": "other",
        "group_label": "Other",
        "items": [s],
    }]


def _normalize_certifications(value: Any) -> list[dict]:
    out: list[dict] = []

    for item in _ensure_list(value):
        if isinstance(item, str):
            out.append({
                "name": item.strip(),
                "achievement_date": "",
            })
            continue

        if not isinstance(item, dict):
            item = {}

        out.append({
            "name": _to_str(item.get("name") or item.get("title")),
            "achievement_date": _normalize_date(
                item.get("achievement_date") or item.get("achievement_year") or item.get("year")
            ),
        })

    return out


def _normalize_project_experience(value: Any) -> list[dict]:
    out: list[dict] = []

    for item in _ensure_list(value):
        if isinstance(item, str):
            out.append({
                "period_label": "",
                "project_name": item.strip(),
                "project_start": "",
                "project_end": "",
                "industry": [],
                "project_target": {"description": ""},
                "responsibilities": [],
                "roles": [],
                "skills": [],
            })
            continue

        if not isinstance(item, dict):
            item = {}

        project_target = item.get("project_target")
        if not isinstance(project_target, dict):
            project_target = {"description": _to_str(item.get("description") or item.get("summary"))}

        out.append({
            "period_label": _to_str(item.get("period_label")),
            "project_name": _to_str(item.get("project_name") or item.get("name") or item.get("title")),
            "project_start": _normalize_date(item.get("project_start") or item.get("start_date") or item.get("from")),
            "project_end": _normalize_date(item.get("project_end") or item.get("end_date") or item.get("to")),
            "industry": _string_list(item.get("industry") or item.get("industries")),
            "project_target": {
                "description": _to_str(project_target.get("description"))
            },
            "responsibilities": _string_list(item.get("responsibilities")),
            "roles": _string_list(item.get("roles") or item.get("role")),
            "skills": _string_list(item.get("skills") or item.get("technologies")),
        })

    return out


def _normalize_integrity(value: Any) -> dict:
    if not isinstance(value, dict):
        value = {}

    return {
        "open_questions": _string_list(value.get("open_questions")),
        "risk_flags": _string_list(value.get("risk_flags")),
        "no_hallucination_policy": True,
    }


def ensure_required_shape(obj: dict) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("AI output is not a JSON object")

    # Top-level output shape
    cv_json = obj.get("cv_json")
    if not isinstance(cv_json, dict):
        cv_json = {}

    obj["cv_json"] = cv_json
    obj["open_questions"] = _string_list(obj.get("open_questions"))
    obj["risk_flags"] = _string_list(obj.get("risk_flags"))

    change_log = obj.get("change_log")
    if not isinstance(change_log, list):
        change_log = []
    obj["change_log"] = change_log

    # Meta
    meta = cv_json.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    cv_json["meta"] = {
        "schema_version": "cv-json-v1",
        "language": _to_str(meta.get("language")) or "en",
    }

    # Enforce exact top-level schema by reconstructing it
    normalized_cv_json = {
        "meta": cv_json["meta"],
        "title_block": _normalize_title_block(cv_json.get("title_block")),
        "academic_qualifications": _normalize_academic_qualifications(cv_json.get("academic_qualifications")),
        "main_skills": _string_list(cv_json.get("main_skills")),
        "languages_spoken": _normalize_languages_spoken(cv_json.get("languages_spoken")),
        "work_experience_compact": _normalize_work_experience_compact(cv_json.get("work_experience_compact")),
        "technologies": _normalize_technologies(cv_json.get("technologies")),
        "certifications": _normalize_certifications(cv_json.get("certifications")),
        "industries": _string_list(cv_json.get("industries")),
        "project_experience": _normalize_project_experience(cv_json.get("project_experience")),
        "integrity": _normalize_integrity(cv_json.get("integrity")),
    }

    obj["cv_json"] = normalized_cv_json

    # Final validation pass on canonical structure
    cv_json = obj["cv_json"]

    if list(cv_json.keys()) != TOP_LEVEL_KEYS:
        raise ValueError("Internal normalization error: cv_json keys do not match required schema")

    tb = cv_json["title_block"]
    for k in ["title", "first_name", "last_name", "seniority"]:
        if not isinstance(tb.get(k), str):
            raise ValueError(f"title_block.{k} must be a string")

    for i, item in enumerate(cv_json["academic_qualifications"]):
        if not isinstance(item, dict):
            raise ValueError(f"academic_qualifications[{i}] must be an object")
        if not isinstance(item.get("name"), str):
            raise ValueError(f"academic_qualifications[{i}].name must be a string")
        if not isinstance(item.get("achievement_year"), str):
            raise ValueError(f"academic_qualifications[{i}].achievement_year must be a string")
        if item["achievement_year"] and not DATE_RE_YYYY.fullmatch(item["achievement_year"]):
            # For academic qualifications keep it stricter: year only
            item["achievement_year"] = ""

    for arr_key in ["main_skills", "industries"]:
        arr = cv_json[arr_key]
        if not isinstance(arr, list) or any(not isinstance(x, str) for x in arr):
            raise ValueError(f"{arr_key} must be a list of strings")

    for i, item in enumerate(cv_json["languages_spoken"]):
        if not isinstance(item, dict):
            raise ValueError(f"languages_spoken[{i}] must be an object")
        if not isinstance(item.get("language"), str):
            raise ValueError(f"languages_spoken[{i}].language must be a string")
        if not isinstance(item.get("level"), str):
            raise ValueError(f"languages_spoken[{i}].level must be a string")

    for i, item in enumerate(cv_json["work_experience_compact"]):
        if not isinstance(item, dict):
            raise ValueError(f"work_experience_compact[{i}] must be an object")
        for k in ["company", "job_title", "start_date", "end_date", "period_label"]:
            if not isinstance(item.get(k), str):
                raise ValueError(f"work_experience_compact[{i}].{k} must be a string")
        if not _is_valid_date(item["start_date"]):
            item["start_date"] = ""
        if not _is_valid_date(item["end_date"]):
            item["end_date"] = ""

    for i, g in enumerate(cv_json["technologies"]):
        if not isinstance(g, dict):
            raise ValueError(f"technologies[{i}] must be an object")
        if g.get("group_key") not in ALLOWED_TECH_GROUP_KEYS:
            g["group_key"] = "other"
        if not isinstance(g.get("group_label"), str):
            g["group_label"] = "Other"
        if not isinstance(g.get("items"), list):
            g["items"] = []
        g["items"] = _string_list(g["items"])

    for i, c in enumerate(cv_json["certifications"]):
        if not isinstance(c, dict):
            raise ValueError(f"certifications[{i}] must be an object")
        if not isinstance(c.get("name"), str):
            raise ValueError(f"certifications[{i}].name must be a string")
        if not isinstance(c.get("achievement_date"), str):
            raise ValueError(f"certifications[{i}].achievement_date must be a string")
        if not _is_valid_date(c["achievement_date"]):
            c["achievement_date"] = ""

    for i, p in enumerate(cv_json["project_experience"]):
        if not isinstance(p, dict):
            raise ValueError(f"project_experience[{i}] must be an object")

        for k in ["period_label", "project_name", "project_start", "project_end"]:
            if not isinstance(p.get(k), str):
                raise ValueError(f"project_experience[{i}].{k} must be a string")

        if not _is_valid_date(p["project_start"]):
            p["project_start"] = ""
        if not _is_valid_date(p["project_end"]):
            p["project_end"] = ""

        if not isinstance(p.get("industry"), list):
            p["industry"] = []
        p["industry"] = _string_list(p["industry"])

        if not isinstance(p.get("project_target"), dict):
            p["project_target"] = {"description": ""}
        if not isinstance(p["project_target"].get("description"), str):
            p["project_target"]["description"] = ""

        for arr_key in ["responsibilities", "roles", "skills"]:
            if not isinstance(p.get(arr_key), list):
                p[arr_key] = []
            p[arr_key] = _string_list(p[arr_key])

    integ = cv_json["integrity"]
    if not isinstance(integ.get("open_questions"), list):
        raise ValueError("integrity.open_questions must be list of strings")
    if not isinstance(integ.get("risk_flags"), list):
        raise ValueError("integrity.risk_flags must be list of strings")
    integ["open_questions"] = _string_list(integ["open_questions"])
    integ["risk_flags"] = _string_list(integ["risk_flags"])
    integ["no_hallucination_policy"] = True

    # Deep forbid keys after normalization
    _walk_and_forbid_keys(cv_json)

    return obj