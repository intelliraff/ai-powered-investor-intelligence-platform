from sqlalchemy import text

from database.postgres_sql import get_engine


def get_metrics() -> list[dict]:
    """
    Retrieve the latest financial metrics for each
    company/year combination.
    """

    engine = get_engine()

    query = """
    SELECT
        id,
        company,
        year,
        revenue,
        net_income,
        operating_income,
        cash_flow,
        total_assets,
        total_liabilities,
        risk_factors,
        growth_drivers,
        created_at
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY company, year
                ORDER BY created_at DESC
            ) AS rn
        FROM financial_metrics
    ) t
    WHERE rn = 1
    ORDER BY company, year;
    """

    with engine.connect() as connection:
        result = connection.execute(text(query))

        rows = [
            dict(row._mapping)
            for row in result
        ]

    return rows


if __name__ == "__main__":
    metrics = get_metrics()

    print("\nFinancial Metrics:\n")

    for row in metrics:
        print("=" * 80)

        for key, value in row.items():
            print(f"{key}: {value}")