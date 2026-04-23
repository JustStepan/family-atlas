from langgraph.graph import StateGraph, START, END

from src.agents.schemas import FamilyAtlasState
from src.agents.nodes import (
    assembld_text_analyzer,
    calendar_file_writer,
    diary_note_file_writer,
    find_ralatives,
    task_file_writer,
    thread_router
)


def graph_builder():
    graph = StateGraph(FamilyAtlasState)
    graph.add_node("analyzer", assembld_text_analyzer)
    graph.add_node("d_n_writer", diary_note_file_writer)
    graph.add_node("c_writer", calendar_file_writer)
    graph.add_node("t_writer", task_file_writer)
    graph.add_node("related", find_ralatives)

    graph.add_edge(START, "analyzer")
    graph.add_conditional_edges(
        "analyzer",
        thread_router,
        {
            "diary": "d_n_writer",
            "notes": "d_n_writer",
            "calendar": "c_writer",
            "task": "t_writer",
        }
    )

    graph.add_edge("d_n_writer", "related")
    graph.add_edge("c_writer", "related")
    graph.add_edge("t_writer", "related")

    graph.add_edge("related", END)

    return graph.compile()

