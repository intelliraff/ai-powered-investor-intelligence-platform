import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel

from llm.ollama_openai import get_openai_client
from vectorstore.faiss_store import FAISSVectorStore, Retriever

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    company: str | None = None
    year: int | None = None


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Load the embedding model once and reuse it between requests.
    """

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )


@router.post("/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    try:
        vector_store = FAISSVectorStore(
            embeddings=get_embeddings(),
            index_path="data/vectorstore",
        )

        retriever = Retriever(
            vectorstore=vector_store,
        )

        documents = retriever.invoke(
            query=request.question,
            company=request.company,
            year=request.year,
            top_k=5,
        )

        context = "\n\n".join(
            document.page_content
            for document in documents
            if document.page_content
        )

        if not context.strip():
            return {
                "answer": (
                    "I could not find relevant information "
                    "in the uploaded financial reports."
                )
            }

        prompt = f"""
You are an expert financial analyst.

Answer the user's question using only the retrieved context.

Rules:

- Do not use outside knowledge.
- Do not invent financial information.
- If the answer is not in the context, say:
  "I do not have enough information in the uploaded reports."
- Preserve the original values, currencies, and units.
- Give a clear and concise answer.

Company filter: {request.company or "Not specified"}
Fiscal year filter: {request.year or "Not specified"}

Retrieved context:
{context}

User question:
{request.question}

Answer:
"""

        client = get_openai_client()
        model = os.getenv("OLLAMA_MODEL", "llama3.2")

        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        answer = response["message"]["content"]

        return {"answer": answer}

    except RuntimeError as exc:
        print(f"[chat] Runtime error: {exc}")

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(f"[chat] Error: {exc}")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc