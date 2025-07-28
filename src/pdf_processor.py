import fitz
import logging
import time
from heading_detector import HeadingDetector
from title_extractor import TitleExtractor
from utils import clean_text, normalize_font_sizes

logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self):
        self.heading_detector = HeadingDetector()
        self.title_extractor = TitleExtractor()
        self.max_full_scan_pages = 30

    def extract_outline_fast(self, pdf_path, start_time, time_limit):
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            elapsed = time.time() - start_time
            if elapsed > time_limit * 0.8:
                doc.close()
                return {"title": "", "outline": []}

            title = self.title_extractor.extract_title_fast(doc)

            elapsed = time.time() - start_time
            if elapsed > time_limit * 0.9:
                doc.close()
                return {"title": title, "outline": []}

            remaining_time = time_limit - elapsed
            outline = self._extract_headings_adaptive(doc, page_count, remaining_time)

            doc.close()

            return {"title": title, "outline": outline}

        except Exception as e:
            logger.error(f"Error in PDF processing: {e}")
            return {"title": "", "outline": []}

    def _extract_headings_adaptive(self, doc, page_count, remaining_time):
        if page_count <= self.max_full_scan_pages and remaining_time > 3:
            return self._extract_headings_full_scan(doc)
        else:
            sample_ratio = min(0.6, remaining_time / 10)
            return self._extract_headings_sampled(doc, page_count, sample_ratio)

    def _extract_headings_full_scan(self, doc):
        text_elements = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    if not line.get("spans"):
                        continue

                    line_text = ""
                    max_font_size = 0
                    is_bold = False
                    bbox = [0, 0, 0, 0]

                    for span in line["spans"]:
                        line_text += span.get("text", "") + " "
                        max_font_size = max(max_font_size, span.get("size", 0))
                        if span.get("flags", 0) & 16:
                            is_bold = True
                        if not bbox[2]:
                            bbox = span.get("bbox", [0, 0, 0, 0])

                    line_text = clean_text(line_text)

                    if line_text and len(line_text) > 2:
                        text_elements.append({
                            "text": line_text,
                            "page": page_num + 1,
                            "font_size": max_font_size,
                            "is_bold": is_bold,
                            "bbox": bbox
                        })

        headings = self.heading_detector.detect_headings_ultra_fast(text_elements)
        return self._assign_heading_levels_smart(headings)

    def _extract_headings_sampled(self, doc, page_count, sample_ratio):
        sample_size = max(10, int(page_count * sample_ratio))
        sample_pages = set()

        first_pages = min(5, page_count // 4)
        sample_pages.update(range(first_pages))

        last_pages = min(3, page_count // 6)
        sample_pages.update(range(page_count - last_pages, page_count))

        remaining_samples = sample_size - len(sample_pages)
        if remaining_samples > 0:
            middle_start = first_pages
            middle_end = page_count - last_pages
            if middle_end > middle_start:
                step = max(1, (middle_end - middle_start) // remaining_samples)
                sample_pages.update(range(middle_start, middle_end, step))

        text_elements = []
        for page_num in sorted(list(sample_pages)[:sample_size]):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    if not line.get("spans"):
                        continue

                    line_text = " ".join(span.get("text", "") for span in line["spans"])
                    line_text = clean_text(line_text)

                    if line_text and len(line_text) > 2:
                        max_font_size = max(span.get("size", 0) for span in line["spans"])
                        is_bold = any(span.get("flags", 0) & 16 for span in line["spans"])
                        bbox = line["spans"][0].get("bbox", [0, 0, 0, 0])

                        text_elements.append({
                            "text": line_text,
                            "page": page_num + 1,
                            "font_size": max_font_size,
                            "is_bold": is_bold,
                            "bbox": bbox
                        })

        headings = self.heading_detector.detect_headings_ultra_fast(text_elements)
        return self._assign_heading_levels_smart(headings)

    def _assign_heading_levels_smart(self, headings):
        if not headings:
            return []

        font_sizes = [h["font_size"] for h in headings]
        font_stats = normalize_font_sizes(font_sizes)

        unique_sizes = sorted(list(set(font_sizes)), reverse=True)

        size_to_level = {}
        for i, size in enumerate(unique_sizes[:3]):
            size_to_level[size] = f"H{i + 1}"

        result = []
        for heading in sorted(headings, key=lambda x: (x["page"], x.get("bbox", [0, 0, 0, 0])[1])):
            if heading["font_size"] in size_to_level:
                result.append({
                    "level": size_to_level[heading["font_size"]],
                    "text": heading["text"],
                    "page": heading["page"]
                })

        return result
