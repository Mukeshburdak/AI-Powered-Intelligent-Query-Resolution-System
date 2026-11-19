
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.database.models import User
from backend.security.auth import get_current_user

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    query_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


@router.post("/feedback")
def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    # TODO: Persist feedback to the analytics database.
    return {
        "accepted": True,
        "query_id": request.query_id,
        "rating": request.rating,
        "user_id": current_user.id,
    }
