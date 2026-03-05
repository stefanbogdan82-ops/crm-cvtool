import fitz  # PyMuPDF

def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    chunks: list[str] = []
    for page in doc:
        txt = page.get_text("text") or ""
        txt = txt.strip()
        if txt:
            chunks.append(txt)
    return "\n\n".join(chunks).strip()

def looks_like_scanned_pdf(extracted_text: str) -> bool:
    # MVP heuristic
    return len(extracted_text.strip()) < 200
