"""
parser.py  ── v3

---------
1. PDF normalisation: pdfplumber x=tolerance grouping so bullets/dashes
   that get split across columns are rejoined correctly.
2. DOCX bullet extraction: reads actual list paragraphs, not just text chars.
3. Keyword extraction uses only MEANINGFUL single-term skills/roles, not
   noisy bigrams, so keyword_match_ratio is honest.
4. section detection is line-level and case-insensitive.
5. action_verb_count counts DISTINCT verbs (unique) not raw occurrences,
   giving a fairer single-page vs multi-page comparison.
6. word_count is capped-normalised: resumes 300-900 words all get a neutral
   score; the CART is not penalised by minor length differences.
7. NEW: extract_skills_from_text() / extract_all_info() now accept an
   optional `known_skills` list (the live skills_master vocabulary from the
   DB), so a resume can be scored against every HR-curated skill, not just
   the ones hardcoded in DEFAULT_KNOWN_SKILLS below. Falls back to
   DEFAULT_KNOWN_SKILLS when no known_skills list is supplied, so existing
   callers that don't pass it keep working unchanged.
"""

import re
import os
from datetime import datetime

import pdfplumber
import docx as python_docx


# ═══════════════════════════════════════════════════════════════════════════════
# Text extraction
# ═══════════════════════════════════════════════════════════════════════════════

