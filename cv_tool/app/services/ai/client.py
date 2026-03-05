import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.services.ai.prompts import SYSTEM, USER_TEMPLATE, PROMPT_VERSION
from app.services.ai.normalize import parse_json_strict, ensure_required_shape

class AIClient:
    def enrich(self, cv_text: str) -> dict:
        raise NotImplementedError

class StubAIClient(AIClient):
    def enrich(self, cv_text: str) -> dict:
        # MVP: deterministic placeholder (no beautify yet)
        # We still wrap into canonical structure so rendering works end-to-end.
        return ensure_required_shape({
            "cv_json": {
                "meta": {
                    "schema_version": "cv-json-v1",
                    "language": "en",
                    "source": {"original_filename": None, "mime_type": None, "ingested_at": None},
                },
                "person": {"full_name": None, "headline": None, "location": None, "email": None, "phone": None, "links": []},
                "summary": [],
                "skills": {"core": [], "secondary": [], "tools": [], "certifications": []},
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
                "languages": [],
                "other": {"publications": [], "awards": [], "volunteering": []},
                "integrity": {
                    "open_questions": ["AI is in stub mode. Enable AI_PROVIDER=openai to get enrichment."],
                    "risk_flags": [],
                    "no_hallucination_policy": True
                }
            },
            "open_questions": ["AI is in stub mode."],
            "risk_flags": [],
            "change_log": [{"type": "stub", "where": "all", "note": "No AI enrichment performed."}]
        })

class OpenAICompatibleClient(AIClient):
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def enrich(self, cv_text: str) -> dict:
        user_prompt = USER_TEMPLATE.replace("{{CV_TEXT}}", cv_text)
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        url = settings.openai_base_url.rstrip("/") + "/chat/completions"
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        obj = parse_json_strict(content)
        obj = ensure_required_shape(obj)
        # stamp prompt version
        obj["cv_json"].setdefault("meta", {})
        obj["cv_json"]["meta"]["prompt_version"] = PROMPT_VERSION
        return obj

def get_ai_client() -> AIClient:
    if settings.ai_provider.lower() == "openai":
        return OpenAICompatibleClient()
    return StubAIClient()
