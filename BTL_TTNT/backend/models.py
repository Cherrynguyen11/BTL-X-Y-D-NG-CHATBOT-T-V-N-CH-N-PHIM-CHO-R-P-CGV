from pydantic import BaseModel
from typing import Optional, List, Any

class ChatRequest(BaseModel):
    message: str
    gemini_key: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    entities: dict
    suggested_movies: List[Any] = []
    showtimes: List[Any] = []
    quick_replies: List[str] = []
    engine_mode: str  # "Gemini LLM (RAG)" hoặc "Local AI Engine"

class RecommendRequest(BaseModel):
    genre: Optional[str] = None
    audience: Optional[str] = None
    format: Optional[str] = None
    keywords: Optional[str] = None

class KeyConfigRequest(BaseModel):
    api_key: str

class BookingRequest(BaseModel):
    movie_id: str
    cinema_id: str
    showtime: str
    format: str
    seats: List[str]
    customer_name: Optional[str] = "Khách Hàng CGV"
    customer_phone: Optional[str] = "0900000000"
