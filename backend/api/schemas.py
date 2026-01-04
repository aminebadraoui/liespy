from typing import List, Optional
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
    claims: List[Claim]

# --- Requests ---

class PageScanRequest(BaseModel):
    url: Optional[str] = None
    candidates: List[str] # List of extracted sentences

class TextScanRequest(BaseModel):
    text: str
    url: Optional[str] = None

# --- Responses ---

class ScanResponse(BaseModel):
    scan_id: UUID
    result: ScanResult
    created_at: datetime
