import asyncio
from typing import TypedDict, Annotated, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.bundle.schema import AnalysisBundle
from app.narrative.nodes import (
    generate_exec_summary,
    generate_methodology,
    generate_brand_health,
    generate_weak_links,
    generate_takeaways
)

def reduce_dict(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer to merge dictionaries in the state."""
    if not left:
        return right
    if not right:
        return left
    return {**left, **right}

def reduce_list(left: List[Any], right: List[Any]) -> List[Any]:
    """Reducer to append lists in the state."""
    if not left:
        return right
    if not right:
        return left
    return left + right

class NarrativeState(TypedDict):
    bundle: AnalysisBundle
    use_llm: bool
    require_llm: bool
    sections: Annotated[Dict[str, str], reduce_dict]
    ppt_sections: Annotated[Dict[str, str], reduce_dict]
    errors: Annotated[List[Dict[str, str]], reduce_list]
    llm_metadata: Annotated[Dict[str, Any], reduce_dict]

def build_graph() -> StateGraph:
    builder = StateGraph(NarrativeState)
    
    # Add nodes
    builder.add_node("executive_summary", generate_exec_summary)
    builder.add_node("methodology", generate_methodology)
    builder.add_node("brand_health", generate_brand_health)
    builder.add_node("weak_links", generate_weak_links)
    builder.add_node("takeaways", generate_takeaways)
    
    # Parallel execution edges from START
    builder.add_edge(START, "executive_summary")
    builder.add_edge(START, "methodology")
    builder.add_edge(START, "brand_health")
    builder.add_edge(START, "weak_links")
    builder.add_edge(START, "takeaways")
    
    # Edges to END
    builder.add_edge("executive_summary", END)
    builder.add_edge("methodology", END)
    builder.add_edge("brand_health", END)
    builder.add_edge("weak_links", END)
    builder.add_edge("takeaways", END)
    
    return builder.compile()

graph = build_graph()

async def run_narrative_engine_async(
    bundle: AnalysisBundle,
    use_llm: bool = True,
    require_llm: bool = False,
) -> dict:
    """
    Run the compiled LangGraph narrative engine with parallel section nodes.
    """
    initial_state = {
        "bundle": bundle,
        "use_llm": use_llm,
        "require_llm": require_llm,
        "sections": {},
        "ppt_sections": {},
        "errors": [],
        "llm_metadata": {},
    }
    
    result = await graph.ainvoke(initial_state)
    return result


def run_narrative_engine(
    bundle: AnalysisBundle,
    use_llm: bool = True,
    require_llm: bool = False,
) -> dict:
    return asyncio.run(
        run_narrative_engine_async(
            bundle,
            use_llm=use_llm,
            require_llm=require_llm,
        )
    )
