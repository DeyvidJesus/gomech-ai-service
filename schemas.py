from pydantic import BaseModel
from typing import Optional, List, Dict

class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None
    suggestions: Optional[List[str]] = None
    columns_by_type: Optional[Dict[str, List[str]]] = None