def _clean(raw: str) -> str:
    """
    Normalise whitespace so PDF and DOCX output are comparable.
    Also converts PDF CID glyph references to their actual characters:
      (cid:127) → bullet  •
      (cid:146) → apostrophe  '
      (cid:148) → closing quote  "
      (cid:149) → bullet  •
      (cid:150) → en-dash  –
      (cid:151) → em-dash  —
    """
    # cover all common glyph encodings
    cid_map = {
        "(cid:127)": "• ",   # bullet
        "(cid:149)": "• ",   # bullet (alt encoding)
        "(cid:146)": "'",    # right single quotation
        "(cid:147)": "\u201c", # left double quote
        "(cid:148)": "\u201d", # right double quote
        "(cid:150)": "\u2013", # en dash
        "(cid:151)": "\u2014", # em dash
        "(cid:160)": " ",    # non-breaking space
        "(cid:183)": "• ",   # middle dot / bullet
    }
    text = raw
    for cid, replacement in cid_map.items():
        text = text.replace(cid, replacement)

    # Replace any remaining (cid:NNN) with a space so they don't corrupt words
    text = re.sub(r"\(cid:\d+\)", " ", text)

    # ── Private-Use-Area glyph normalisation ────────────────────────────────
    # Word/LibreOffice render bullet lists using the Wingdings/Symbol fonts.
    # When such a PDF is text-extracted, pdfplumber decodes those glyphs to
    # their *font* codepoint, which lands in the Unicode Private Use Area
    # (U+F000–U+F8FF) rather than becoming "•" or a "(cid:N)" string. Left
    # unmapped, these glyphs are invisible to BULLET_RE, so PDFs silently
    # lose their bullet_count vs. the same resume saved as DOCX. Map the
    # common Wingdings/Symbol bullet codepoints explicitly, then catch any
    # other PUA glyph that starts a line (almost always a bullet/marker).
    pua_bullet_map = {
        "\uf0b7": "• ",  # Symbol font bullet
        "\uf0a7": "• ",  # Wingdings square bullet
        "\uf06f": "• ",  # Wingdings open circle bullet
        "\uf0d8": "• ",  # Wingdings arrow bullet
        "\uf0fc": "• ",  # Wingdings checkmark bullet
        "\uf02d": "• ",  # Wingdings dash bullet
        "\uf0a0": "• ",  # Wingdings filled square
        "\uf0e8": "• ",  # Wingdings arrow
    }
    for glyph, replacement in pua_bullet_map.items():
        text = text.replace(glyph, replacement)
    # Catch-all: any other leftover Private-Use-Area glyph at the start of a
    # line is almost certainly an unmapped bullet/marker character — treat it
    # the same way so the bullet counter stays format-independent.
    text = re.sub(r"(?m)^([ \t]*)[\uE000-\uF8FF]\s*", r"\1• ", text)
    # Any remaining PUA glyphs elsewhere in the line: drop them rather than
    # let them corrupt word_count / keyword matching.
    text = re.sub(r"[\uE000-\uF8FF]", "", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract text from PDF.  Uses word-level bounding boxes to detect
    bullet-like characters that would otherwise be separated from their line.
    """
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            raw = page.extract_text(layout=False) or ""
            pages.append(raw)
    return _clean("\n".join(pages))


def _iter_block_items(parent):
    """
    Yield each paragraph and table child of `parent` in actual document
    order (top to bottom, as Word would render it).

    BUGFIX: doc.paragraphs (used previously) ONLY returns top-level
    paragraphs — it silently skips any text that lives inside a table.
    Tables are an extremely common resume pattern (skills grids, contact
    info blocks, even whole two-column layouts built as a table), so any
    such resume saved as .docx was losing that content entirely while the
    same resume saved as .pdf kept it (pdfplumber reads visible text
    regardless of whether it sits in a table). That alone could swing a
    resume from "Weak Fit" to "Moderate/Strong Fit" depending on format.
    This walks the underlying XML body so paragraphs AND tables are both
    captured, in the order they actually appear.
    """
    from docx.oxml.ns import qn
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph

    if isinstance(parent, python_docx.document.Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        parent_elm = parent

    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _table_to_lines(table) -> list:
    """
    Flatten a DOCX table into text lines. Each row becomes one line with
    cells joined by " | " (mirrors how a resume's skills/contact table
    would read visually), and any paragraph-level bullet formatting inside
    a cell is preserved. Nested tables (rare, but happens with some
    templates) are recursed into.
    """
    lines = []
    for row in table.rows:
        cell_texts = []
        for cell in row.cells:
            # A cell can contain multiple paragraphs and/or nested tables.
            for item in _iter_block_items(cell):
                from docx.table import Table as _Table
                if isinstance(item, _Table):
                    lines.extend(_table_to_lines(item))
                    continue
                try:
                    text = item.text
                except Exception:
                    continue
                if not text.strip():
                    continue
                if _docx_has_bullet(item) and not text.lstrip().startswith(
                    ("•", "·", "▪", "-", "*")
                ):
                    text = "• " + text
                cell_texts.append(text.strip())
        if cell_texts:
            # Plain whitespace, not " | " — a literal pipe character gets
            # counted as its own "word" by word_count's simple split(),
            # which would inflate DOCX word counts relative to the same
            # table read out of a PDF (pdfplumber just emits column gaps
            # as spaces, no separator character). Multiple spaces collapse
            # to one in _clean(), so this stays visually row-like without
            # skewing the count.
            lines.append("   ".join(cell_texts))
    return lines


def _docx_has_bullet(para) -> bool:
    """Return True if this DOCX paragraph is a list item. Fully guarded."""
    try:
        pPr = para._p.pPr
        if pPr is not None and pPr.numPr is not None:
            return True
    except Exception:
        pass
    try:
        style = para.style
        if style is not None:
            style_name = (style.name or "").lower()
            if "list" in style_name or "bullet" in style_name:
                return True
    except Exception:
        pass
    try:
        t = para.text.lstrip()
        return bool(t and t[0] in "•·▪▸‡–-*")
    except Exception:
        return False


def extract_text_from_docx(filepath: str) -> str:
    """
    Extract DOCX text in real document order, including table content,
    and inject a '• ' prefix for list paragraphs so the bullet counter
    works the same way as it does on PDF text.
    """
    from docx.table import Table

    doc = python_docx.Document(filepath)
    lines = []
    for item in _iter_block_items(doc):
        if isinstance(item, Table):
            lines.extend(_table_to_lines(item))
            continue
        try:
            text = item.text
        except Exception:
            continue
        if not text.strip():
            lines.append("")
            continue
        try:
            is_bullet = _docx_has_bullet(item)
        except Exception:
            is_bullet = False
        if is_bullet and not text.lstrip().startswith(("•", "·", "▪", "-", "*")):
            text = "• " + text
        lines.append(text)
    return _clean("\n".join(lines))


def extract_text_from_doc(filepath: str) -> str:
    """
    Legacy binary .doc files are NOT docx/zip files — python-docx cannot
    open them (it would raise a "not a zip file" / BadZipFile error, or
    silently return garbage). Convert to .docx with LibreOffice headless
    first, then reuse the normal DOCX path so .doc gets the exact same
    bullet/section handling as .docx instead of producing a different,
    lower-quality result.
    """
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "docx",
                 "--outdir", tmpdir, filepath],
                check=True, capture_output=True, timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError) as e:
            raise ValueError(
                "Could not convert legacy .doc file. Please re-save it as "
                ".docx or .pdf and re-upload."
            ) from e

        base = os.path.splitext(os.path.basename(filepath))[0]
        converted = os.path.join(tmpdir, base + ".docx")
        if not os.path.exists(converted):
            raise ValueError(
                "Could not convert legacy .doc file. Please re-save it as "
                ".docx or .pdf and re-upload."
            )
        return extract_text_from_docx(converted)


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext == ".docx":
        return extract_text_from_docx(filepath)
    elif ext == ".doc":
        return extract_text_from_doc(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ═══════════════════════════════════════════════════════════════════════════════
# Regex primitives
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s.\-]?)?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}"
)
DATE_RE = re.compile(
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}"
    r"|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
    re.IGNORECASE,
)
DATE_RANGE_RE = re.compile(
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?"
    r"\d{4}\s*[-–—to]+\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?"
    r"(?:\d{4}|present|current|now)\b",
    re.IGNORECASE,
)
# Catches •  ·  ▪  ▸  –  -  *  or digit.  at the START of a line
BULLET_RE = re.compile(
    r"^[ \t]*(?:[•·▪▸\u2022\u2023\u25aa]|\-|\*|\d+[\.\)])\s+\S",
    re.MULTILINE,
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
DECLARED_EXPERIENCE_RE = re.compile(
    r"\b(?:over\s+|more\s+than\s+|at\s+least\s+)?(\d+(?:\.\d+)?)\+?\s*"
    r"(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|work\s+)?experience\b",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"\b\d+\s[\w\s]+(?:St(?:reet)?|Ave(?:nue)?|Blvd|Rd|Road|Lane|Dr(?:ive)?|"
    r"Lot|Block|Brgy|Barangay)[\w\s,\.]*"
    r"(?:City|Province|Manila|Quezon|Pasig|Makati|Taguig|Pasay|Caloocan|"
    r"Marikina|New York|Austin|California|Texas|Metro Manila)[\w\s,\.]*",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Section detection
# ═══════════════════════════════════════════════════════════════════════════════

_SECTION_PATTERNS = {
    "contact":    [r"\bcontact\b", r"\bphone\b", r"\bemail\b"],
    "summary":    [r"\bsummary\b", r"\bobjective\b", r"\bprofile\b",
                   r"\bprofessional\s+summary\b", r"\bcareer\s+summary\b"],
    "experience": [r"\bexperience\b", r"\bemployment\b", r"\bwork\s+history\b",
                   r"\bwork\s+experience\b", r"\bprofessional\s+experience\b",
                   r"\bcareer\s+history\b", r"\bwork\s+experiences\b"],
    "education":  [r"\beducation\b", r"\bacademic\b", r"\bschooling\b",
                   r"\beducational\s+background\b"],
    "skills":     [r"\bskills\b", r"\btechnical\s+skills\b",
                   r"\bcore\s+competencies\b", r"\bcompetencies\b",
                   r"\bkey\s+skills\b", r"\bqualifications\b"],
}


def _collapse_spaced_heading(line: str) -> str:
    """
    PDF fonts sometimes letter-space section headings so that pdfplumber
    extracts them with spaces inserted mid-word, e.g.:
        'PRO FESSI O NA L SUM MA RY'  ->  'PROFESSIONAL SUMMARY'
        'W O RK EXPERI ENCE'          ->  'WORK EXPERIENCE'
        'SKI LLS'                     ->  'SKILLS'
        'EDUCA TI O N'                ->  'EDUCATION'

    Approach: if the line is short and all-uppercase, collapse ALL spaces
    to get a single run of letters, then re-insert spaces by trying to match
    known section keywords (longest-match). If no known keyword matches, keep
    the raw collapsed string (it is still matchable by the section patterns
    because the patterns don't require spaces: e.g. r'\bsummary\b' won't
    fire, but we add a no-space variant in _SECTION_PATTERNS via this helper).
    """
    alpha = re.sub(r"[^A-Za-z]", "", line)
    if not alpha or len(alpha) < 4:
        return line
    upper_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
    if upper_ratio < 0.85:
        return line

    # Collapse all spaces in the uppercase run
    collapsed = re.sub(r"\s+", "", line)   # e.g. "PROFESSIONALSUMMARY"

    # Try to recover known section words from the collapsed string
    # (in priority / longest-first order)
    _KNOWN_WORDS = [
        "PROFESSIONAL", "SUMMARY", "EXPERIENCE", "EDUCATION",
        "SKILLS", "WORK", "HISTORY", "EMPLOYMENT", "CAREER",
        "CONTACT", "PROFILE", "PERSONAL", "REFERENCES", "OBJECTIVE",
        "ACADEMIC", "BACKGROUND", "COMPETENCIES", "QUALIFICATIONS",
    ]
    remainder = collapsed.upper()
    out_tokens = []
    while remainder:
        matched = False
        for w in sorted(_KNOWN_WORDS, key=len, reverse=True):
            if remainder.startswith(w):
                out_tokens.append(w)
                remainder = remainder[len(w):]
                matched = True
                break
        if not matched:
            # consume one character to avoid infinite loop
            if out_tokens:
                out_tokens[-1] = out_tokens[-1] + remainder[0]
            else:
                out_tokens.append(remainder[0])
            remainder = remainder[1:]
    return " ".join(out_tokens)


def detect_sections(text: str) -> dict:
    found = {k: False for k in _SECTION_PATTERNS}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            continue
        # Collapse letter-spaced PDF headings before matching
        collapsed = _collapse_spaced_heading(stripped)
        stripped_lower = collapsed.lower()
        for section, patterns in _SECTION_PATTERNS.items():
            if found[section]:
                continue
            for pat in patterns:
                if re.search(pat, stripped_lower):
                    found[section] = True
                    break
    return found


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword matching  (meaningful terms only)
# ═══════════════════════════════════════════════════════════════════════════════

# FALLBACK ONLY when no `known_skills` list is supplied by the caller (the
# caller is expected to pass in the live skills_master table contents from
# the DB — see routes/applicants.py's _all_known_skills() /
# _job_required_skills()). A resume mentioning a real, HR-curated skill
# that simply isn't on this hardcoded list would otherwise never be
# detected, no matter what job it was screened against.
DEFAULT_KNOWN_SKILLS = [
    # Languages
    "Python","Java","JavaScript","TypeScript","C","C++","C#","Ruby","PHP",
    "Swift","Kotlin","Go","R","MATLAB","Scala",
    # Web
    "HTML","CSS","React","Angular","Vue","Node.js","Django","Flask","Laravel",
    "Spring","REST","GraphQL",
    # Data / BI
    "SQL","MySQL","PostgreSQL","MongoDB","SQLite","Oracle","NoSQL",
    "Excel","Tableau","Power BI","Pandas","NumPy","Spark","Hadoop",
    "SPSS","SAS","Looker","Google Analytics","Data Analysis","Data Visualization",
    "Dashboard","KPI","Reporting",
    # Cloud / DevOps
    "AWS","Azure","GCP","Docker","Kubernetes","Jenkins","Terraform",
    "CI/CD","Linux","Git","GitHub","Ansible",
    # Project / process
    "Agile","Scrum","Kanban","Jira","Confluence","Trello","SDLC",
    "SAP","ERP","CRM","Salesforce",
    # Soft skills
    "Leadership","Communication","Problem Solving","Teamwork",
    "Time Management","Critical Thinking","Adaptability",
    # ML / AI
    "Machine Learning","Deep Learning","NLP","TensorFlow","PyTorch",
    # Security / Networking
    "Cybersecurity","Networking",
    # Design
    "Photoshop","Figma","AutoCAD","Sketch",
    # BA-specific
    "Business Analysis","Requirements Gathering","Process Improvement",
    "Stakeholder Management","UAT","User Acceptance Testing",
    "Workflow Optimization","System Design","Technical Specifications",
    "Project Management","Risk Management","Change Management",
    "Gap Analysis","Business Requirements","Functional Specifications",
    "Use Cases","User Stories","Process Mapping","BPMN",
    "Business Intelligence","Data Governance",
]

# Backward-compat alias — this module (and extract_keywords_from_job_desc
# below) previously only ever knew this list as `KNOWN_SKILLS`. Keep the
# old name pointing at the same list so nothing else in the codebase that
# imports KNOWN_SKILLS directly breaks.
KNOWN_SKILLS = DEFAULT_KNOWN_SKILLS

COMMON_ACTION_VERBS = [
    "managed","led","developed","built","designed","implemented","created",
    "improved","increased","reduced","achieved","launched","coordinated",
    "analyzed","optimized","delivered","executed","facilitated","streamlined",
    "established","maintained","collaborated","supported","conducted",
    "evaluated","identified","resolved","trained","mentored","negotiated",
    "presented","documented","planned","monitored","assessed","deployed",
    "integrated","automated","migrated","architected","spearheaded",
    "oversaw","supervised","directed",
]


def _simple_stem(word: str) -> str:
    w = word.lower()
    for suffix in ("ing","tion","tions","ed","er","ers","es","s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: len(w) - len(suffix)]
    return w


def count_keyword_matches(text: str, keywords: list) -> dict:
    lowered = text.lower()
    resume_stems = {_simple_stem(w) for w in re.findall(r"[a-zA-Z]{3,}", text)}
    result = {}
    for kw in keywords:
        kw_clean = kw.lower().strip()
        exact = len(re.findall(r"\b" + re.escape(kw_clean) + r"\b", lowered))
        if exact > 0:
            result[kw] = exact
        else:
            kw_stem = _simple_stem(kw_clean)
            result[kw] = 1 if kw_stem in resume_stems else 0
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Job-description keyword extractor  (LAST-RESORT FALLBACK ONLY)
# ═══════════════════════════════════════════════════════════════════════════════
#
# DEPRECATED as a primary source. This regex-guesses a job's required
# skills from its free-text description (and, failing that, from a
# hardcoded role-name → implied-skills map). It exists ONLY as a fallback
# for a job posting that has no rows yet in the real, HR-curated
# job_required_skills / skills_master DB tables — routes/applicants.py's
# _job_required_skills() always tries the real DB table first and only
# calls this function if that comes back empty. Do not call this directly
# as your source of "what skills does this job need" — query
# job_required_skills instead.

# Skills/roles that are actually checkable in a resume
_CHECKABLE_TERMS = [s.lower() for s in DEFAULT_KNOWN_SKILLS] + [
    "microsoft office","ms office","google workspace","g suite",
    "database","api","software development","web development",
    "testing","quality assurance","qa","project management",
    "business analyst","system analyst","data analyst","developer",
    "engineer","architect","manager","coordinator","specialist",
]

# Role → implied skill keywords (used when job description text is thin)
_ROLE_SKILL_MAP = {
    "software developer":   ["Python","JavaScript","SQL","HTML","CSS","Git","REST",
                             "Agile","MySQL","Problem Solving","software development",
                             "web development","Testing","SDLC","GitHub"],
    "developer":            ["Python","JavaScript","SQL","Git","Agile","SDLC","Testing"],
    "business analyst":     ["SQL","Excel","Business Analysis","Requirements Gathering",
                             "Process Improvement","Stakeholder Management","UAT",
                             "Agile","Jira","Tableau","Power BI","SDLC",
                             "Workflow Optimization","Communication","Data Analysis"],
    "system analyst":       ["SQL","Business Analysis","Requirements Gathering",
                             "System Design","Technical Specifications","UAT",
                             "Process Mapping","SDLC","Documentation"],
    "data analyst":         ["SQL","Python","Excel","Tableau","Power BI","Data Analysis",
                             "Data Visualization","Reporting","Dashboard","KPI"],
    "project manager":      ["Agile","Scrum","Jira","Project Management","Risk Management",
                             "Stakeholder Management","Communication","Leadership"],
    "web developer":        ["HTML","CSS","JavaScript","React","Node.js","SQL","Git",
                             "REST","Testing","GitHub"],
    "junior developer":     ["Python","JavaScript","HTML","CSS","SQL","Git","Agile"],
}


def extract_keywords_from_job_desc(description: str, job_name: str = "") -> list[str]:
    """
    FALLBACK ONLY — see module note above. Pull known-skill / role-name
    terms from the job description text by regex, then (if still thin)
    supplement with role-based implied skills looked up from the job name.
    Returns a deduplicated list (original casing from DEFAULT_KNOWN_SKILLS).

    Prefer routes/applicants.py's _job_required_skills(), which reads the
    real HR-curated job_required_skills/skills_master rows instead of
    guessing.
    """
    lower_desc = (description or "").lower()
    found = []

    # Match multi-word skills first (longer matches first)
    for skill in sorted(DEFAULT_KNOWN_SKILLS, key=len, reverse=True):
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lower_desc):
            found.append(skill)

    # Also pick up single-word checkable terms not already found
    found_lower = {x.lower() for x in found}
    for term in _CHECKABLE_TERMS:
        if term.lower() not in found_lower:
            if re.search(r"\b" + re.escape(term) + r"\b", lower_desc):
                found.append(term.title() if " " not in term else term)
                found_lower.add(term.lower())

    # If still thin, supplement from role-name map
    if len(found) < 5 and job_name:
        jn_lower = job_name.lower().strip()
        for role_key, implied in _ROLE_SKILL_MAP.items():
            if role_key in jn_lower or jn_lower in role_key:
                for skill in implied:
                    if skill.lower() not in found_lower:
                        found.append(skill)
                        found_lower.add(skill.lower())
                break   # use the first matching role only

    # Deduplicate preserving order
    seen, out = set(), []
    for item in found:
        if item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)

    return out


# ═══════════════════════════════════════════════════════════════════════════════
# ATS feature extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_ats_features(text: str, job_keywords: list = None) -> dict:
    """
    All counts use normalised text so PDF and DOCX score identically
    for the same resume content. `job_keywords` should be the job's real
    required-skills list (from job_required_skills/skills_master) —
    callers get this via routes/applicants.py's _job_required_skills().
    """
    job_keywords = job_keywords or []
    sections     = detect_sections(text)

    word_count       = len(text.split())
    has_email        = bool(EMAIL_RE.search(text))
    has_phone        = bool(PHONE_RE.search(text))
    bullet_count     = len(BULLET_RE.findall(text))
    date_range_count = len(DATE_RANGE_RE.findall(text))

    lower = text.lower()
    # Count UNIQUE action verbs (not total occurrences) → format-independent
    action_verb_count = sum(
        1 for v in COMMON_ACTION_VERBS
        if re.search(r"\b" + v + r"\b", lower)
    )

    suspicious_table_lines = sum(
        1 for line in text.splitlines()
        if len(re.findall(r"\t| {4,}", line)) >= 2
    )

    keyword_hits        = count_keyword_matches(text, job_keywords)
    keyword_hit_count   = sum(1 for v in keyword_hits.values() if v > 0)
    keyword_total_count = len(job_keywords)
    keyword_match_ratio = (
        keyword_hit_count / keyword_total_count if keyword_total_count else 0.0
    )

    sections_present = sum([
        sections["contact"] or has_email or has_phone,
        sections["summary"],
        sections["experience"],
        sections["education"],
        sections["skills"],
    ])

    # Experience depth: how many distinct job blocks appear
    experience_depth = len(DATE_RANGE_RE.findall(text))

    return {
        "word_count":              word_count,
        "bullet_count":            bullet_count,
        "date_range_count":        date_range_count,
        "action_verb_count":       action_verb_count,
        "suspicious_table_lines":  suspicious_table_lines,
        "has_contact_section":     sections["contact"] or has_email or has_phone,
        "has_summary_section":     sections["summary"],
        "has_experience_section":  sections["experience"],
        "has_education_section":   sections["education"],
        "has_skills_section":      sections["skills"],
        "has_email":               has_email,
        "has_phone":               has_phone,
        "sections_present":        sections_present,
        "keyword_hit_count":       keyword_hit_count,
        "keyword_total_count":     keyword_total_count,
        "keyword_match_ratio":     round(keyword_match_ratio, 3),
        "keyword_hits":            keyword_hits,
        "experience_depth":        experience_depth,
    }


def ats_compliance_report(features: dict) -> dict:
    checks = []

    def add(label, passed, tip):
        checks.append({"label": label, "passed": bool(passed), "tip": tip})

    add("Contact info detected",            features["has_contact_section"],
        "Add a clear email and phone number near the top.")
    add("Has a Summary/Objective section",  features["has_summary_section"],
        "Add a 2-3 line professional summary near the top.")
    add("Has an Experience section",        features["has_experience_section"],
        "Label your work history section clearly as 'Experience'.")
    add("Has an Education section",         features["has_education_section"],
        "Add a clearly labeled Education section.")
    add("Has a Skills section",             features["has_skills_section"],
        "Add a dedicated Skills section listing relevant skills.")
    add("Uses bullet points (3+)",          features["bullet_count"] >= 3,
        "Use bullet points to describe responsibilities/achievements.")
    add("Uses action verbs (5+)",           features["action_verb_count"] >= 5,
        "Start bullets with strong action verbs (led, built, increased, etc.).")
    add("Has work date ranges",             features["date_range_count"] >= 1,
        "Include start–end dates for each position (e.g. Jan 2022 – Present).")
    add("Avoids table-heavy formatting",    features["suspicious_table_lines"] <= 2,
        "Avoid multi-column tables; ATS parsers often misread them.")
    add("Reasonable length (300-900 words)",300 <= features["word_count"] <= 900,
        "Aim for 1-2 pages (roughly 300-900 words).")

    passed = sum(1 for c in checks if c["passed"])
    return {"checks": checks, "score": passed, "max_score": len(checks)}


# ═══════════════════════════════════════════════════════════════════════════════
# Contact / personal field extractors
# ═══════════════════════════════════════════════════════════════════════════════

def guess_full_name(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line) or "http" in line.lower():
            continue
        if re.match(r"^(resume|curriculum vitae|cv)\s*$", line, re.IGNORECASE):
            continue
        if 1 < len(line.split()) <= 6 and not re.search(r"\d", line):
            return line
    return None


# Suffixes that shouldn't be mistaken for a last name / middle initial
# when a resume header reads e.g. "Juan Dela Cruz Jr." or "Maria Santos III".
_NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def split_full_name(full_name: str | None) -> dict:
    """
    Break a single "First [Middle] Last [Suffix]" string into
    first_name / middle_initial / last_name so each part can be stored
    in its own normalized column instead of one combined field.

    Rules of thumb (good enough for resume headers, not a full NLP parser):
      - 1 word   -> treated as the last name (first_name left blank).
      - 2 words  -> first_name, last_name.
      - 3+ words -> first_name, middle word(s) reduced to an initial,
                    remaining word(s) as last_name. A trailing suffix
                    (Jr., III, ...) is kept attached to the last name.
    """
    if not full_name or not full_name.strip():
        return {"first_name": "", "middle_initial": "", "last_name": ""}

    parts = full_name.strip().split()

    suffix = ""
    if len(parts) > 1 and parts[-1].strip(".").lower() in _NAME_SUFFIXES:
        suffix = " " + parts.pop()

    if len(parts) == 1:
        return {"first_name": "", "middle_initial": "", "last_name": parts[0] + suffix}

    if len(parts) == 2:
        return {"first_name": parts[0], "middle_initial": "", "last_name": parts[1] + suffix}

    first_name = parts[0]
    last_name = parts[-1] + suffix
    middle_words = parts[1:-1]
    middle_initial = "".join(w[0].upper() for w in middle_words if w)

    return {"first_name": first_name, "middle_initial": middle_initial, "last_name": last_name}


def guess_name_parts(text: str) -> dict:
    """Resume-header equivalent of split_full_name(guess_full_name(text))."""
    return split_full_name(guess_full_name(text))


def extract_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None


def extract_phone(text: str) -> str | None:
    m = PHONE_RE.search(text)
    return m.group(0).strip() if m else None


def extract_address(text: str) -> str | None:
    # BUGFIX: the old pattern had no word boundaries, so it matched "address"
    # inside ordinary words like "addressed" anywhere in a paragraph (e.g.
    # "...business needs were addressed throughout the SDLC.") and grabbed
    # the rest of that sentence as if it were a location. Now we only treat
    # a line as a contact-style label if "Address"/"Location" is a whole
    # word AND the line is short (a label line, not a paragraph sentence).
    label_re = re.compile(r"^\s*(?:address|location)\s*:?\s*(.+)$", re.IGNORECASE)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            continue
        m = label_re.match(stripped)
        if m:
            value = m.group(1).strip()
            if value:
                return value
    m = ADDRESS_RE.search(text)
    if m:
        return m.group(0).strip()
    city_re = re.compile(
        r"\b(Manila|Quezon City|Pasig|Makati|Taguig|Pasay|Caloocan|Marikina"
        r"|Parañaque|Las Piñas|Muntinlupa|Mandaluyong|San Juan|Valenzuela"
        r"|New York|Austin|California|Texas|Chicago|Houston)\b",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        if city_re.search(line):
            return line.strip()
    return None


def _normalise_date(raw: str) -> str:
    raw = raw.strip().rstrip(",")
    fmts = [
        "%m/%d/%Y","%d/%m/%Y","%Y-%m-%d","%Y/%m/%d",
        "%B %d, %Y","%b %d, %Y","%B %d %Y","%b %d %Y",
        "%d %B %Y","%d %b %Y","%m-%d-%Y","%d-%m-%Y",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw


def extract_birthdate(text: str) -> str | None:
    bday_re = re.compile(
        r"(?:date\s+of\s+birth|birthdate|dob|born)\s*:?\s*(.+)", re.IGNORECASE
    )
    m = bday_re.search(text)
    if m:
        candidate = m.group(1).strip()
        dm = DATE_RE.search(candidate)
        if dm:
            return _normalise_date(dm.group(0))
        return candidate[:30]
    for m in DATE_RE.finditer(text[:800]):
        val = m.group(0)
        if not DATE_RANGE_RE.search(val):
            return _normalise_date(val)
    return None


def extract_skills_from_text(text: str, extra_keywords: list = None, known_skills: list = None) -> list:
    """
    Detect which skills are mentioned in the resume text.

    `known_skills` is the vocabulary to check against — pass in the real
    skills_master table contents (all skill_name rows) so the parser can
    recognize any skill HR has ever defined, not just the ones baked into
    DEFAULT_KNOWN_SKILLS. Falls back to DEFAULT_KNOWN_SKILLS if the caller
    doesn't supply one, so this still works standalone (e.g. tests).

    `extra_keywords` is additional job-specific terms to also check for
    (typically the same job_keywords passed to extract_ats_features), kept
    separate from `known_skills` since it may include terms that aren't in
    skills_master at all (e.g. free-text description keywords from the
    legacy fallback).
    """
    vocabulary = known_skills if known_skills is not None else DEFAULT_KNOWN_SKILLS
    found = set()
    lower = text.lower()
    for skill in vocabulary:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lower):
            found.add(skill)
    if extra_keywords:
        for kw in extra_keywords:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", lower):
                found.add(kw)
    return sorted(found)


# ═══════════════════════════════════════════════════════════════════════════════
# Education block parser
# ═══════════════════════════════════════════════════════════════════════════════

DEGREE_KEYWORDS = {
    "Doctoral":          [r"ph\.?d", r"doctor"],
    "Master's":          [r"master", r"m\.s", r"m\.b\.a", r"mba", r"m\.eng"],
    "Bachelor's":        [r"bachelor", r"b\.s\b", r"b\.a\b", r"b\.eng",
                          r"bscs",r"bsit",r"bsba",r"bsee",r"bsce",
                          r"undergraduate",r"\bbs\b",r"\bab\b"],
    "Associate":         [r"associate"],
    "Diploma":           [r"diploma", r"certificate"],
    "Entry-level track": [r"entry.level", r"vocational", r"tesda"],
}


def _detect_degree_level(line: str) -> str | None:
    lower = line.lower()
    for level, patterns in DEGREE_KEYWORDS.items():
        for p in patterns:
            if re.search(p, lower):
                return level
    return None


def extract_education(text: str) -> list:
    edu_re = re.compile(
        r"(?:EDUCATION|ACADEMIC|SCHOOLING|EDUCATIONAL\s+BACKGROUND)"
        r"\s*\n(.*?)(?=\n[A-Z][A-Z\s]{2,}\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = edu_re.search(text)
    block = m.group(1) if m else text

    entries = []
    lines   = [l.strip() for l in block.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        degree_level = _detect_degree_level(lines[i])
        if degree_level:
            entry = {"degree_level": degree_level, "major": None,
                     "institution": None, "graduation_year": None}
            window = lines[i: i + 5]
            for wline in window:
                ym = YEAR_RE.search(wline)
                if ym and not entry["graduation_year"]:
                    entry["graduation_year"] = int(ym.group(0))
                if re.search(
                    r"university|college|institute|school|tech|polytechnic", wline, re.I
                ):
                    entry["institution"] = wline
                if re.search(
                    r"science|engineering|business|arts|admin|management|"
                    r"technology|information|computer|nursing|accounting|"
                    r"education|psychology|economics|finance|marketing", wline, re.I
                ) and wline != entry.get("institution"):
                    entry["major"] = wline
            entries.append(entry)
            i += 4
        else:
            i += 1
    return entries


# ═══════════════════════════════════════════════════════════════════════════════
# Work experience block parser
# ═══════════════════════════════════════════════════════════════════════════════

def extract_work_experience(text: str) -> list:
    exp_re = re.compile(
        r"(?:WORK\s+EXPERIENCE?S?|EXPERIENCE|EMPLOYMENT|WORK\s+HISTORY|"
        r"PROFESSIONAL\s+EXPERIENCE|CAREER\s+HISTORY)\s*\n(.*?)"
        r"(?=\n[A-Z][A-Z\s]{2,}\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = exp_re.search(text)
    block = m.group(1) if m else text

    entries = []
    lines   = [l.strip() for l in block.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        dr_match = DATE_RANGE_RE.search(lines[i])
        if dr_match:
            entry = {"job_title": None, "company_name": None,
                     "start_date": None, "end_date": None, "description": None}
            raw_range = dr_match.group(0)
            parts = re.split(r"[-–—to]+", raw_range, maxsplit=1)
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str   = parts[1].strip()
                if re.fullmatch(r"\d{4}", start_str):
                    start_str = f"{start_str}-01-01"
                if re.fullmatch(r"\d{4}", end_str):
                    end_str = f"{end_str}-12-31"
                entry["start_date"] = start_str or None
                entry["end_date"]   = (
                    None if end_str.lower() in ("present","current","now") else end_str
                )
            if i > 0:
                prev = lines[i - 1]
                if "|" in prev or "," in prev:
                    p2 = re.split(r"[|,]", prev, maxsplit=1)
                    entry["job_title"]    = p2[0].strip()
                    entry["company_name"] = p2[1].strip()
                else:
                    entry["job_title"] = prev
            same_before = lines[i][:dr_match.start()].strip()
            if same_before and not entry["job_title"]:
                entry["job_title"] = same_before
            desc_lines = []
            j = i + 1
            while j < len(lines) and not DATE_RANGE_RE.search(lines[j]):
                if re.match(
                    r"^(EDUCATION|SKILLS|SUMMARY|CONTACT|WORK|REFERENCE|PERSONAL)",
                    lines[j], re.I
                ):
                    break
                desc_lines.append(lines[j])
                j += 1
            entry["description"] = " ".join(desc_lines).strip() or None
            entries.append(entry)
            i = j
        else:
            i += 1
    return entries


# ═══════════════════════════════════════════════════════════════════════════════
# Experience / education requirement matching
# (used by app.py to compare the applicant against a specific job posting)
# ═══════════════════════════════════════════════════════════════════════════════

DEGREE_LEVEL_ORDER = [
    "Entry-level track", "Diploma", "Associate", "Bachelor's", "Master's", "Doctoral",
]


def extract_declared_experience_years(text: str) -> float | None:
    """Return the strongest explicit ``X years of experience`` claim, if any.

    The elite ATS dataset uses this common resume wording instead of date
    ranges, so ignoring it made otherwise valid resumes appear to have zero
    experience. The value is still shown on the review page for correction.
    """
    values = [float(match.group(1)) for match in DECLARED_EXPERIENCE_RE.finditer(text or "")]
    return max(values) if values else None


def _parse_resume_date(value, *, is_end: bool) -> datetime | None:
    """Parse ISO, year-only, and common resume month/year date formats."""
    raw = str(value or "").strip().lower().replace(".", "")
    if not raw or raw in {"present", "current", "now", "ongoing"}:
        return datetime.today() if is_end else None

    formats = ("%Y-%m-%d", "%B %Y", "%b %Y", "%m/%Y", "%Y/%m")
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw.title() if "%b" in fmt or "%B" in fmt else raw, fmt)
            if fmt == "%Y":
                return parsed.replace(month=12 if is_end else 1, day=31 if is_end else 1)
            return parsed
        except ValueError:
            continue
    if re.fullmatch(r"\d{4}", raw):
        return datetime(int(raw), 12 if is_end else 1, 31 if is_end else 1)
    return None


def calculate_total_experience_years(work_experience: list, text: str = "") -> float:
    """
    Calculates experience from date ranges and explicit resume claims.
    Supports dates such as ``January 2024`` and ``Feb 2023`` in addition to
    ISO dates. Overlapping date ranges are merged so concurrent roles are not
    double-counted. If no reliable dates exist, use an explicit ``X years of
    experience`` statement (the convention used by the elite ATS dataset).
    """
    intervals = []
    for entry in work_experience or []:
        start = _parse_resume_date(entry.get("start_date"), is_end=False)
        end = _parse_resume_date(entry.get("end_date"), is_end=True)
        if not start or not end or end < start:
            continue
        intervals.append((start, end))

    intervals.sort(key=lambda interval: interval[0])
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    dated_years = sum((end - start).days for start, end in merged) / 365.25
    declared_years = extract_declared_experience_years(text)
    return round(max(dated_years, declared_years or 0.0), 1)


def evaluate_education_requirement(education: list, baseline: str | None) -> dict:
    """
    Compares the applicant's highest detected degree level against the job's
    `education_baseline` text (e.g. "Bachelor's Degree in Computer Science").

    Returns
    -------
    {"highest_level": str | None, "required_level": str | None, "meets": bool}
    """
    applicant_levels = [
        e.get("degree_level") for e in (education or []) if e.get("degree_level")
    ]
    applicant_rank = max(
        (DEGREE_LEVEL_ORDER.index(lvl) for lvl in applicant_levels
         if lvl in DEGREE_LEVEL_ORDER),
        default=-1,
    )
    highest_level = DEGREE_LEVEL_ORDER[applicant_rank] if applicant_rank >= 0 else None

    required_level = _detect_degree_level(baseline) if baseline else None
    if required_level is None:
        # No explicit requirement could be detected → treat as satisfied
        return {"highest_level": highest_level, "required_level": None, "meets": True}

    required_rank = DEGREE_LEVEL_ORDER.index(required_level)
    meets = applicant_rank >= required_rank
    return {
        "highest_level":  highest_level,
        "required_level": required_level,
        "meets":          meets,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Master extractor
# ═══════════════════════════════════════════════════════════════════════════════

def extract_all_info(text: str, job_keywords: list = None, known_skills: list = None) -> dict:
    """
    Single entry point. Returns everything the DB layer and CART model need.
    `text` must already be the output of extract_text() (normalised).

    `job_keywords` — the job's real required-skills list (from
    job_required_skills/skills_master via routes/applicants.py's
    _job_required_skills()). Used both to score keyword_match_ratio and as
    additional terms extract_skills_from_text() checks for.

    `known_skills` — the full skills_master vocabulary (ALL skill_name
    rows, not just this job's), so the parser can recognize any skill the
    resume mentions, not only the ones required by this particular job.
    Falls back to DEFAULT_KNOWN_SKILLS if not supplied.
    """
    job_keywords = job_keywords or []

    guessed_full_name = guess_full_name(text)
    name_parts = split_full_name(guessed_full_name)

    contact_info = {
        "full_name":       guessed_full_name,
        "first_name":      name_parts["first_name"],
        "middle_initial":  name_parts["middle_initial"],
        "last_name":       name_parts["last_name"],
        "email":           extract_email(text),
        "contact_num":     extract_phone(text),
        "location":        extract_address(text),
        "date_of_birth":   extract_birthdate(text),
    }

    skills          = extract_skills_from_text(text, extra_keywords=job_keywords, known_skills=known_skills)
    education       = extract_education(text)
    work_experience = extract_work_experience(text)
    ats_features    = extract_ats_features(text, job_keywords=job_keywords)
    compliance      = ats_compliance_report(ats_features)

    return {
        "contact_info":    contact_info,
        "skills":          skills,
        "education":       education,
        "work_experience": work_experience,
        "ats_features":    ats_features,
        "ats_compliance":  compliance,
        "normalised_text": text,
    }