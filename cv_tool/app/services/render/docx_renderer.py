from pathlib import Path
from docxtpl import DocxTemplate
from app.core.config import settings

def render_company_docx(cv_json: dict, template_version: str = "company-v1") -> bytes:
    template_path = Path(settings.template_dir) / f"{template_version}.docx"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    tpl = DocxTemplate(str(template_path))

    # Context mapping (keep it simple; expand later)
    context = cv_json.copy()

    tpl.render(context)

    # Save to bytes
    from io import BytesIO
    buf = BytesIO()
    tpl.save(buf)
    return buf.getvalue()
