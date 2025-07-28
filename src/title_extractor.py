import re
import logging
import fitz
from utils import clean_text, is_likely_heading

logger = logging.getLogger(__name__)


class TitleExtractor:
    def extract_title_fast(self, doc):
        title = self._extract_from_metadata(doc)
        if title:
            return title

        title = self._extract_from_first_page_fast(doc)
        if title:
            return title

        if hasattr(doc, 'name') and doc.name:
            return self._extract_from_filename(doc.name)

        return ""

    def _extract_from_metadata(self, doc):
        try:
            metadata = doc.metadata
            if metadata and metadata.get('title'):
                title = clean_text(metadata['title'])
                if self._is_valid_title(title):
                    return title
        except Exception:
            pass
        return ""

    def _extract_from_first_page_fast(self, doc):
        if len(doc) == 0:
            return ""

        try:
            first_page = doc[0]
            blocks = first_page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

            candidates = []

            for block in blocks[:3]:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    if not line.get("spans"):
                        continue

                    line_text = ""
                    max_font_size = 0
                    is_bold = False
                    y_pos = 0

                    for span in line["spans"]:
                        line_text += span.get("text", "") + " "
                        font_size = span.get("size", 0)
                        if font_size > max_font_size:
                            max_font_size = font_size
                        if span.get("flags", 0) & 16:
                            is_bold = True
                        if not y_pos:
                            y_pos = span.get("bbox", [0, 0, 0, 0])[1]

                    line_text = clean_text(line_text)

                    if self._is_title_candidate_fast(line_text, max_font_size, is_bold, y_pos):
                        candidates.append({
                            "text": line_text,
                            "font_size": max_font_size,
                            "is_bold": is_bold,
                            "y_pos": y_pos
                        })

            if candidates:
                candidates.sort(key=lambda x: (-x["font_size"], x["y_pos"]))
                return candidates[0]["text"]

        except Exception:
            pass

        return ""

    def _is_title_candidate_fast(self, text, font_size, is_bold, y_pos):
        if len(text) < 5 or len(text) > 200:
            return False

        if font_size < 12:
            return False

        if y_pos > 300:
            return False

        if not re.search(r'[a-zA-Z]', text):
            return False

        if is_likely_heading(text):
            return False

        text_lower = text.lower()
        avoid_patterns = [
            r'^\d+$', r'^page\s+\d+', r'^abstract$', r'^introduction$',
            r'^table\s+of\s+contents', r'^contents$'
        ]

        if any(re.match(pattern, text_lower) for pattern in avoid_patterns):
            return False

        return True

    def _extract_from_filename(self, filename):
        try:
            name = filename.split('/')[-1].split('\\')[-1]
            if '.' in name:
                name = name.rsplit('.', 1)[0]

            title = re.sub(r'[_-]', ' ', name)
            title = re.sub(r'\s+', ' ', title).strip()

            if self._is_valid_title(title):
                return title
        except Exception:
            pass

        return ""

    def _is_valid_title(self, title):
        if not title or len(title) < 5 or len(title) > 200:
            return False

        if not re.search(r'[a-zA-Z]', title):
            return False

        bad_patterns = [
            r'^\d+$', r'^untitled', r'^document', r'^microsoft\s+word'
        ]

        title_lower = title.lower()
        return not any(re.match(pattern, title_lower) for pattern in bad_patterns)
