import re
import logging
from typing import Dict, Any
def setup_logging():
    logging.basicConfig(level=logging.INFO ,
                        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                        )
def clean_text(text:str)-> str:
    if not text:
        return ""
    text = re.sub(r'\s+' , ' ' , text.strip())
    text  = re.sub(r'[^\w\s\-\.\,\:\;\!\?\(\)]+' , '' , text)
    return text
def is_likely_heading(text: str)-> bool:
    text =text.strip()
    heading_words = [
        'introduction' , 'conclusion' , 'abstract','overview',
        'methodology', 'method', 'results', 'discussion', 'background',
        'literature', 'review', 'analysis', 'implementation', 'evaluation',
        'future', 'work', 'references', 'bibliography', 'appendix'
    ]
    patterns = [
        r'^\d+\.?\s+[A-Z]',
        r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$',
        r'^[A-Z\s]+$',
    ]
    text_lower = text.lower()
    contains_heading = any(word in text_lower for word in heading_words)
    matches_patter = any(re.match(pattern , text) for pattern in patterns)
    reasonable_length = len(text) <=100
    return (contains_heading or matches_patter)  and reasonable_length
def validate_input(result : Dict[str, Any]) -> bool:
    if not isinstance(result , dict):
        return False
    if "title" not in result or "outline" not in result:
        return False
    if not isinstance(result["title"], str):
        return False
    if not isinstance(result["outline"], str):
        return False
    for item in result["outline"]:
        if not isinstance(item, dict):
            return False
        required_keys = ["level" , "text" , "page"]
        if not all(key in item for key in required_keys):
            return False
        if item["level"] not in ["H1" , "H2" , "H3"]:
            return False
        if not isinstance(item["page"] , int) or item["page"] < 0:
            return False
    return True


