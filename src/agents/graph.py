from langgraph.graph import StateGraph, START, END

from src.agents.schemas import FamilyAtlasState
import src.agents.nodes as nd


def graph_builder():
    graph = StateGraph(FamilyAtlasState)
    graph.add_node("analyzer", nd.assembld_text_analyzer)
    graph.add_node("related", nd.find_relatives)
    graph.add_node("data_base_upd", nd.db_updater)

    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "related")
    graph.add_edge("related", "data_base_upd")
    graph.add_edge("data_base_upd", END)

    return graph.compile()