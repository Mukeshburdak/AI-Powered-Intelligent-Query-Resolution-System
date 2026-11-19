from pydantic import BaseModel

class DocumentUploadResponse(BaseModel):
    message: str
    filename: str
    characters: int
    chunks_created: int
    status: str
