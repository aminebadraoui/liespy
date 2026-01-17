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
    candidates: List[str]
    results: Dict[str, Any]

# Initialize Real LLM (Perplexity via OpenAI-compatible API)

llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    temperature=0.1
)

def classify_claims(state: ScanState):
    candidates = state["candidates"]
    if not candidates:
        return {"results": {"page_risk": "low", "trust_score": 100, "summary": "No risky content found.", "claims": []}}

    # Construct Prompt
    candidates_text = "\n".join([f"- {c}" for c in candidates])
    
    system_prompt = """
    You are an expert fact-checker for older adults. 
    Analyze the provided text candidates from a webpage.
    Identify any CLAIMS that are:
    1. Health misinformation (fake cures, anti-science).
    2. Financial scams (guaranteed returns, immediate wealth).
    3. Urgent pressure tactics (limited time, act now).
    4. Deceptive Marketing (advertorials masquerading as news/reviews, fake endorsements).
    
    Return a JSON object with this structure:
    {
        "page_risk": "low" | "medium" | "high",
        "trust_score": 0 to 100 (integer),
        "summary": "Start with 'This page seems...' or similar. Keep it under 15 words.",
        "claims": [
            {
                "text": "The exact text of the claim",
                "risk_level": "medium" | "high",
                "category": "Health" | "Financial" | "Urgency" | "Deceptive" | "Other",
                "explanation": "A simple, clear explanation of why this is misleading.",
                "confidence": 0.0 to 1.0
            }
        ]
    }
    
    If no risky claims are found, return {"page_risk": "low", "trust_score": 90, "summary": "This page appears to be safe.", "claims": []}.
    """
    
    user_message = f"Here are the text snippets to analyze:\n{candidates_text}"
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        # Parse JSON
        content = response.content
        # Simple cleanup if the model adds markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content.strip())
        scan_result = ScanResult(**data)
        return {"results": scan_result.model_dump()}
        
    except Exception as e:
        print(f"LLM Error: {e}")
        # Fallback for error
    except Exception as e:
        print(f"LLM Error: {e}")
        # Fallback for error
        return {"results": {"page_risk": "unknown", "trust_score": 50, "summary": "Analysis failed.", "claims": []}}

# Define the graph
workflow = StateGraph(ScanState)
# Skip filter node for now, standard pass-through
workflow.add_node("classify", classify_claims)

workflow.set_entry_point("classify")
workflow.add_edge("classify", END)

app_pipeline = workflow.compile()

async def run_page_scan(candidates: List[str]) -> ScanResult:
    inputs = {"candidates": candidates, "results": {}}
    output = await app_pipeline.ainvoke(inputs)
    return ScanResult(**output["results"])

async def run_text_scan(text: str) -> ScanResult:
    return await run_page_scan([text])
