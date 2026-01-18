from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import PageScanRequest, TextScanRequest, ScanResponse, ScanResult, Claim, ScanChunkRequest, ScanAggregateRequest
from services.ai_pipeline import run_page_scan, run_text_scan, process_chunk, analyze_aggregated_results
from db.models import User, Scan
from db.session import get_session
from uuid import uuid4
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/scan/page", response_model=ScanResponse)
async def scan_page(
    request: PageScanRequest, 
    session: AsyncSession = Depends(get_session)
):
    # Check for cache if not forcing refresh
    if not request.force_refresh:
        # Normalize URL (basic)
        normalized_url = request.url
        
        statement = select(Scan).where(Scan.url == normalized_url).order_by(Scan.created_at.desc())
        result = await session.execute(statement)
        cached_scan = result.scalars().first()
        
        if cached_scan:
            # Check age (optional, e.g. 24 hours)
            # if (datetime.utcnow() - cached_scan.created_at) < timedelta(hours=24):
            return ScanResponse(
                scan_id=cached_scan.id,
                result=cached_scan.result,
                created_at=cached_scan.created_at,
                is_cached=True
            )
    
    # If we only wanted to check cache, and found nothing
    if request.only_check_cache:
        raise HTTPException(status_code=404, detail="No cached scan found")

    # 1. Orchestrate AI Pipeline
    # TODO: Pass force_refresh to pipeline if needed
    result_data: ScanResult = await run_page_scan(
        candidates=request.candidates,
        metadata=request.metadata,
        indicators=request.indicators
    )
    
    # 2. Store in Supabase
    new_scan = Scan(
        url=request.url,
        result=result_data.model_dump(), # Convert Pydantic model to dict
        score=None, #/ TODO: Calculate score
        user_id=None #/ TODO: Link to user if auth enabled
    )
    session.add(new_scan)
    await session.commit()
    await session.refresh(new_scan)
    
    return ScanResponse(
        scan_id=new_scan.id,
        result=result_data,
        created_at=new_scan.created_at,
        is_cached=False
    )

@router.post("/scan/text", response_model=ScanResponse)
async def scan_text(request: TextScanRequest):
    result: ScanResult = await run_text_scan(request.text)
    scan_id = uuid4()
    
    return ScanResponse(
        scan_id=scan_id,
        result=result,
        created_at=datetime.utcnow(),
        is_cached=False
    )

@router.post("/scan/chunk")
async def scan_chunk_endpoint(request: ScanChunkRequest):
    # Process a single chunk: Identify & Verify
    # We use the pipeline's modular functions directly
    claims = await process_chunk(request.chunk)
    return {"verified_claims": claims}

@router.post("/scan/aggregate", response_model=ScanResponse)
async def scan_aggregate_endpoint(
    request: ScanAggregateRequest,
    session: AsyncSession = Depends(get_session)
):
    # Final aggregation step
    result_data: ScanResult = await analyze_aggregated_results(
        all_claims=request.verified_claims, 
        full_text_summary=request.full_text_summary
    )
    
    # Store in Supabase logic similar to scan_page
    # Note: We might want to construct a "fake" URL or use metadata to uniquely identify if needed, 
    # but for now we just store the result as a new scan entry.
    # Ideally, the client passes the URL in metadata for logging.
    url = request.metadata.get("url", "https://aggregated-result.com")
    
    new_scan = Scan(
        url=url,
        result=result_data.model_dump(),
        score=result_data.trust_score,
        user_id=None 
    )
    session.add(new_scan)
    await session.commit()
    await session.refresh(new_scan)
    
    return ScanResponse(
        scan_id=new_scan.id,
        result=result_data,
        created_at=new_scan.created_at,
        is_cached=False
    )

@router.post("/users/register")
async def register_user(
    anonymous_id: str,
    session: AsyncSession = Depends(get_session)
):
    # Upsert user
    statement = select(User).where(User.device_id == anonymous_id)
    result = await session.execute(statement)
    existing_user = result.scalars().first()
    
    if existing_user:
        existing_user.is_premium = True
        await session.commit()
        return {"status": "updated", "anonymous_id": anonymous_id}
    
    new_user = User(device_id=anonymous_id, is_premium=True)
    session.add(new_user)
    await session.commit()
    
    return {"status": "registered", "anonymous_id": anonymous_id}
