# app/services/render/docx_renderer.py

from pathlib import Path
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
ORDER_INDEX = {k: i for i, k in enumerate(TECH_GROUP_ORDER)}

def _prepare_context(cv_json: dict) -> dict:
    ctx = dict(cv_json)

    # 1) Work experience compact: ensure period_label, optional sorting
    we = list(ctx.get("work_experience_compact", []))
    for item in we:
        if not item.get("period_label"):
            item["period_label"] = make_period_label(item.get("start_date"), item.get("end_date"))
        # normalize end_date presentation in template via period_label; template uses period_label already

    # Sort by start_date desc when present
    def we_sort_key(x):
        sd = x.get("start_date") or ""
        return sd
    we.sort(key=we_sort_key, reverse=True)
    ctx["work_experience_compact"] = we[:6]  # enforce max 6 like your template

    # 2) Technologies: enforce ordering by group_key
    tech = list(ctx.get("technologies", []))
    tech.sort(key=lambda g: ORDER_INDEX.get(g.get("group_key", "other"), 999))
    ctx["technologies"] = tech

    # 3) Projects: ensure period_label exists, sort by project_end desc then start desc
    pe = list(ctx.get("project_experience", []))
    for p in pe:
        if not p.get("period_label"):
            p["period_label"] = make_period_label(p.get("project_start"), p.get("project_end"))

    def proj_sort_key(p):
        endd = p.get("project_end") or "9999-99"  # ongoing first
        startd = p.get("project_start") or ""
        return (endd, startd)

    pe.sort(key=proj_sort_key, reverse=True)
    ctx["project_experience"] = pe

    # 4) Enforce no contact keys sneaking into template context
    # (template won’t reference them, but we keep it clean)
    # Your schema already omits them; validation also forbids them.

    return ctx

def render_company_docx(cv_json: dict, template_version: str = "company-v1") -> bytes:
    template_path = Path(settings.template_dir) / f"{template_version}.docx"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    tpl = DocxTemplate(str(template_path))
    context = _prepare_context(cv_json)
    tpl.render(context)

    from io import BytesIO
    buf = BytesIO()
    tpl.save(buf)
    return buf.getvalue()
