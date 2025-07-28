import os
import sys
import json
import time
import logging
from pathlib import Path
from pdf_processor import PDFProcessor
from utils import setup_logging , validate_input

setup_logging()
logger = logging.getLogger(__name__)

class OutlineExtractor:
    def __init__(self):
        self.processor  = PDFProcessor()
        self.input_dir = Path("/app/input")
        self.