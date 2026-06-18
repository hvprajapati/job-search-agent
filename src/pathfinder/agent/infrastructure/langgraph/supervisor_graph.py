"""Supervisor Graph — compiles all nodes into the LangGraph StateGraph."""
from langgraph.graph import StateGraph, END
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.infrastructure.langgraph.nodes.guardrail import guardrail_node
from pathfinder.agent.infrastructure.langgraph.nodes.context_builder import context_builder_node
from pathfinder.agent.infrastructure.langgraph.nodes.intent_router_node import intent_router_node
from pathfinder.agent.infrastructure.langgraph.nodes.task_planner_node import task_planner_node
from pathfinder.agent.infrastructure.langgraph.nodes.tool_executor import tool_executor_node
from pathfinder.agent.infrastructure.langgraph.nodes.result_synthesizer import result_synthesizer_node
from pathfinder.agent.infrastructure.langgraph.nodes.quality_gate import quality_gate_node


def _build_graph() -> StateGraph:
    builder = StateGraph(SupervisorState)

    builder.add_node("guardrail", guardrail_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("task_planner", task_planner_node)
    builder.add_node("tool_executor", tool_executor_node)
    builder.add_node("result_synthesizer", result_synthesizer_node)
    builder.add_node("quality_gate", quality_gate_node)

    builder.set_entry_point("guardrail")
    builder.add_edge("guardrail", "context_builder")
    builder.add_edge("context_builder", "intent_router")

    def route_after_intent(state: SupervisorState) -> str:
        phase = state.get("agent_phase", "")
        if phase == "needs_clarification":
            return "result_synthesizer"
        if phase == "blocked":
            return END
        return "task_planner"

    builder.add_conditional_edges("intent_router", route_after_intent, {
        "result_synthesizer": "result_synthesizer",
        "task_planner": "task_planner",
        END: END,
    })

    builder.add_edge("task_planner", "tool_executor")
    builder.add_edge("tool_executor", "result_synthesizer")
    builder.add_edge("result_synthesizer", "quality_gate")

    def quality_decision(state: SupervisorState) -> str:
        phase = state.get("agent_phase", "")
        if phase == "revise":
            return "result_synthesizer"
        return END

    builder.add_conditional_edges("quality_gate", quality_decision, {
        "result_synthesizer": "result_synthesizer",
        END: END,
    })

    return builder


def compile_supervisor_graph():
    builder = _build_graph()
    graph = builder.compile()
    return graph.with_config(recursion_limit=15)


supervisor_graph = compile_supervisor_graph()
