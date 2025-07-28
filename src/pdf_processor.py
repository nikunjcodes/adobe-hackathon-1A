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
        doc = None
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # Check if document is empty
            if page_count == 0:
                logger.warning("PDF has no pages")
                return {"title": "", "outline": []}

            elapsed = time.time() - start_time
            if elapsed > time_limit * 0.8:
                logger.warning("Time limit reached before processing")
                return {"title": "", "outline": []}

            title = self.title_extractor.extract_title_fast(doc)

            elapsed = time.time() - start_time
            if elapsed > time_limit * 0.9:
                logger.warning("Time limit reached after title extraction")
                return {"title": title, "outline": []}

            remaining_time = time_limit - elapsed
            outline = self._extract_headings_adaptive(doc, page_count, remaining_time)

            return {"title": title, "outline": outline}

        except Exception as e:
            logger.error(f"Error in PDF processing: {e}")
            return {"title": "", "outline": []}
        finally:
            # Ensure document is always closed
            if doc:
                try:
                    doc.close()
                except:
                    pass

    def _extract_headings_adaptive(self, doc, page_count, remaining_time):
        if page_count <= self.max_full_scan_pages and remaining_time > 3:
            return self._extract_headings_full_scan(doc)
        else:
            sample_ratio = min(0.6, remaining_time / 10)
            return self._extract_headings_sampled(doc, page_count, sample_ratio)

    def _extract_headings_full_scan(self, doc):
        text_elements = []

        try:
            for page_num in range(len(doc)):
                try:
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
                                span_text = span.get("text", "")
                                if span_text:  # Only add non-empty text
                                    line_text += span_text + " "

                                font_size = span.get("size", 0)
                                if font_size > 0:  # Only consider valid font sizes
                                    max_font_size = max(max_font_size, font_size)

                                if span.get("flags", 0) & 16:  # Bold flag
                                    is_bold = True

                                # Get bbox from first span with valid bbox
                                span_bbox = span.get("bbox", [0, 0, 0, 0])
                                if span_bbox and span_bbox[2] > span_bbox[0]:  # Valid bbox
                                    if bbox == [0, 0, 0, 0]:
                                        bbox = span_bbox

                            line_text = clean_text(line_text)

                            # More robust text validation
                            if line_text and len(line_text.strip()) > 2 and max_font_size > 0:
                                text_elements.append({
                                    "text": line_text.strip(),
                                    "page": page_num + 1,
                                    "font_size": max_font_size,
                                    "is_bold": is_bold,
                                    "bbox": bbox
                                })

                except Exception as e:
                    logger.warning(f"Error processing page {page_num}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in full scan: {e}")

        headings = self.heading_detector.detect_headings(text_elements)
        return self._assign_heading_levels_smart(headings)

    def _extract_headings_sampled(self, doc, page_count, sample_ratio):
        sample_size = max(10, int(page_count * sample_ratio))
        sample_pages = set()

        # Always include first pages
        first_pages = min(5, page_count // 4)
        sample_pages.update(range(first_pages))

        # Always include last pages
        last_pages = min(3, page_count // 6)
        sample_pages.update(range(page_count - last_pages, page_count))

        # Fill remaining samples from middle
        remaining_samples = sample_size - len(sample_pages)
        if remaining_samples > 0:
            middle_start = first_pages
            middle_end = page_count - last_pages
            if middle_end > middle_start:
                step = max(1, (middle_end - middle_start) // remaining_samples)
                sample_pages.update(range(middle_start, middle_end, step))

        text_elements = []

        try:
            for page_num in sorted(list(sample_pages)[:sample_size]):
                try:
                    page = doc[page_num]
                    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

                    for block in blocks:
                        if "lines" not in block:
                            continue

                        for line in block["lines"]:
                            if not line.get("spans"):
                                continue

                            line_text = " ".join(span.get("text", "") for span in line["spans"] if span.get("text", ""))
                            line_text = clean_text(line_text)

                            if line_text and len(line_text.strip()) > 2:
                                # More robust font size calculation
                                font_sizes = [span.get("size", 0) for span in line["spans"] if span.get("size", 0) > 0]
                                max_font_size = max(font_sizes) if font_sizes else 12  # Default font size

                                is_bold = any(span.get("flags", 0) & 16 for span in line["spans"])

                                # Get bbox from first valid span
                                bbox = [0, 0, 0, 0]
                                for span in line["spans"]:
                                    span_bbox = span.get("bbox", [0, 0, 0, 0])
                                    if span_bbox and span_bbox[2] > span_bbox[0]:
                                        bbox = span_bbox
                                        break

                                text_elements.append({
                                    "text": line_text.strip(),
                                    "page": page_num + 1,
                                    "font_size": max_font_size,
                                    "is_bold": is_bold,
                                    "bbox": bbox
                                })

                except Exception as e:
                    logger.warning(f"Error processing sampled page {page_num}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in sampled extraction: {e}")

        headings = self.heading_detector.detect_headings_ultra_fast(text_elements)
        return self._assign_heading_levels_smart(headings)

    def _assign_heading_levels_smart(self, headings):
        if not headings:
            return []

        try:
            font_sizes = [h["font_size"] for h in headings if h.get("font_size", 0) > 0]

            if not font_sizes:
                logger.warning("No valid font sizes found in headings")
                return []

            # Use font statistics for better level assignment
            font_stats = normalize_font_sizes(font_sizes)
            unique_sizes = sorted(list(set(font_sizes)), reverse=True)

            # Create level mapping for up to 3 levels
            size_to_level = {}
            for i, size in enumerate(unique_sizes[:3]):
                size_to_level[size] = f"H{i + 1}"

            result = []

            # Sort headings by page and then by vertical position
            sorted_headings = sorted(
                headings,
                key=lambda x: (
                    x.get("page", 0),
                    x.get("bbox", [0, 0, 0, 0])[1]  # y-coordinate
                )
            )

            for heading in sorted_headings:
                font_size = heading.get("font_size", 0)
                if font_size in size_to_level and heading.get("text", "").strip():
                    result.append({
                        "level": size_to_level[font_size],
                        "text": heading["text"].strip(),
                        "page": heading.get("page", 1)
                    })

            logger.info(f"Assigned levels to {len(result)} headings")
            return result

        except Exception as e:
            logger.error(f"Error in level assignment: {e}")
            return []
