from datetime import datetime, timezone
from cv_tool.app.services.ai.ai_client import AIClient
from cv_tool.app.services.ai.normalize import ensure_required_shape


class StubAIClient(AIClient):
    def enrich(self, cv_text: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        base = {
            "meta": {"schema_version": "cv-json-v1", "language": "en"},
            "title_block": {"title": "", "first_name": "", "last_name": "", "seniority": ""},
            "academic_qualifications": [],
            "main_skills": [],
            "languages_spoken": [],
            "work_experience_compact": [],
            "technologies": [],
            "certifications": [],
            "industries": [],
            "project_experience": [],
            "integrity": {
                "open_questions": ["AI is in stub mode. Set AI_PROVIDER=openai to enable enrichment."],
                "risk_flags": [],
                "no_hallucination_policy": True
            }
        }

        return ensure_required_shape({
            "cv_json": base,
            "open_questions": ["AI is in stub mode."],
            "risk_flags": [],
            "change_log": [{"type": "stub", "where": "all", "note": "No AI enrichment performed."}]
        })


def get_ai_client() -> AIClient:
    return StubAIClient()