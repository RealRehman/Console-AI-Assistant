from docx import Document
from pypdf import PdfReader

_document_text = ""


def load_document(file_path):
    global _document_text

    if file_path.lower().endswith(".pdf"):

        reader = PdfReader(file_path)

        pages = [
            (page.extract_text() or "").strip()
            for page in reader.pages
        ]

        _document_text = "\n".join(p for p in pages if p)

    else:

        document = Document(file_path)

        paragraphs = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                paragraphs.append(text)

        _document_text = "\n".join(paragraphs)


def get_document_context():
    return _document_text


def has_document():
    return bool(_document_text.strip())


def clear_document():
    global _document_text
    _document_text = ""
