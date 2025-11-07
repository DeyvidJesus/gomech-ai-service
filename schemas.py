from pydantic import BaseModel
from typing import Optional, List, Dict

class VideoResult(BaseModel):
    title: str
    video_id: str
    iframe_url: str
    thumbnail: str
    channel: str

class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str
    user_id: int

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None
    videos: Optional[List[VideoResult]] = []