from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    generator,
    query_analyzer,
    query_rewriter,
    reflection,
    reranker_node,
    retriever,
    route_after_analyzer,
    route_after_reflection,
)
from app.graph.state import GraphState


def build_workflow():
    workflow = StateGraph(GraphState)
    workflow.add_node("query_analyzer", query_analyzer)
    workflow.add_node("query_rewriter", query_rewriter)
    workflow.add_node("retriever", retriever)
    workflow.add_node("reranker", reranker_node)
    workflow.add_node("generator", generator)
    workflow.add_node("reflection", reflection)

    workflow.add_edge(START, "query_analyzer")
    workflow.add_conditional_edges(
        "query_analyzer",
        route_after_analyzer,
        {
            "retriever": "query_rewriter",
            "generator": "generator",
        },
    )
    workflow.add_edge("query_rewriter", "retriever")
    workflow.add_edge("retriever", "reranker")
    workflow.add_edge("reranker", "generator")
    workflow.add_edge("generator", "reflection")
    workflow.add_conditional_edges(
        "reflection",
        route_after_reflection,
        {
            "query_rewriter": "query_rewriter",
            "retriever": "retriever",
            "end": END,
        },
    )

    return workflow.compile()


_workflow_instance = None


def get_workflow():
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = build_workflow()
    return _workflow_instance
