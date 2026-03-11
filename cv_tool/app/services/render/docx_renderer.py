from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from cv_tool.app.core.config import settings
from cv_tool.app.services.render.dates import make_period_label


TECH_GROUP_ORDER = [
    "cicd",
    "databases",
    "etl",
    "operating_system",
    "platforms",
    "programming",
    "reporting",
    "other",
]

ORDER_INDEX = {key: index for index, key in enumerate(TECH_GROUP_ORDER)}


def _resolve_template_path(template_version: str) -> Path:
    """
    Resolve the template path from configured template_dir.

    Example:
        template_dir = ./cv_tool/app/templates
        template_version = company-v1
        -> cv_tool/app/templates/company-v1.docx
    """
    if not settings.template_dir:
        raise ValueError("settings.template_dir is empty or not configured.")

    template_dir = Path(settings.template_dir).resolve()
    template_path = template_dir / f"{template_version}.docx"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    if not template_path.is_file():
        raise FileNotFoundError(f"Template path is not a file: {template_path}")

    return template_path


def _copy_list_of_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Create a shallow copy of a list of dicts so we do not mutate the caller's input.
    """
    return [dict(item) for item in items if isinstance(item, dict)]


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_str_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _to_list(value):
        if item is None:
            continue
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _safe_nested_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _prepare_work_experience(ctx: dict[str, Any]) -> None:
    work_experience = _copy_list_of_dicts(ctx.get("work_experience_compact", []))

    prepared: list[dict[str, Any]] = []
    for item in work_experience:
        prepared_item = {
            "company": str(item.get("company", "") or ""),
            "job_title": str(item.get("job_title", "") or ""),
            "start_date": str(item.get("start_date", "") or ""),
            "end_date": str(item.get("end_date", "") or ""),
            "period_label": str(item.get("period_label", "") or ""),
        }

        if not prepared_item["period_label"]:
            prepared_item["period_label"] = make_period_label(
                prepared_item["start_date"],
                prepared_item["end_date"],
            )

        prepared.append(prepared_item)

    def work_experience_sort_key(item: dict[str, Any]) -> str:
        return item.get("start_date") or ""

    prepared.sort(key=work_experience_sort_key, reverse=True)

    ctx["work_experience_compact"] = prepared[:6]


def _prepare_technologies(ctx: dict[str, Any]) -> None:
    """
    Prepare technologies for templating.

    Important:
    We expose both:
    - items: original canonical key
    - tech_items: template-safe alias

    In DOCX/Jinja templates, dict.items can collide with the built-in dict method,
    so template code should prefer tech.tech_items instead of tech.items.
    """
    technologies = _copy_list_of_dicts(ctx.get("technologies", []))

    prepared: list[dict[str, Any]] = []
    for group in technologies:
        group_key = str(group.get("group_key", "other") or "other")
        group_label = str(group.get("group_label", "") or "")
        items = _to_str_list(group.get("items", []))

        prepared.append({
            "group_key": group_key,
            "group_label": group_label or group_key.replace("_", " ").title(),
            "items": items,
            "tech_items": items,
        })

    prepared.sort(
        key=lambda group: ORDER_INDEX.get(group.get("group_key", "other"), 999)
    )

    ctx["technologies"] = prepared


def _prepare_projects(ctx: dict[str, Any]) -> None:
    project_experience = _copy_list_of_dicts(ctx.get("project_experience", []))

    prepared: list[dict[str, Any]] = []
    for project in project_experience:
        project_target = _safe_nested_dict(project.get("project_target"))

        prepared_project = {
            "period_label": str(project.get("period_label", "") or ""),
            "project_name": str(project.get("project_name", "") or ""),
            "project_start": str(project.get("project_start", "") or ""),
            "project_end": str(project.get("project_end", "") or ""),
            "industry": _to_str_list(project.get("industry", [])),
            "project_target": {
                "description": str(project_target.get("description", "") or "")
            },
            "responsibilities": _to_str_list(project.get("responsibilities", [])),
            "roles": _to_str_list(project.get("roles", [])),
            "skills": _to_str_list(project.get("skills", [])),
        }

        if not prepared_project["period_label"]:
            prepared_project["period_label"] = make_period_label(
                prepared_project["project_start"],
                prepared_project["project_end"],
            )

        prepared.append(prepared_project)

    def project_sort_key(project: dict[str, Any]) -> tuple[str, str]:
        project_end = project.get("project_end") or "9999-99"
        project_start = project.get("project_start") or ""
        return project_end, project_start

    prepared.sort(key=project_sort_key, reverse=True)
    ctx["project_experience"] = prepared


def _prepare_simple_lists(ctx: dict[str, Any]) -> None:
    for key in [
        "academic_qualifications",
        "main_skills",
        "languages_spoken",
        "certifications",
        "industries",
    ]:
        if key not in ctx:
            continue

        value = ctx.get(key)

        if key in {"main_skills", "industries"}:
            ctx[key] = _to_str_list(value)
        elif isinstance(value, list):
            ctx[key] = value
        else:
            ctx[key] = []


def _prepare_context(cv_json: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare a safe rendering context for the DOCX template.
    """
    context = dict(cv_json or {})

    _prepare_simple_lists(context)
    _prepare_work_experience(context)
    _prepare_technologies(context)
    _prepare_projects(context)

    # Keep context clean even if upstream accidentally injects contact-like keys.
    for forbidden_key in ("email", "phone", "mobile", "address", "linkedin", "website", "contact"):
        context.pop(forbidden_key, None)

    return context


def render_company_docx(cv_json: dict[str, Any], template_version: str = "company-v1") -> bytes:
    """
    Render the configured company DOCX template using the provided CV JSON.
    Returns the rendered document as bytes.
    """
    template_path = _resolve_template_path(template_version)
    context = _prepare_context(cv_json)

    template = DocxTemplate(str(template_path))
    template.render(context)

    buffer = BytesIO()
    template.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()