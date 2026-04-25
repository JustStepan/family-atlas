from langgraph.graph import StateGraph, START, END

from src.agents.schemas import FamilyAtlasState
import src.agents.nodes as nd


def graph_builder():
    graph = StateGraph(FamilyAtlasState)
    graph.add_node("analyzer", nd.assembld_text_analyzer)
    graph.add_node("d_n_c_writer", nd.diary_note_calend_file_writer)
    graph.add_node("t_writer", nd.task_file_writer)
    graph.add_node("data_base_upd", nd.db_updater)
    graph.add_node("related", nd.find_ralatives)

    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "related")
    graph.add_conditional_edges(
        "related",
        nd.thread_router,
        {
            "diary": "d_n_c_writer",
            "notes": "d_n_c_writer",
            "calendar": "d_n_c_writer",
            "task": "t_writer",
        }
    )

    graph.add_edge("d_n_c_writer", "data_base_upd")
    graph.add_edge("t_writer", "data_base_upd")

    graph.add_edge("data_base_upd", END)

    return graph.compile()

