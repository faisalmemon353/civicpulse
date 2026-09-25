from fastapi import APIRouter, Response

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats(response: Response):
    # TODO: replace with real Redis-cached aggregates in Step 9
    response.headers["X-Cache"] = "MISS"
    return {"by_category": {}, "by_priority": {}}