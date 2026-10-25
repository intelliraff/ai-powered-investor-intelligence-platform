import json

from sqlalchemy import text

from database.postgres_sql import get_engine


def _to_text(value) -> str | None:
    """
    Convert an extracted metric into a PostgreSQL-friendly string.

    Handles:
        - None
        - strings
        - integers/floats
        - lists
        - dictionaries
    """

    if value is None:
        return None

    if isinstance(value, list):
        return "\n".join(
            str(item)
            for item in value
        )

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False
        )

    return str(value)


def save_metrics(
    company: str,
    year: int,
    metrics: dict
) -> None:
    """
    Save extracted financial metrics to PostgreSQL.

    Args:
        company:
            Company name.

        year:
            Fiscal year.

        metrics:
            Financial metrics returned by the RAG/LLM pipeline.
    """

    engine = get_engine()

    query = """
    INSERT INTO financial_metrics (
        company,
        year,
        revenue,
        net_income,
        operating_income,
        cash_flow,
        total_assets,
        total_liabilities,
        risk_factors,
        growth_drivers
    )
    VALUES (
        :company,
        :year,
        :revenue,
        :net_income,
        :operating_income,
        :cash_flow,
        :total_assets,
        :total_liabilities,
        :risk_factors,
        :growth_drivers
    );
    """

    # Support both:
    #
    # {
    #     "Revenue": "...",
    #     "Net Income": "..."
    # }
    #
    # and:
    #
    # {
    #     "revenue": "...",
    #     "net_income": "..."
    # }

    revenue = metrics.get("Revenue")
    if revenue is None:
        revenue = metrics.get("revenue")

    net_income = metrics.get("Net Income")
    if net_income is None:
        net_income = metrics.get("net_income")

    operating_income = metrics.get("Operating Income")
    if operating_income is None:
        operating_income = metrics.get("operating_income")

    cash_flow = metrics.get(
        "Cash Flow from Operating Activities"
    )
    if cash_flow is None:
        cash_flow = metrics.get("cash_flow")

    total_assets = metrics.get("Total Assets")
    if total_assets is None:
        total_assets = metrics.get("total_assets")

    total_liabilities = metrics.get("Total Liabilities")
    if total_liabilities is None:
        total_liabilities = metrics.get(
            "total_liabilities"
        )

    risk_factors = metrics.get("Top Risk Factors")
    if risk_factors is None:
        risk_factors = metrics.get("risk_factors")

    growth_drivers = metrics.get("Top Growth Drivers")
    if growth_drivers is None:
        growth_drivers = metrics.get("growth_drivers")

    params = {
        "company": company,
        "year": str(year),

        "revenue": _to_text(revenue),
        "net_income": _to_text(net_income),
        "operating_income": _to_text(operating_income),
        "cash_flow": _to_text(cash_flow),
        "total_assets": _to_text(total_assets),
        "total_liabilities": _to_text(total_liabilities),

        "risk_factors": _to_text(risk_factors),
        "growth_drivers": _to_text(growth_drivers),
    }

    with engine.begin() as connection:
        connection.execute(
            text(query),
            params
        )

    print(
        f"Successfully saved metrics "
        f"for {company} {year}"
    )


if __name__ == "__main__":

    sample_metrics = {
        "Revenue": "$391,035 million",

        "Net Income": "$93,736 million",

        "Operating Income": "$123,216 million",

        "Cash Flow from Operating Activities":
            "$118,254 million",

        "Total Assets": "$364,980 million",

        "Total Liabilities": "$308,030 million",

        "Top Risk Factors": [
            "Macroeconomic conditions including "
            "inflation, interest rates, and currency "
            "fluctuations could materially impact results.",

            "High competition with aggressive pricing, "
            "short product life cycles, and rapid "
            "technological changes.",

            "Dependence on single or limited sources "
            "for certain components, with potential "
            "supply shortages.",

            "Exposure to foreign exchange rate "
            "fluctuations impacting sales and margins.",

            "Legal and regulatory challenges."
        ],

        "Top Growth Drivers": [
            "Increased Services revenue from advertising, "
            "App Store, and cloud services.",

            "Higher Mac sales driven by increased "
            "laptop demand.",

            "Continued strong iPhone sales performance."
        ]
    }

    save_metrics(
        company="Apple",
        year=2024,
        metrics=sample_metrics
    )