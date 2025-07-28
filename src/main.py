import os
import sys
import json
import time
import logging
from pathlib import Path
from pdf_processor import PDFProcessor
from utils import setup_logging, validate_output

setup_logging()
logger = logging.getLogger(__name__)


class OutlineExtractor:
    def __init__(self):
        self.processor = PDFProcessor()
        self.input_dir = Path("/app/input")
        self.output_dir = Path("/app/output")
        self.time_limit = 10

    def process_all_pdfs(self):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            pdf_files = list(self.input_dir.glob("*.pdf"))

            if not pdf_files:
                logger.warning("No PDF files found")
                return

            logger.info(f"Processing {len(pdf_files)} PDF files")

            for pdf_file in pdf_files:
                self._process_single_pdf(pdf_file)

        except Exception as e:
            logger.error(f"Critical error: {e}")
            sys.exit(1)

    def _process_single_pdf(self, pdf_path):
        start_time = time.time()
        output_path = self.output_dir / f"{pdf_path.stem}.json"

        try:
            logger.info(f"Processing: {pdf_path.name}")
            result = self.processor.extract_outline_fast(str(pdf_path), start_time, self.time_limit)

            if not validate_output(result):
                result = {"title": "", "outline": []}

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            elapsed_time = time.time() - start_time
            logger.info(f"Completed {pdf_path.name} in {elapsed_time:.2f}s")

        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"title": "", "outline": []}, f)


def main():
    extractor = OutlineExtractor()
    extractor.process_all_pdfs()


if __name__ == "__main__":
    main()
