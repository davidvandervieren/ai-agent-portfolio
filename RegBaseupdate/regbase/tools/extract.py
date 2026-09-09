"""Turn downloaded HTML/PDF/DOCX into citable plain text.

Output convention (consumed by build_index.py):
  * Markdown-ish text, one `## ` heading per structural heading found.
  * A `<!-- heading-path: A > B > C -->` marker before each section so a chunk
    can rebuild the citation trail even after it is split out of context.
  * A YAML front-matter block carrying the provenance the indexer needs.

Extraction is deliberately conservative: it drops navigation chrome but never
rewrites regulatory language, because the text is used to produce citations.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional

# Chrome that shows up on virtually every municipal code site and carries no
# regulatory content. Matched against tag/class/id, case-insensitively.
_CHROME_SELECTORS = [
    "script", "style", "noscript", "svg", "form", "iframe",
    "nav", "header", "footer", "aside",
]
_CHROME_PATTERNS = re.compile(
    r"(nav|menu|breadcrumb|sidebar|footer|header|banner|cookie|consent|"
    r"skip-link|search-box|social|share|print-button|toolbar|pagination|"
    r"back-to-top|site-tools|utility-bar)",
    re.I,
)

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _collapse(text: str) -> str:
    text = text.replace("\xa0", " ").replace("​", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_text(html: str, base_url: str = "") -> str:
    """Strip chrome, keep headings and body text, emit heading-path markers."""
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    for sel in _CHROME_SELECTORS:
        for el in soup.find_all(sel):
            el.decompose()
    for el in soup.find_all(attrs={"class": _CHROME_PATTERNS}):
        el.decompose()
    for el in soup.find_all(attrs={"id": _CHROME_PATTERNS}):
        el.decompose()
    for el in soup.find_all(attrs={"role": re.compile(r"^(navigation|banner|search)$", re.I)}):
        el.decompose()

    main = (soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find("article")
            or soup.find(id=re.compile(r"^(content|main|body)", re.I))
            or soup.body
            or soup)

    out: list[str] = []
    path: list[str] = []

    def flush_path() -> None:
        if path:
            out.append(f"<!-- heading-path: {' > '.join(path)} -->")

    for el in main.descendants:
        name = getattr(el, "name", None)
        if name in _HEADING_TAGS:
            level = int(name[1])
            text = _collapse(el.get_text(" ", strip=True))
            if not text:
                continue
            del path[level - 1:]
            path.append(text)
            out.append("")
            flush_path()
            out.append(f"{'#' * min(level, 6)} {text}")
        elif name in ("p", "li", "dd", "dt", "blockquote", "pre"):
            text = _collapse(el.get_text(" ", strip=True))
            if text:
                out.append(text)
        elif name == "table":
            rows = []
            for tr in el.find_all("tr"):
                cells = [_collapse(td.get_text(" ", strip=True))
                         for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                out.append("")
                out.extend(rows)
                out.append("")

    text = _collapse("\n".join(out))
    if len(text) < 200:
        # Layouts we did not understand: fall back to the whole document rather
        # than silently indexing an empty page.
        text = _collapse(soup.get_text("\n", strip=True))
    return text


def pdf_to_text(data: bytes) -> str:
    """pypdf first (fast); pdfminer.six as the fallback for awkward layouts."""
    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for i, page in enumerate(reader.pages, 1):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                pages.append(f"<!-- page: {i} -->\n{t}")
        text = "\n\n".join(pages)
    except Exception:
        text = ""

    if len(text.strip()) < 200:
        try:
            from pdfminer.high_level import extract_text as _pm

            text = _pm(io.BytesIO(data)) or text
        except Exception:
            pass
    return _collapse(text)


def docx_to_text(data: bytes) -> str:
    """Minimal OOXML reader — no python-docx dependency."""
    import zipfile
    import xml.etree.ElementTree as ET

    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        root = ET.fromstring(z.read("word/document.xml"))
    except Exception:
        return ""
    body = root.find(W + "body")
    if body is None:
        return ""

    def cell_text(el) -> str:
        return "".join(t.text or "" for t in el.iter(W + "t"))

    out: list[str] = []
    for el in body:
        tag = el.tag.replace(W, "")
        if tag == "p":
            style = el.find(f"{W}pPr/{W}pStyle")
            s = cell_text(el).strip()
            if not s:
                continue
            val = style.get(W + "val", "") if style is not None else ""
            m = re.match(r"Heading(\d)", val or "")
            out.append(f"{'#' * min(int(m.group(1)), 6)} {s}" if m else s)
        elif tag == "tbl":
            for tr in el.findall(W + "tr"):
                cells = [cell_text(tc).strip().replace("\n", " ")
                         for tc in tr.findall(W + "tc")]
                if any(cells):
                    out.append(" | ".join(cells))
    return _collapse("\n".join(out))


_EXT_BY_CT = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/zip": ".zip",
    "text/plain": ".txt",
    "application/json": ".json",
}


def guess_ext(content_type: str, url: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in _EXT_BY_CT:
        return _EXT_BY_CT[ct]
    tail = Path(url.split("?")[0]).suffix.lower()
    if tail in (".pdf", ".html", ".htm", ".doc", ".docx", ".txt", ".xml", ".json", ".zip"):
        return ".html" if tail == ".htm" else tail
    return ".bin"


def extract(data: bytes, ext: str, url: str = "") -> str:
    """Dispatch on file extension. Returns '' when the format is unsupported."""
    if ext == ".pdf":
        return pdf_to_text(data)
    if ext in (".html", ".htm", ".xml"):
        try:
            return html_to_text(data.decode("utf-8", errors="replace"), url)
        except Exception:
            return ""
    if ext == ".docx":
        return docx_to_text(data)
    if ext in (".txt", ".json"):
        return _collapse(data.decode("utf-8", errors="replace"))
    return ""


def front_matter(**fields) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if v is None or v == "":
            continue
        s = str(v).replace("\n", " ")
        lines.append(f'{k}: "{s}"' if any(c in s for c in ':#"') else f"{k}: {s}")
    lines.append("---")
    return "\n".join(lines)
