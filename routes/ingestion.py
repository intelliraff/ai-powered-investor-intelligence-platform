import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_huggingface import HuggingFaceEmbeddings

from vectorstore.faiss_store import FAISSVectorStore
from ingestion.ingest_documents import ingest_document


router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file name provided."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    upload_dir = Path("data/raw_pdfs")

    upload_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = upload_dir / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        print(
            f"[upload] Saved PDF: {file_path}"
        )

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        print(
            "[upload] Loaded local embedding model."
        )

        vector_store = FAISSVectorStore(
            embeddings=embeddings
        )

        print(
            "[upload] Initialized FAISS vector store."
        )


        ingest_document(
            pdf_path=str(file_path),
            embeddings=embeddings,
            vector_store=vector_store
        )

        print(
            f"[upload] Successfully ingested "
            f"{file.filename}"
        )

        return {
            "message": "Document uploaded and ingested successfully",
            "file_name": file.filename
        }

    except Exception as exc:

        print(
            f"[upload] Ingestion failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}"
        )

    finally:
        await file.close()