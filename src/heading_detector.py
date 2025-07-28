import re
import logging
import os
import numpy as np

from collections import Counter

from typing import List , Dict , Any , Tuple

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
from utils import clean_text , is_likely_heading

logger = logging.getLogger(__name__)
class HeadingDetector:
    def __init__(self):
        self.model = None
        self.prototype_embedding = None

        if MODEL_AVAILABLE:
            try:
                model_path = './models/sentence_model'
                if os.path.exists(model_path):
                    self.mode=  SentenceTransformer(model_path)
                    self.prototype_embedding = self._create_enhanced_prototypes()
                    logger.info("Loaded enhanced heading detection model")
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
        self.heading_patterns = [
            re.compile(r'^(Chapter|Section|Appendix|Part)\s+\d+', re.IGNORECASE),
            re.compile(r'^\d+(\.\d+)*\s+[A-Z]'),
            re.compile(r'^([IVXLCDM]+)\.?\s+[A-Z]', re.IGNORECASE),
            re.compile(r'^[A-Z][A-Z\s\-]{4,}$'),
            re.compile(r'^\d+(\.\d+){0,2}$'),
            re.compile(r'^[A-Z]\.\s+[A-Z]', re.IGNORECASE),
            re.compile(r'^(Abstract|Introduction|Conclusion|References|Bibliography)$', re.IGNORECASE)
        ]
        self.heading_keywords = {
            'abstract', 'introduction', 'background', 'literature', 'review', 'summary',
            'conclusion', 'discussion', 'results', 'findings', 'analysis', 'evaluation',
            'method', 'methods', 'methodology', 'approach', 'techniques', 'implementation',
            'experiments', 'experimental', 'study', 'research', 'investigation',
            'chapter', 'section', 'subsection', 'appendix', 'part', 'overview',
            'references', 'bibliography', 'acknowledgments', 'preface', 'contents',
            'objectives', 'goals', 'hypothesis', 'theory', 'framework', 'model',
            'design', 'architecture', 'system', 'algorithm', 'procedure', 'process'
        }
        self.false_positive_patterns = [
            re.compile(r'^page\s*\d*$', re.IGNORECASE),
            re.compile(r'^fig(ure)?\s*\d*', re.IGNORECASE),
            re.compile(r'^table\s*\d*', re.IGNORECASE),
            re.compile(r'^(www\.|http|https)', re.IGNORECASE),
            re.compile(r'^\d+$'),
            re.compile(r'^[^\w\s]*$'),
            re.compile(r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.IGNORECASE)
        ]
    def _create_enhanced_prototypes(self) -> np.ndarray:
        if not self.model:
            return np.array([])
        prototype_texts = [
            "Introduction", "Abstract", "Summary", "Conclusion", "Discussion",
            "Methodology", "Methods", "Results", "Analysis", "Evaluation",
            "Background", "Literature Review", "Implementation", "Experiments",
            "Chapter 1 Overview", "Section 2.1 Methods", "Appendix A Results",
            "Theoretical Framework", "System Design", "Future Work"
        ]
        try:
            return self.mode.encode(prototype_texts)
        except Exception:
            return np.array([])
    def detect_headings(self , text_elements: List[Dict[str ,Any]])-> List[Dict[str ,Any]]:
        if not text_elements:
            return []
        font_analysis = self._analysze_font_characteristics(text_elements)
        candidates = self._extract_heading_candidates(text_elements , font_analysis)
        scored_candidates = self._score_candidates_advanced(candidates , font_analysis)
        validated_heading = self._validate_and_filter(scored_candidates)
        return self._cleanup(validated_heading)
    def _analysze_font_characteristics(self, text_elements: List[Dict[str,Any]]) ->Dict[str,Any]:
        font_sizes = [elem["font_size"] for elem in text_elements]
        indentations = [elem.get("bbox" , [0,0,0,0])[0] for elem in text_elements]
        font_stats = {
            'sizes': font_sizes,
            'unique_sizes': sorted(list(set(font_sizes)), reverse=True),
            'size_counts': Counter(font_sizes),
            'percentiles': {
                'p75': np.percentile(font_sizes, 75),
                'p90': np.percentile(font_sizes, 90),
                'mean': np.mean(font_sizes),
                'std': np.std(font_sizes)
            },
            'indentations': indentations,
            'mean_indent': np.mean(indentations),
            'min_indent': np.min(indentations)
        }
        return font_stats

    def _extract_heading_candidates(self, elements: List[Dict[str, Any]], font_analysis: Dict[str, Any]) -> List[
        Dict[str, Any]]:
        candidates = []
        size_threshold = font_analysis['percentiles']['p75']

        for elem in elements:
            text = elem["text"]
            font_size = elem["font_size"]
            is_bold = elem["is_bold"]
            bbox = elem.get("bbox", [0, 0, 0, 0])
            indent = bbox[0]

            if self._is_potential_heading(text, font_size, is_bold, indent, size_threshold, font_analysis):
                candidates.append(elem)

        return candidates

    def _is_potential_heading(self, text: str, font_size: float, is_bold: bool,
                              indent: float, size_threshold: float, font_analysis: Dict[str, Any]) -> bool:
        if len(text) < 3 or len(text) > 150:
            return False

        if self._is_obvious_false_positive(text):
            return False

        mean_font = font_analysis['percentiles']['mean']
        unique_sizes = font_analysis['unique_sizes']

        font_score = 0
        if font_size >= size_threshold or font_size > mean_font * 1.2:
            font_score += 2
        if font_size in unique_sizes[:3]:
            font_score += 1
        if is_bold:
            font_score += 2

        pattern_score = 0
        if any(pattern.match(text.strip()) for pattern in self.heading_patterns):
            pattern_score = 3

        content_score = 0
        if is_likely_heading(text):
            content_score = 2

        layout_score = 0
        if indent <= font_analysis['mean_indent']:
            layout_score = 1

        total_score = font_score + pattern_score + content_score + layout_score
        return total_score >= 3
    def _score_candidates_advanced(self, candidates : List[Dict[str,Any]] , font_analysis: Dict[str, Any]) -> List[Dict[str,Any]]:
        scored_candidates = []

        for candidate in candidates:
            score = self._calculate_comprehensive_score(candidate, font_analysis)
            candidate['heading_score'] = score
            scored_candidates.append(candidate)

        scored_candidates.sort(key=lambda x: x['heading_score'], reverse=True)
        return scored_candidates

    def _calculate_comprehensive_score(self, candidate: Dict[str, Any],
                                       font_analysis: Dict[str, Any]) -> float:
        text = candidate["text"]
        font_size = candidate["font_size"]
        is_bold = candidate["is_bold"]
        bbox = candidate.get("bbox", [0, 0, 0, 0])

        score = 0.0

        font_score = self._calculate_font_score(font_size, is_bold, font_analysis)
        pattern_score = self._calculate_pattern_score(text)
        semantic_score = self._calculate_semantic_score(text)
        layout_score = self._calculate_layout_score(bbox, font_analysis)
        length_score = self._calculate_length_score(text)

        score = (font_score * 0.25 + pattern_score * 0.25 +
                 semantic_score * 0.25 + layout_score * 0.15 + length_score * 0.1)

        return score
    def _calculate_font_score(self , font_size:float , is_bold : bool , font_analysis: Dict[str, Any]) -> float:
        unique_sizes = font_analysis['unique_sizes']
        mean_font = font_analysis['percentiles']['mean']
        score = 0.0
        if len(unique_sizes) >= 3:
            if font_size == unique_sizes[0]:
                score += 1.0
            elif font_size == unique_sizes[1]:
                score += 0.8
            elif font_size == unique_sizes[2]:
                score += 0.6
        else:
            if font_size > mean_font * 1.3:
                score += 1.0
            elif font_size > mean_font * 1.1:
                score += 0.7

        if is_bold:
            score += 0.5

        return min(score, 1.0)
    def _calculate_pattern_score(self , text:str)-> float:
        text_stripped = text.strip()
        for i, pattern in enumerate(self.heading_patterns):
            if pattern.match(text_stripped):
                return 1.0 - (i * 0.1)

        if text_stripped.isupper() and 5 <= len(text_stripped) <= 50:
            return 0.7

        return 0.0

    def _calculate_semantic_score(self, text: str) -> float:
        text_lower = text.lower()

        keyword_matches = sum(1 for keyword in self.heading_keywords if keyword in text_lower)
        keyword_score = min(keyword_matches / 3.0, 1.0)

        model_score = 0.0
        if self.model and self.prototype_embedding.size > 0 and len(text) > 5:
            try:
                text_embedding = self.model.encode([text])
                similarities = cosine_similarity(text_embedding, self.prototype_embedding)
                model_score = np.max(similarities)
            except Exception:
                pass

        return max(keyword_score, model_score)

    def _calculate_layout_score(self, bbox: List[float], font_analysis: Dict[str, Any]) -> float:
        indent = bbox[0]
        min_indent = font_analysis['min_indent']
        mean_indent = font_analysis['mean_indent']
        if indent <= min_indent + 5:
            return 1.0
        elif indent <= mean_indent:
            return 0.7
        else:
            return 0.3

    def _calculate_length_score(self, text: str) -> float:
        length = len(text)
        if 5 <= length <= 80:
            return 1.0
        elif 3 <= length <= 120:
            return 0.7
        else:
            return 0.0
    def _validate_and_filter (self , scored_candidates : List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not scored_candidates:
            return []
        threshold = max(0.4, scored_candidates[0]['heading_score'] * 0.6)

        validated = []
        for candidate in scored_candidates:
            if candidate['heading_score'] >= threshold:
                validated.append(candidate)

        return validated[:50]
    def _cleanup(self , headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []
        seen_texts = set()

        for heading in sorted(headings, key=lambda x: (x["page"], x.get("bbox", [0, 0, 0, 0])[1])):
            text = clean_text(heading["text"])
            text_lower = text.lower()

            if text_lower in seen_texts or self._is_obvious_false_positive(text):
                continue

            seen_texts.add(text_lower)
            heading["text"] = text
            cleaned.append(heading)

        return cleaned
    def _is_obvious_false_positive(self, text: str) -> bool:
        text_clean = text.lower().strip()
        if len(text_clean) < 3:
            return True
        return any(pattern.match(text_clean) for pattern in self.heading_patterns)


