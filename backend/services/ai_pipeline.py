from typing import List, Dict, Any, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from backend.api.schemas import ScanResult, Claim

# Mocking LLM for now, in production use ChatOpenAI or similar
class MockLLM:
    def invoke(self, messages):
        # This simulates the LLM response
        content = """
        {
            "page_risk": "high",
            "claims": [
                {
                    "text": "This pill cures all cancer instantly.",
                    "risk": "high",
                    "category": "Health",
                    "explanation": "No single pill cures all cancer. This is a dangerous medical claim.",
                    "confidence": 0.95
                }
            ]
        }
        """
        return type('obj', (object,), {'content': content})

llm = MockLLM()

class ScanState(TypedDict):
    candidates: List[str]
    results: Dict[str, Any]

def filter_candidates(state: ScanState):
    # Logic to filter out irrelevant candidates
    # In real impl, use LLM or heuristics
    return {"candidates": state["candidates"]}

def classify_claims(state: ScanState):
    # Call LLM to classify
    # mock response creation
    claims = []
    for candidate in state["candidates"]:
        # Logic to skip some
        if "cancer" in candidate:
             claims.append(Claim(
                 text=candidate,
                 risk_level="high",
                 category="Health",
                 explanation="Medical claim without evidence.",
                 confidence=0.9
             ))
    
    result = ScanResult(
        page_risk="high" if claims else "low",
        claims=claims
    )
    return {"results": result.model_dump()}

# Define the graph
workflow = StateGraph(ScanState)
workflow.add_node("filter", filter_candidates)
workflow.add_node("classify", classify_claims)

workflow.set_entry_point("filter")
workflow.add_edge("filter", "classify")
workflow.add_edge("classify", END)

app_pipeline = workflow.compile()

async def run_page_scan(candidates: List[str]) -> ScanResult:
    inputs = {"candidates": candidates, "results": {}}
    output = await app_pipeline.ainvoke(inputs)
    return ScanResult(**output["results"])

async def run_text_scan(text: str) -> ScanResult:
    # Simplified single text scan
    # Reusing the same pipeline logic for simplicity in this artifact
    return await run_page_scan([text])
