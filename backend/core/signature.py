import puremagic

# Allowed magic extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".zip"}


def validate_file_signature(content: bytes, filename: str) -> str:
    """Validate file bytes against allowed magic headers. Returns matched extension or raises ValueError."""
    matches = None
    try:
        matches = puremagic.magic_string(content)
    except Exception:
        pass

    if matches:
        # Sort matches by confidence descending
        matches.sort(key=lambda x: x.confidence, reverse=True)
        matched_ext = matches[0].extension.lower()
        
        # DOCX is packaged as a ZIP, so puremagic might match it as .zip or .docx
        if matched_ext in {".zip", ".docx"} and filename.lower().endswith(".docx"):
            import zipfile
            import io
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    if "word/document.xml" not in z.namelist():
                        raise ValueError("Invalid DOCX structure. Missing word/document.xml.")
            except Exception as exc:
                raise ValueError(f"Invalid DOCX file structure: {exc}")
            return ".docx"
        elif matched_ext in ALLOWED_EXTENSIONS:
            return matched_ext

    # Fallback to plain text validation (TXT files have no magic binary header)
    try:
        content.decode("utf-8")
        if filename.lower().endswith(".txt"):
            return ".txt"
    except UnicodeDecodeError:
        pass

    raise ValueError("Invalid file signature. Only PDF, DOCX, and TXT are allowed.")


def extract_text_from_docx_bytes(content: bytes) -> str:
    """Extract text from docx bytes without external dependencies."""
    import io
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_content = z.read("word/document.xml")
            root = ET.fromstring(xml_content)
            paragraphs = []
            for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                p_text = []
                for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if t.text:
                        p_text.append(t.text)
                paragraphs.append("".join(p_text))
            return "\n".join(paragraphs).strip()
    except Exception as exc:
        raise ValueError(f"Failed to extract text from DOCX file: {exc}")


def extract_text_from_file_bytes(content: bytes, filename: str) -> str:
    """Validate signature and extract text based on the file type."""
    from pypdf import PdfReader
    import io
    
    matched_ext = validate_file_signature(content, filename)
    
    if matched_ext == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif matched_ext == ".docx":
        text = extract_text_from_docx_bytes(content)
    elif matched_ext == ".txt":
        text = content.decode("utf-8")
    else:
        raise ValueError(f"Unsupported file signature extension: {matched_ext}")
        
    return text

