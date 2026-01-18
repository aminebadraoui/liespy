from typing import List, Dict, Any, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from api.schemas import ScanResult, Claim

import json
import asyncio
from langchain_openai import ChatOpenAI
from core.config import settings

# Initialize Real LLM
llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    temperature=0.1
)

# --- Utilities ---

def split_text(text: str, chunk_size: int = 20000, overlap: int = 500) -> List[str]:
    """Splits text into larger chunks for processing."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# --- Agencies ---


def extract_json(text: str) -> Dict[str, Any]:
    """Robustly extracts JSON from LLM response text."""
    try:
        # 1. Try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract code block
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    # 3. Find first { and last }
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    
    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse extracted JSON: {e}")
    
    raise ValueError("No JSON object found in text")

# --- Agencies ---

async def extract_content(candidates: List[str]) -> str:
    """Extracts clean text from raw HTML/candidates."""
    if not candidates:
        return ""
        
    full_text = "\\n".join(candidates)
    
    system_prompt = """
    You are an expert content extractor. Your job is to take raw text from a webpage and extract the MAIN ARTICLE CONTENT.
    Ignore navigation, footers, and general site chrome.
    If it's a sales page, keep the sales copy.
    Return ONLY the cleaned text.
    """
    
    try:
        # We process extraction on the first X chars to avoid blowing context if it's huge, 
        # but realistically the client sends decent candidates.
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"RAW TEXT:\\n{full_text[:50000]}") 
        ])
        return response.content
    except Exception as e:
        print(f"Extraction Error: {e}")
        return full_text[:20000]

# Helper for retries
async def invoke_with_retry(messages, max_retries=3):
    """Invokes LLM with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt # 1s, 2s, 4s
                    print(f"Rate limit hit. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
            raise e
    raise Exception("Max retries exceeded")

async def identify_claims_in_chunk(chunk: str) -> List[str]:
    """Identifies potential claims in a specific text chunk."""
    system_prompt = """
    You are an expert investigative journalist. Identify specific CLAIMS in the text that match:
    1. Health claims (cures, treatments).
    2. Financial claims (money making, returns).
    3. Urgency claims (limited time).
    4. Trust/Authority claims (endorsements).
    
    Extract the EXACT sentences. Return a JSON object: {"claims": ["claim 1", "claim 2"]}
    """
    
    try:
        response = await invoke_with_retry([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"TEXT CHUNK:\\n{chunk}")
        ])
        
        content = response.content.strip()
        data = extract_json(content)
        return data.get("claims", [])
    except Exception as e:
        print(f"Identification Error: {e}")
        print(f"RAW IDENTIFICATION RESPONSE: {response.content if 'response' in locals() else 'None'}")
        return []

async def verify_chunk_claims(chunk: str, claims: List[str]) -> List[Dict[str, Any]]:
    """Verifies a list of claims against their chunk context."""
    if not claims:
        return []
        
    claims_text = "\\n- ".join(claims)
    
    system_prompt = """
    You are an expert fact-checker. Analyze the provided claims based on the text context.
    For each claim, determine if it is Misleading, Scam, or Legitimate.
    
    Return a JSON object with key "verified_claims":
    {
        "verified_claims": [
            {
                "text": "Claim text",
                "risk_level": "low" | "medium" | "high",
                "category": "Health" | "Financial" | "Urgency" | "Trust",
                "explanation": "Brief explanation...",
                "confidence": 0.0 to 1.0
            }
        ]
    }
    """
    
    try:
        response = await invoke_with_retry([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"CONTEXT:\\n{chunk}\\n\\nCLAIMS TO VERIFY:\\n- {claims_text}")
        ])
        
        content = response.content.strip()
        data = extract_json(content)
        return data.get("verified_claims", [])
    except Exception as e:
        print(f"Verification Error: {e}")
        print(f"RAW VERIFICATION RESPONSE: {response.content if 'response' in locals() else 'None'}")
        return []


async def analyze_aggregated_results(all_claims: List[Dict[str, Any]], full_text_summary: str) -> ScanResult:
    """Calculates final score and summary based on all verified claims."""
    
    claims_dump = json.dumps(all_claims, indent=2)
    
    system_prompt = """
    You are the Chief Risk Officer. Analyze the list of verified claims from a webpage scan.
    
    Your Goal:
    1. specific: Calculate a 'trust_score' (0-100). 100 is perfectly safe, 0 is a definite scam.
    2. Determine overall 'page_risk' (low, medium, high).
    3. Write a short 'summary' (max 2 sentences) explaining the verdict.
    
    Return JSON matching ScanResult (minus the claims list, I will attach that later):
    {
        "page_risk": "low" | "medium" | "high",
        "trust_score": 85,
        "summary": "This page contains..."
    }
    """
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"VERIFIED CLAIMS:\\n{claims_dump}\\n\\nPAGE CONTEXT SUMMARY:\\n{full_text_summary[:5000]}")
        ])
        
        content = response.content.strip()
        data = extract_json(content)
        
        # We manually construct ScanResult to ensure we keep the claims
        return ScanResult(
            page_risk=data.get("page_risk", "medium"),
            trust_score=data.get("trust_score", 50),
            summary=data.get("summary", "Analysis complete."),
            claims=all_claims
        )
    except Exception as e:
        print(f"Aggregation Error: {e}")
        print(f"RAW AGGREGATION RESPONSE: {response.content if 'response' in locals() else 'None'}")
        return ScanResult(
            page_risk="unknown",
            trust_score=50,
            summary="Failed to generate final score.",
            claims=all_claims
        )


# --- Orchestrator ---

async def process_chunk(chunk: str) -> List[Dict[str, Any]]:
    """Pipeline for a single chunk: Identify -> Verify."""
    claims = await identify_claims_in_chunk(chunk)
    if not claims:
        return []
    verified = await verify_chunk_claims(chunk, claims)
    return verified

async def run_page_scan(candidates: List[str], metadata: Dict[str, str] = {}, indicators: List[str] = []) -> ScanResult:
    # 1. Extract clean text
    clean_text = await extract_content(candidates)
    
    # 2. Split into chunks
    chunks = split_text(clean_text)
    print(f"Split content into {len(chunks)} chunks.")
    
    # 3. Parallel Processing (Identify & Verify per chunk)
    tasks = [process_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    
    # 4. Flatten Results
    all_claims = []
    for res in results:
        all_claims.extend(res)
        
    print(f"Total claims found: {len(all_claims)}")
        
    # 5. Aggregate
    final_result = await analyze_aggregated_results(all_claims, clean_text)
    
    return final_result

async def run_text_scan(text: str) -> ScanResult:
    return await run_page_scan([text])

