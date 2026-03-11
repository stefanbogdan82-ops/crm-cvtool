import json

from openai import OpenAI

from cv_tool.app.core.config import settings
from cv_tool.app.services.ai.ai_client import AIClient
from cv_tool.app.services.ai.normalize import ensure_required_shape


SYSTEM_PROMPT = """
You are a CV parsing and normalization assistant.

Your task:
- Read raw CV text.
- Extract only information explicitly present in the CV.
- Return ONLY valid JSON.
- Do not wrap the output in markdown.
- Do not invent or infer facts that are not supported by the CV.
- If a value is unknown, use an empty string, empty list, or empty object as appropriate.
- Never include personal contact data such as email, phone, address, website, LinkedIn, or other contact fields.
- Preserve the exact schema requested by the user prompt.
""".strip()


def _build_schema_example() -> dict:
    return {
        "cv_json": {
            "meta": {
                "schema_version": "cv-json-v1",
                "language": "en"
            },
            "title_block": {
                "title": "",
                "first_name": "",
                "last_name": "",
                "seniority": ""
            },
            "academic_qualifications": [
                {
                    "name": "",
                    "achievement_year": ""
                }
            ],
            "main_skills": [""],
            "languages_spoken": [
                {
                    "language": "",
                    "level": ""
                }
            ],
            "work_experience_compact": [
                {
                    "company": "",
                    "job_title": "",
                    "start_date": "",
                    "end_date": "",
                    "period_label": ""
                }
            ],
            "technologies": [
                {
                    "group_key": "other",
                    "group_label": "Other",
                    "items": [""]
                }
            ],
            "certifications": [
                {
                    "name": "",
                    "achievement_date": ""
                }
            ],
            "industries": [""],
            "project_experience": [
                {
                    "period_label": "",
                    "project_name": "",
                    "project_start": "",
                    "project_end": "",
                    "industry": [""],
                    "project_target": {
                        "description": ""
                    },
                    "responsibilities": [""],
                    "roles": [""],
                    "skills": [""]
                }
            ],
            "integrity": {
                "open_questions": [],
                "risk_flags": [],
                "no_hallucination_policy": True
            }
        },
        "open_questions": [],
        "risk_flags": [],
        "change_log": []
    }


def _build_user_prompt(cv_text: str) -> str:
    schema_example = _build_schema_example()

    return f"""
Extract information from the CV text below and return ONLY valid JSON.

Rules:
- Preserve the exact JSON structure shown below.
- Do not return markdown.
- Do not return explanations.
- Do not include any fields not present in the schema.
- Do not include email, phone, address, website, LinkedIn, or other contact details.
- Use empty string / empty list / empty object when unknown.
- Do not hallucinate.
- If technologies are returned, use the grouped schema:
  - group_key
  - group_label
  - items
- Allowed technology group_key values are:
  - cicd
  - databases
  - etl
  - operating_system
  - platforms
  - programming
  - reporting
  - other
- academic_qualifications must be a list of objects with:
  - name
  - achievement_year
- languages_spoken must be a list of objects with:
  - language
  - level
- work_experience_compact must be a list of objects with:
  - company
  - job_title
  - start_date
  - end_date
  - period_label
- certifications must be a list of objects with:
  - name
  - achievement_date
- project_experience must be a list of objects with:
  - period_label
  - project_name
  - project_start
  - project_end
  - industry
  - project_target
  - responsibilities
  - roles
  - skills
- project_target must be an object with:
  - description
- main_skills, industries, integrity.open_questions, integrity.risk_flags, open_questions, risk_flags must be lists of strings.
- Dates should preferably be YYYY or YYYY-MM when known. Otherwise use empty string.
- For academic_qualifications.achievement_year prefer YYYY only.

Required JSON shape:
{json.dumps(schema_example, ensure_ascii=False, indent=2)}

CV text:
{cv_text}
""".strip()


class StubAIClient(AIClient):
    def enrich(self, cv_text: str) -> dict:
        base = {
            "cv_json": {
                "meta": {
                    "schema_version": "cv-json-v1",
                    "language": "en"
                },
                "title_block": {
                    "title": "",
                    "first_name": "",
                    "last_name": "",
                    "seniority": ""
                },
                "academic_qualifications": [],
                "main_skills": [],
                "languages_spoken": [],
                "work_experience_compact": [],
                "technologies": [],
                "certifications": [],
                "industries": [],
                "project_experience": [],
                "integrity": {
                    "open_questions": [
                        "AI is in stub mode. Set AI_PROVIDER=openai to enable enrichment."
                    ],
                    "risk_flags": [],
                    "no_hallucination_policy": True
                }
            },
            "open_questions": [
                "AI is in stub mode."
            ],
            "risk_flags": [],
            "change_log": [
                {
                    "type": "stub",
                    "where": "all",
                    "note": "No AI enrichment performed."
                }
            ]
        }

        return ensure_required_shape(base)


class OpenAIClient(AIClient):
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing. Set it in .env when AI_PROVIDER=openai."
            )

        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.openai_model

    def enrich(self, cv_text: str) -> dict:
        prompt = _build_user_prompt(cv_text)

        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )

        output_text = (response.output_text or "").strip()

        if not output_text:
            raise ValueError("OpenAI response was empty.")

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"OpenAI response was not valid JSON. Response was: {output_text}"
            ) from exc

        print("DEBUG PARSED AI OUTPUT =", json.dumps(parsed, indent=2, ensure_ascii=False))

        return ensure_required_shape(parsed)


def get_ai_client() -> AIClient:
    provider = (settings.ai_provider or "stub").strip().lower()

    if provider == "openai":
        return OpenAIClient()

    return StubAIClient()