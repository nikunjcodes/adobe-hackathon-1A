import re
import logging
from typing import Dict, Any


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'[^\w\s\-\.\,\:\;\!\?\(\)\[\]\'\"]+', '', text)

    return text


def is_likely_heading(text: str) -> bool:
    if not text or len(text) < 3:
        return False

    text = text.strip()
    text_lower = text.lower()

    if len(text) > 150:
        return False

    comprehensive_heading_keywords = {
        'abstract', 'introduction', 'background', 'literature', 'review', 'summary',
        'conclusion', 'conclusions', 'discussion', 'results', 'findings', 'analysis',
        'evaluation', 'assessment', 'method', 'methods', 'methodology', 'approach',
        'techniques', 'implementation', 'experiments', 'experimental', 'study',
        'research', 'investigation', 'chapter', 'section', 'subsection', 'appendix',
        'part', 'overview', 'references', 'bibliography', 'acknowledgments',
        'acknowledgements', 'preface', 'contents', 'objectives', 'goals', 'aims',
        'hypothesis', 'theory', 'theoretical', 'framework', 'model', 'design',
        'architecture', 'system', 'algorithm', 'procedure', 'process', 'workflow',
        'applications', 'case', 'examples', 'limitations', 'future', 'recommendations',
        'implications', 'significance', 'contribution', 'novelty', 'related',
        'previous', 'existing', 'current', 'proposed', 'solution', 'problem'
    }

    if any(keyword in text_lower for keyword in comprehensive_heading_keywords):
        return True

    heading_patterns = [
        r'^(chapter|section|appendix|part)\s+\d+',
        r'^\d+(\.\d+)*\s+[a-zA-Z]',
        r'^([ivxlcdm]+)\.?\s+[a-zA-Z]',
        r'^[a-z]\.\s+[a-zA-Z]',
        r'^(abstract|introduction|conclusion|references|bibliography)$'
    ]

    if any(re.match(pattern, text_lower) for pattern in heading_patterns):
        return True

    if text.isupper() and 5 <= len(text) <= 80:
        return True

    title_case_pattern = r'^[A-Z][a-z]*(\s+[A-Z][a-z]*)*$'
    if re.match(title_case_pattern, text) and len(text) <= 100:
        return True

    sentence_case_pattern = r'^[A-Z][a-z]*.*[^.]$'
    if re.match(sentence_case_pattern, text) and 10 <= len(text) <= 60:
        word_count = len(text.split())
        if 2 <= word_count <= 8:
            return True

    return False


def validate_output(result: Dict[str, Any]) -> bool:
    try:
        if not isinstance(result, dict):
            return False

        if "title" not in result or "outline" not in result:
            return False

        if not isinstance(result["title"], str) or not isinstance(result["outline"], list):
            return False

        for item in result["outline"]:
            if not isinstance(item, dict):
                return False

            if not all(key in item for key in ["level", "text", "page"]):
                return False

            if item["level"] not in ["H1", "H2", "H3"]:
                return False

            if not isinstance(item["page"], int) or item["page"] < 1:
                return False

            if not isinstance(item["text"], str) or not item["text"].strip():
                return False

        return True

    except Exception:
        return False


def normalize_font_sizes(font_sizes: list) -> Dict[str, float]:
    if not font_sizes:
        return {}

    import numpy as np

    sizes_array = np.array(font_sizes)

    return {
        'min': np.min(sizes_array),
        'max': np.max(sizes_array),
        'mean': np.mean(sizes_array),
        'median': np.median(sizes_array),
        'std': np.std(sizes_array),
        'p25': np.percentile(sizes_array, 25),
        'p75': np.percentile(sizes_array, 75),
        'p90': np.percentile(sizes_array, 90)
    }


def extract_numbering_pattern(text: str) -> Dict[str, Any]:
    text = text.strip()

    patterns = {
        'decimal': re.match(r'^(\d+(\.\d+)*)', text),
        'roman': re.match(r'^([IVXLCDM]+)', text, re.IGNORECASE),
        'alpha': re.match(r'^([A-Z])', text),
        'chapter': re.match(r'^(Chapter|Section|Appendix)\s+(\d+)', text, re.IGNORECASE)
    }

    for pattern_type, match in patterns.items():
        if match:
            return {
                'type': pattern_type,
                'number': match.group(1),
                'full_match': match.group(0)
            }

    return {'type': 'none', 'number': None, 'full_match': None}
