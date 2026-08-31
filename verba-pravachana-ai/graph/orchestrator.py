from langgraph.graph import StateGraph, END, START
from graph.state import VerbaState
from agents.listener_agent import listener_agent
from agents.transcription_agent import transcription_agent
from agents.harmony_agent import harmony_agent
from agents.shloka_detect_agent import shloka_detect_agent
from agents.notes_generator_agent import notes_generator_agent
from agents.knowledge_structurer_agent import knowledge_structurer_agent
from agents.memory_agent import memory_agent
from agents.correction_agent import correction_agent

graph = StateGraph(VerbaState)

graph.add_node("listener",             listener_agent)
graph.add_node("transcription",        transcription_agent)
graph.add_node("correction",           correction_agent)
graph.add_node("harmony",              harmony_agent)          # melodic/chanting detection
graph.add_node("shloka_detector",      shloka_detect_agent)
graph.add_node("knowledge_structurer", knowledge_structurer_agent)
graph.add_node("notes_generator",      notes_generator_agent)
graph.add_node("memory",               memory_agent)

# Pipeline flow
graph.add_edge(START,          "listener")
graph.add_edge("listener",     "transcription")
graph.add_edge("transcription","correction")        # fix ASR errors before any analysis
graph.add_edge("correction",   "harmony")           # audio analysis runs after correction
graph.add_edge("harmony",      "shloka_detector")   # harmony data fed into shloka detection
graph.add_edge("harmony",      "knowledge_structurer")
graph.add_edge("shloka_detector",      "notes_generator")
graph.add_edge("knowledge_structurer", "notes_generator")
graph.add_edge("notes_generator", "memory")
graph.add_edge("memory", END)

app = graph.compile()
