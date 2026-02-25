from pathlib import Path
import PyPDF2


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract all text content from a PDF file.

    Reads the PDF at the specified path and concatenates the text from all pages
    into a single string, separating pages with newline characters.

    Args:
        pdf_path (Path): Path to the PDF file to be read.

    Returns:
        str: The combined text content of the PDF. Empty pages are skipped.
    """
    reader = PyPDF2.PdfReader(str(pdf_path))
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return '\n'.join(text)
