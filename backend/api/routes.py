from fastapi import APIRouter, HTTPException, Depends
from backend.api.schemas import PageScanRequest, TextScanRequest, ScanResponse, ScanResult, Claim
from backend.services.ai_pipeline import run_page_scan, run_text_scan
from backend.db.supabase import supabase
from uuid import uuid4
from datetime import datetime

router = APIRouter()

@router.post("/scan/page", response_model=ScanResponse)
async def scan_page(request: PageScanRequest):
    # 1. Orchestrate AI Pipeline
    result: ScanResult = await run_page_scan(request.candidates)
    
    # 2. Store in Supabase (simplified)
    # In real app, get user_id from auth context
    scan_id = uuid4()
    
    # mocked storage call
    # supabase.table("scans").insert({...})
    
    return ScanResponse(
        scan_id=scan_id,
        result=result,
        created_at=datetime.utcnow()
    )

@router.post("/scan/text", response_model=ScanResponse)
async def scan_text(request: TextScanRequest):
    result: ScanResult = await run_text_scan(request.text)
    scan_id = uuid4()
    
    return ScanResponse(
        scan_id=scan_id,
        result=result,
        created_at=datetime.utcnow()
    )

@router.post("/users/register")
async def register_user(anonymous_id: str):
    # supabase.table("users").insert({"anonymous_id": anonymous_id})
    return {"status": "registered", "anonymous_id": anonymous_id}
