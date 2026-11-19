
from fastapi import APIRouter, Depends

from backend.database.models import User
from backend.security.auth import get_current_user

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def analytics_summary(
    current_user: User = Depends(get_current_user),
):
    # Placeholder until query and feedback logging are implemented.
    return {
        "total_queries": 0,
        "feedback_count": 0,
        "status": "not_yet_persisted",
        "user_id": current_user.id,
    }
