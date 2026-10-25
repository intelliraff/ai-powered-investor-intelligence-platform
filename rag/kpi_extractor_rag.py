from typing import Any

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel, Field

from database.save_metrics import save_metrics
from llm.ollama_openai import get_structured_completion
from vectorstore.faiss_store import FAISSVectorStore, Retriever

load_dotenv()


class FinancialMetrics(BaseModel):
    revenue: str | int | None = Field(
        default=None,
        alias="Revenue",
    )
    net_income: str | int | None = Field(
        default=None,
        alias="Net Income",
    )
    operating_income: str | int | None = Field(
        default=None,
        alias="Operating Income",
    )
    cash_flow: str | int | None = Field(
        default=None,
        alias="Cash Flow from Operating Activities",
    )
    total_assets: str | int | None = Field(
        default=None,
        alias="Total Assets",
    )
    total_liabilities: str | int | None = Field(
        default=None,
        alias="Total Liabilities",
    )
    risk_factors: str | list[str] | None = Field(
        default=None,
        alias="Top Risk Factors",
    )
    growth_drivers: str | list[str] | None = Field(
        default=None,
        alias="Top Growth Drivers",
    )


def retrieve_context(
    retriever: Retriever,
    company: str,
    year: int,
) -> str:
    """
    Retrieve relevant financial-report chunks from local FAISS.
    """

    query = f"""
Annual report financial statements
income statement
balance sheet
cash flow statement
revenue
net income
operating income
cash flow from operating activities
total assets
total liabilities
risk factors
growth drivers
financial performance
for {company} fiscal year {year}
"""

    documents = retriever.invoke(
        query=query,
        company=company,
        year=year,
        top_k=20,
    )

    return "\n\n".join(
        document.page_content
        for document in documents
        if document.page_content
    )


def build_extraction_prompt(
    company: str,
    year: int,
    context: str,
) -> str:
    """
    Build the prompt used by local Ollama/Llama 3.2.
    """

    return f"""
You are an expert financial analyst.

Company: {company}
Fiscal year: {year}

Retrieved context:
{context}

Extract the following information:

1. Revenue
2. Net Income
3. Operating Income
4. Cash Flow from Operating Activities
5. Total Assets
6. Total Liabilities
7. Top Risk Factors
8. Top Growth Drivers

Rules:

- Use only the retrieved context.
- Do not use outside knowledge.
- Do not invent missing values.
- Return null when information is unavailable.
- Preserve the exact currency and units from the report.
- Keep risk factors concise.
- Keep growth drivers concise.
- Return valid JSON matching the provided schema.
"""


def extract_financial_metrics(
    retriever: Retriever,
    company: str,
    year: int,
) -> dict[str, Any]:
    """
    Retrieve report context from FAISS and extract metrics with Ollama.
    """

    context = retrieve_context(
        retriever=retriever,
        company=company,
        year=year,
    )

    if not context.strip():
        print(
            f"[warning] No FAISS context found for "
            f"{company} {year}."
        )
        return {}

    print(
        f"[debug] Retrieved {len(context)} "
        f"context characters."
    )

    prompt = build_extraction_prompt(
        company=company,
        year=year,
        context=context,
    )

    metrics = get_structured_completion(
        prompt=prompt,
        response_model=FinancialMetrics,
    )

    return metrics.model_dump(by_alias=True)


def main() -> None:
    company = "Apple"
    year = 2024

    print("Loading local MiniLM embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )

    print("Loading local FAISS vector store...")

    vector_store = FAISSVectorStore(
        embeddings=embeddings,
        index_path="data/vectorstore",
    )

    retriever = Retriever(
        vectorstore=vector_store,
    )

    results = extract_financial_metrics(
        retriever=retriever,
        company=company,
        year=year,
    )

    if not results:
        print(
            f"No financial metrics were extracted "
            f"for {company} {year}."
        )
        return

    print(f"\nExtracted KPIs for {company} {year}\n")

    for key, value in results.items():
        print(f"{key}:")
        print(value)
        print("-" * 80)

    save_metrics(
        company=company,
        year=year,
        metrics=results,
    )

    print("Financial metrics saved to PostgreSQL.")


if __name__ == "__main__":
    main()