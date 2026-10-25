from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings

from ingestion.pdf_to_markdown import PDFToMarkdownConverter
from ingestion.semantic_chunker import chunk_markdown

# We will replace this Azure implementation with FAISS
from vectorstore.faiss_store import FAISSVectorStore, Retriever

from rag.kpi_extractor_rag import extract_financial_metrics
from database.save_metrics import save_metrics


def parse_company_year(pdf_file: Path) -> tuple[str, str]:
    """
    Parse company and year from a PDF filename.

    Supports:
        2024_Apple.pdf
        2024_AnnualReport_Apple.pdf
    """

    stem = pdf_file.stem
    parts = stem.split("_")

    if parts and parts[0].isdigit():
        year = parts[0]
        company = parts[-1]

    elif len(parts) >= 2:
        company = parts[0]
        year = parts[1]

    else:
        company = stem
        year = ""

    return company, year


def ingest_document(
    pdf_path: str,
    embeddings,
    vector_store
) -> None:
    """
    Ingest a single PDF document.

    Pipeline:

        PDF
         ↓
        PyMuPDF4LLM
         ↓
        Markdown
         ↓
        Semantic Chunking
         ↓
        Local Embeddings
         ↓
        FAISS
         ↓
        RAG
         ↓
        PostgreSQL
    """

    pdf_file = Path(pdf_path)

    company, year = parse_company_year(pdf_file)

    print(
        f"\nIngesting {pdf_file.name} "
        f"as company={company!r}, year={year!r}"
    )

    # --------------------------------------------------
    # STEP 1: PDF → Markdown
    # --------------------------------------------------

    print("\n[1/5] Converting PDF to Markdown...")

    converter = PDFToMarkdownConverter()

    markdown_file = converter.convert_pdf(
        pdf_path=pdf_path,
        output_dir="data/markdown"
    )

    print(f"Markdown created: {markdown_file}")

    # --------------------------------------------------
    # STEP 2: Markdown → Semantic Chunks
    # --------------------------------------------------

    print("\n[2/5] Creating semantic chunks...")

    chunks = chunk_markdown(
        markdown_file=markdown_file,
        embeddings=embeddings
    )

    print(
        f"Generated {len(chunks)} chunks "
        f"for {pdf_file.name}"
    )

    # --------------------------------------------------
    # STEP 3: Store embeddings in FAISS
    # --------------------------------------------------

    print("\n[3/5] Creating local vector index...")

    vector_store.upload_chunks(
        chunks=chunks,
        embeddings=embeddings,
        company=company,
        year=year,
        source_file=pdf_file.name
    )

    print("Chunks successfully stored in FAISS.")

    # --------------------------------------------------
    # STEP 4: RAG → Extract financial metrics
    # --------------------------------------------------

    print("\n[4/5] Extracting financial metrics...")

    retriever = Retriever(
        vectorstore=vector_store,
    )

    metrics = extract_financial_metrics(
        retriever=retriever,
        company=company,
        year=int(year) if year.isdigit() else None,
    )

    if metrics:
        print("Financial metrics extracted successfully.")

    else:
        print("No financial metrics were extracted.")

    # --------------------------------------------------
    # STEP 5: Save metrics to PostgreSQL
    # --------------------------------------------------

    print("\n[5/5] Saving metrics to PostgreSQL...")

    if metrics:

        save_metrics(
            company=company,
            year=int(year) if year.isdigit() else None,
            metrics=metrics
        )

        print("Metrics saved successfully.")

    print(
        f"\nFinished ingestion for {pdf_file.name}\n"
    )


def ingest_directory(input_dir: str) -> None:
    """
    Ingest all PDFs from a directory.

    Uses completely local/free embeddings:

        sentence-transformers/all-MiniLM-L6-v2

    No Azure OpenAI required.
    """

    # --------------------------------------------------
    # LOCAL EMBEDDING MODEL
    # --------------------------------------------------

    print("Loading local embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    print("Embedding model loaded!")

    # --------------------------------------------------
    # LOCAL VECTOR DATABASE
    # --------------------------------------------------

    print("Initializing FAISS vector store...")

    vector_store = FAISSVectorStore(
        embeddings=embeddings
    )

    print("FAISS initialized!")

    # --------------------------------------------------
    # FIND PDFs
    # --------------------------------------------------

    pdf_files = list(
        Path(input_dir).glob("*.pdf")
    )

    print(
        f"\nFound {len(pdf_files)} PDF(s) "
        f"in {input_dir}"
    )

    if not pdf_files:
        print("No PDF files found.")
        return

    # --------------------------------------------------
    # INGEST EACH PDF
    # --------------------------------------------------

    for pdf_file in pdf_files:

        ingest_document(
            pdf_path=str(pdf_file),
            embeddings=embeddings,
            vector_store=vector_store
        )


if __name__ == "__main__":

    ingest_directory(
        "data/raw_pdfs"
    )