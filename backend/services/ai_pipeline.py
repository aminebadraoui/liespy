from typing import List, Dict, Any, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from api.schemas import ScanResult, Claim

import json
import openai
from pydantic import ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.config import settings


class ScanState(TypedDict):
    candidates: List[str] # Input raw text chunks
    metadata: Dict[str, str]
    indicators: List[str]
    clean_text: str # Output of extractor
    extracted_claims: List[str] # Output of identifier
    results: Dict[str, Any] # Output of verifier

# Initialize Real LLM
llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    temperature=0.1
)

# Application of "Extraction" Agency
def extract_content(state: ScanState):
    raw_candidates = state.get("candidates", [])
    if not raw_candidates:
        return {"clean_text": ""}
        
    # Combine chunks for analysis
    # Limit to reasonable context window if needed, though most input will be filtered by client size limits
    full_text = "\n".join(raw_candidates)
    
    system_prompt = """
    You are an expert content extractor. Your job is to take raw text from a webpage and extract the MAIN ARTICLE CONTENT.
    Ignore:
    - Navigation menus
    - Footers
    - Related article links
    - Cookie warnings
    - General site chrome
    
    If the text appears to be a Landing Page or Sales Page (long form sales letter), keep the sales copy as it is the "content".
    
    Return ONLY the cleaned text. Do not add any preamble or markdown formatting like "Here is the text".
    """
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"RAW TEXT:\n{full_text[:200000]}") # Increased Safety cap for full HTML
        ])
        return {"clean_text": response.content}
    except Exception as e:
        print(f"Extraction Error: {e}")
        # Fallback to using raw text
        return {"clean_text": full_text[:10000]}

# Application of "Claim Identification" Agency
def identify_claims(state: ScanState):
    clean_text = state.get("clean_text", "")
    
    if not clean_text:
        return {"extracted_claims": []}
        
    system_prompt = """
    You are an expert investigative journalist. Your goal is to Identify specific CLAIMS in the text that match these categories:
    1. Health claims (cures, treatments, medical advice).
    2. Financial claims (returns, investments, money making).
    3. Urgency claims (limited time, act now).
    4. Trust/Authority claims (endorsements, "proven system").
    
    Extract the EXACT sentences or phrases. Do not classify or debunk them yet. Just list them.
    Return a JSON object with a single key "claims" containing a list of strings.
    """
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"TEXT:\n{clean_text}")
        ])
        
        # Parse JSON
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content.strip())
        claims = data.get("claims", [])
        return {"extracted_claims": claims}
        
    except Exception as e:
        print(f"Identification Error: {e}")
        return {"extracted_claims": []}

# Application of "Verification" Agency
def verify_claims(state: ScanState):
    clean_text = state.get("clean_text", "")
    extracted_claims = state.get("extracted_claims", [])
    metadata = state.get("metadata", {})
    indicators = state.get("indicators", [])
    
    metadata_text = json.dumps(metadata, indent=2)
    indicators_text = ", ".join(indicators)
    claims_text = "\n- ".join(extracted_claims)
    
    system_prompt = f"""
    You are an expert fact-checker. Analyze the identified claims from a webpage.
    
    Context:
    - Metadata: {metadata_text}
    - Indicators: {indicators_text}
    
    Your Task:
    1. Determine the overall Page Risk and Trust Score.
    2. For each extracted claim, analyze if it is Misleading, Scam, or Legitimate.
    
    Return a JSON object matching the ScanResult schema:
    {{
        "page_risk": "low" | "medium" | "high",
        "trust_score": 0 to 100,
        "summary": "Short summary...",
        "claims": [
            {{
                "text": "Claim text",
                "risk_level": "medium" | "high",
                "category": "Health"...,
                "explanation": "Why it is misleading...",
                "confidence": 0.0 to 1.0
            }}
        ]
    }}
    """
    
    # If no specific claims were found but text exists, do a general page-level analysis
    if not extracted_claims and clean_text:
         user_message = f"""
         No specific isolated claims found. Please analyze the Page Tone and Structure for risk.
         
         MAIN TEXT:
         {clean_text[:5000]}
         """
    else:
        user_message = f"""
        CLAIMS TO VERIFY:
        - {claims_text}
        
        FULL CONTEXT (for reference):
        {clean_text[:10000]}
        """
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        # Parse JSON
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content.strip())
        scan_result = ScanResult(**data)
        return {"results": scan_result.model_dump()}
        
    except Exception as e:
        print(f"Verification Error: {e}")
        # Log the failed content for debugging
        if 'content' in locals():
            print(f"Failed Content: {content[:500]}...") 
        return {"results": {"page_risk": "unknown", "trust_score": 50, "summary": "Verification failed due to AI response error.", "claims": []}}

# Define the graph
workflow = StateGraph(ScanState)
workflow.add_node("extract", extract_content)
workflow.add_node("identify", identify_claims)
workflow.add_node("verify", verify_claims)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "identify")
workflow.add_edge("identify", "verify")
workflow.add_edge("verify", END)

app_pipeline = workflow.compile()

async def run_page_scan(candidates: List[str], metadata: Dict[str, str] = {}, indicators: List[str] = []) -> ScanResult:
    inputs = {
        "candidates": candidates, 
        "metadata": metadata, 
        "indicators": indicators,
        "clean_text": "",
        "extracted_claims": [],
        "results": {}
    }
    output = await app_pipeline.ainvoke(inputs)
    return ScanResult(**output["results"])

async def run_text_scan(text: str) -> ScanResult:
    return await run_page_scan([text])
