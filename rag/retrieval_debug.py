from types import SimpleNamespace

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from llm.ollama_openai import get_structured_completion
from vectorstore.faiss_store import FAISSVectorStore

load_dotenv()


class FinancialMetrics(BaseModel):
    revenue: str | int | None = Field(None, alias="Revenue")
    net_income: str | int | None = Field(None, alias="Net Income")
    operating_income: str | int | None = Field(None, alias="Operating Income")
    cash_flow: str | int | None = Field(
        None,
        alias="Cash Flow from Operating Activities"
    )
    total_assets: str | int | None = Field(None, alias="Total Assets")
    total_liabilities: str | int | None = Field(None, alias="Total Liabilities")
    risk_factors: str | list | None = Field(
        None,
        alias="Top Risk Factors"
    )
    growth_drivers: str | list | None = Field(
        None,
        alias="Top Growth Drivers"
    )


class Retriever:
    """
    Retriever for the local FAISS vector store.
    """

    def __init__(self, vector_store: FAISSVectorStore):
        self.vector_store = vector_store

    def invoke(
        self,
        query: str,
        company: str | None = None,
        year: int | None = None,
        top_k: int = 20
    ) -> list:
        """
        Retrieve relevant chunks from local FAISS.
        """

        documents = self.vector_store.search(
            query=query,
            top_k=top_k,
            company=company,
            year=year
        )

        return [
            SimpleNamespace(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
            for doc in documents
        ]


def retrieve_context(
    retriever: Retriever,
    company: str,
    year: int
) -> str:
    """
    Retrieve broad financial context from the local vector store.
    """

    query = f"""
Annual report financial statements,
income statement,
balance sheet,
cash flow statement,
risks,
growth drivers,
financial performance
for {company} fiscal year {year}
"""

    documents = retriever.invoke(
        query=query,
        company=company,
        year=year,
        top_k=20
    )

    return "\n\n".join(
        doc.page_content
        for doc in documents
    )


def build_extraction_prompt(
    company: str,
    year: int,
    context: str
) -> str:
    """
    Build KPI extraction prompt.
    """

    return f"""
You are an expert financial analyst.

Company: {company}
Year: {year}

Context:
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

Instructions:

- Use ONLY the provided context.
- Do NOT use outside knowledge.
- Return null if information is unavailable.
- Financial values must match the report exactly.
- Preserve units such as millions or billions.
- Preserve the currency.
- Risk factors should be concise.
- Growth drivers should be concise.
- Return valid JSON only.
"""


def extract_financial_metrics(
    retriever: Retriever,
    company: str,
    year: int
) -> dict:
    """
    Extract financial KPIs using RAG + local Ollama.
    """

    context = retrieve_context(
        retriever=retriever,
        company=company,
        year=year
    )

    if not context.strip():
        print(
            f"[warning] No context retrieved for "
            f"{company} {year}"
        )
        return {}

    print(
        f"[debug] Retrieved context length: "
        f"{len(context)} characters"
    )

    prompt = build_extraction_prompt(
        company=company,
        year=year,
        context=context
    )

    metrics = get_structured_completion(
        prompt=prompt,
        response_model=FinancialMetrics
    )

    return metrics.model_dump(by_alias=True)


def main() -> None:
    company = "Apple"
    year = 2024

    # Load the local FAISS vector store
    vector_store = FAISSVectorStore(
        embeddings=None
    )

    # Create retriever
    retriever = Retriever(
        vector_store=vector_store
    )

    # Extract KPIs
    results = extract_financial_metrics(
        retriever=retriever,
        company=company,
        year=year
    )

    print(
        f"\nExtracted KPIs for "
        f"{company} {year}\n"
    )

    for key, value in results.items():
        print(f"{key}:")
        print(value)
        print("-" * 80)

    # Save to PostgreSQL
    from database.save_metrics import save_metrics

    save_metrics(
        company=company,
        year=year,
        metrics=results
    )


if __name__ == "__main__":
    main()