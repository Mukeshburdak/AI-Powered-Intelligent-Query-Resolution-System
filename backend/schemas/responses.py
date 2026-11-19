from pydantic import BaseModel

class SourceItem(BaseModel):
    filename: str
    chunk_index: int | None = None
    text: str | None = None

class QueryResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceItem] = []
    confidence: float = 0.0
    needs_clarification: bool = False
