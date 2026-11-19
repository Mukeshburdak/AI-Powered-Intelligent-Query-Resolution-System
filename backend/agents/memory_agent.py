
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import ConversationMessage


class MemoryAgent:
    """Store and retrieve conversation context for an authenticated user."""

    def get_context(
        self,
        conversation_id: str | None,
        user_id: int,
        db: Session,
        limit: int = 10,
    ) -> list[dict]:
        if not conversation_id:
            return []

        statement = (
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.user_id == user_id,
            )
            .order_by(ConversationMessage.id.desc())
            .limit(limit)
        )

        messages = list(db.scalars(statement).all())
        messages.reverse()

        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

    def save_message(
        self,
        conversation_id: str,
        user_id: int,
        role: str,
        content: str,
        db: Session,
    ) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Role must be 'user' or 'assistant'.")

        message = ConversationMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
        )

        db.add(message)
        db.commit()
