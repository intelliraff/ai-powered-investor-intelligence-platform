from fastapi import APIRouter

from database.metrics import get_metrics


router = APIRouter()


@router.get("/metrics")
def metrics_dashboard():
    """
    Return the latest financial metrics for
    each company and fiscal year.
    """

    try:
        return get_metrics()

    except Exception as exc:
        return {
            "error": str(exc)
        }