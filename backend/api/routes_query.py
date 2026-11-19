
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.queries import QueryRequest
from backend.orchestration.orchestrator import answer_query
from backend.database.connection import get_db
from backend.database.models import User
from backend.security.auth import get_current_user

router = APIRouter(tags=["queries"])


@router.post("/query")
def query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return answer_query(
        question=request.question,
        conversation_id=request.conversation_id,
        user_id=current_user.id,
        db=db,
        document_id=request.document_id,
    )
