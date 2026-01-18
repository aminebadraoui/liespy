from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

# --- Shared Models ---

class Claim(BaseModel):
    text: str
    category: str
    risk_level: str
    explanation: str
    confidence: float

class ScanResult(BaseModel):
    page_risk: str
    trust_score: int = Field(..., description="0-100 score, where 100 is highly credible and 0 is a scam.")
    summary: str = Field(..., description="A short, one-sentence commentary explaining the score.")
    claims: List[Claim]

# --- Requests ---

class PageScanRequest(BaseModel):
    url: Optional[str] = None
    candidates: List[str] # List of extracted sentences
    metadata: Dict[str, str] = {}
    indicators: List[str] = []
    force_refresh: bool = False
    only_check_cache: bool = False

class TextScanRequest(BaseModel):
    text: str
    url: Optional[str] = None

# --- Responses ---

class ScanChunkRequest(BaseModel):
    chunk: str
    metadata: Dict[str, str] = {}
    indicators: List[str] = []

class ScanAggregateRequest(BaseModel):
    verified_claims: List[Dict[str, Any]] # List of claims (partial dicts or Claim model dumps)
    metadata: Dict[str, str] = {}
    full_text_summary: str = Field(default="", description="Optional summary or full text context if available")

class ScanResponse(BaseModel):
    scan_id: UUID
    result: ScanResult
    created_at: datetime
    is_cached: bool = False
