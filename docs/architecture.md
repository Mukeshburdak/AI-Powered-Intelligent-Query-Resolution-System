# Proposed Architecture

**Status:** Proposed baseline; components marked as planned are not yet implemented.

```mermaid
flowchart LR
    A[Document Upload] --> B[Parsing and Cleaning]
    B --> C[Chunking]
    C --> D[Embedding Service]
    D --> E[FAISS Vector Store]
    F[User Question] --> G[Query Agent]
    G --> H[Retrieval Agent]
    E --> H
    H --> I[Response Agent]
    I --> J[Answer with Citations]
    I --> K[Confidence Service]
```

The initial scaffold currently supports document upload, text extraction for PDF/DOCX/TXT, text cleaning, character-based chunking, and a baseline query endpoint. Embeddings, FAISS retrieval, grounded answer generation, persistence, and the complete UI are planned work.
