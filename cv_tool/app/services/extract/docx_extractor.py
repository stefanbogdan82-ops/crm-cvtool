from docx import Document

def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    parts: list[str] = []
    for p in doc.paragraphs:
        txt = (p.text or "").strip()
        if txt:
            parts.append(txt)
    return "\n".join(parts).strip()
