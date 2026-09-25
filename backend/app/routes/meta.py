from fastapi import APIRouter

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers")
def get_providers():
    # TODO: replace with real provider registry + last-20 outcomes in Step 7
    return {"active_provider": "rules", "recent_outcomes": []}