
from fastapi import APIRouter, Depends

from backend.database.models import User
from backend.security.auth import get_current_user

router = APIRouter(tags=["history"])


@router.get("/history/{conversation_id}")
def get_history(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):

    return {
        "conversation_id": conversation_id,
        "messages": [],
        "user_id": current_user.id,
    }
