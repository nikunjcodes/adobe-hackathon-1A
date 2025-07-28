# Adobe Hackathon PDF Processor

This Docker container automatically extracts titles and hierarchical outlines from PDF documents using advanced text analysis and machine learning techniques.

## Our Approach

Our solution employs a multi-stage pipeline combining traditional document analysis with modern NLP:

**Title Extraction**: We extract titles using a priority-based approach: first from PDF metadata, then analyzing the first page for large/bold text positioned at the top, and finally falling back to filename parsing. Font size thresholds and positioning heuristics ensure accurate title detection.

**Heading Detection**: Our heading detector uses comprehensive scoring based on:
- Font characteristics (size, boldness relative to document statistics)
- Pattern matching (numbering schemes, chapter/section keywords)
- Semantic analysis using Sentence Transformers for content similarity
- Layout analysis (positioning, indentation)
- False positive filtering (removing page numbers, figures, tables)

**Adaptive Processing**: For efficiency, we use intelligent sampling for large documents (>30 pages) while maintaining full scanning for smaller ones. This ensures sub-10-second processing while preserving accuracy.

## Models & Libraries

- **PyMuPDF (fitz)**: PDF parsing and text extraction with font/formatting metadata
- **Sentence Transformers**: paraphrase-MiniLM-L3-v2 model (~116MB) for semantic heading analysis
- **NLTK**: Text preprocessing with punkt tokenizer and stopwords
- **scikit-learn**: Cosine similarity calculations for semantic matching
- **NumPy**: Statistical analysis of font characteristics

All models are pre-downloaded during Docker build for offline operation.

## Build Instructions

```bash
docker build --platform linux/amd64 -t adobe-hackathon-pdf-processor:latest .
```

## Run Instructions

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none adobe-hackathon-pdf-processor:latest
```

## Output Format

Each PDF generates a corresponding JSON file with:
```json
{
  "title": "Document Title",
  "outline": [
    {"level": "H1", "text": "Chapter 1", "page": 1},
    {"level": "H2", "text": "1.1 Overview", "page": 2}
  ]
}
```

## Performance Features

- ✅ AMD64 compatible, CPU-only processing
- ✅ Sub-10 second processing for 50-page documents
- ✅ Offline operation with pre-cached models
- ✅ Memory-efficient with automatic cleanup
- ✅ Time-bounded execution with graceful fallbacks
