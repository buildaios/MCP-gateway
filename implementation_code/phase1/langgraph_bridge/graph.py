from langgraph.graph import StateGraph, END
from .adapter import LangGraphState

def build_base_graph():
    """
    Returns a blank StateGraph initialized with the Fedora AI OS state schema.
    Specialist agents (CEO, Security) will add their own nodes and edges to this graph.
    """
    workflow = StateGraph(LangGraphState)
    return workflow
