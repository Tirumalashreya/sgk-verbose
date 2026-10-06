from langgraph.graph import StateGraph, END, START
from graph.state import VerbaState
from agents.listener_agent import listener_agent
from agents.transcription_agent import transcription_agent
from agents.correction_agent import correction_agent
from agents.shloka_detect_agent import shloka_detect_agent
from agents.knowledge_structurer_agent import knowledge_structurer_agent
from agents.summary_agent import summary_agent
from agents.formatting_agent import formatting_agent
from agents.validation_agent import validation_agent
from agents.memory_agent import memory_agent

graph = StateGraph(VerbaState)

graph.add_node("listener",             listener_agent)
graph.add_node("transcription",        transcription_agent)
graph.add_node("correction",           correction_agent)       # deterministic term fixes only
graph.add_node("shloka_detector",      shloka_detect_agent)    # LLM selects verses, verified verbatim
graph.add_node("knowledge_structurer", knowledge_structurer_agent)
graph.add_node("summary",              summary_agent)
graph.add_node("formatting",           formatting_agent)       # code only — builds verbatim notes
graph.add_node("validation",           validation_agent)       # flags for manual review, no retry
graph.add_node("memory",               memory_agent)

# Pipeline flow
graph.add_edge(START,           "listener")
graph.add_edge("listener",      "transcription")
graph.add_edge("transcription", "correction")
# These three only read the transcript, so they run in parallel
graph.add_edge("correction",    "shloka_detector")
graph.add_edge("correction",    "knowledge_structurer")
graph.add_edge("correction",    "summary")
graph.add_edge(["shloka_detector", "knowledge_structurer", "summary"], "formatting")
graph.add_edge("formatting",    "validation")
graph.add_edge("validation",    "memory")
graph.add_edge("memory", END)

app = graph.compile()
