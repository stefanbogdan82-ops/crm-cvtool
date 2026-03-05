import json

def ensure_required_shape(obj: dict) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("AI output is not a JSON object")

    for k in ["cv_json", "open_questions", "risk_flags", "change_log"]:
        if k not in obj:
            raise ValueError(f"AI output missing key: {k}")

    if not isinstance(obj["cv_json"], dict):
        raise ValueError("cv_json must be an object")

    # Minimal meta guard
    meta = obj["cv_json"].get("meta") or {}
    if meta.get("schema_version") != "cv-json-v1":
        # if AI didn't set it, enforce it
        obj["cv_json"].setdefault("meta", {})
        obj["cv_json"]["meta"]["schema_version"] = "cv-json-v1"

    return obj

def parse_json_strict(text: str) -> dict:
    # Strict: must be pure JSON
    text = text.strip()
    return json.loads(text)
