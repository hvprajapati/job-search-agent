"""Agent API routes."""
import json
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathfinder.shared.infrastructure.database import get_session
from pathfinder.identity.presentation.dependencies import get_current_user
from pathfinder.identity.domain.entities import User
from pathfinder.agent.domain.state import SupervisorState
from pathfinder.agent.infrastructure.langgraph.supervisor_graph import supervisor_graph
from pathfinder.agent.infrastructure.tools.search_tools import register_search_tools
from pathfinder.agent.infrastructure.tools.match_tools import register_match_tools
from pathfinder.agent.infrastructure.tools.profile_tools import register_profile_tools

# Register tools on module load
register_search_tools()
register_match_tools()
register_profile_tools()

router = APIRouter(prefix="/v1/agent", tags=["Agent"])


@router.post("/execute")
async def agent_execute(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    user_message = body.get("message", "")
    stream = body.get("stream", False)
    session_id = str(uuid4())

    initial_state: SupervisorState = {
        "session_id": session_id,
        "user_id": str(current_user.id),
        "tier": current_user.tier.value,
        "user_message": user_message,
        "agent_phase": "starting",
        "call_id": str(uuid4()),
        "errors": [],
        "quality_gate_passes": 0,
        "execution_plan": [],
        "current_step": 0,
        "tool_results": {},
        "tool_errors": {},
        "final_response": None,
        "intent": None,
        "intent_confidence": 0.0,
        "clarification_question": None,
        "user_profile": None,
        "user_preferences": {},
        "user_resumes": [],
        "recent_history": [],
        "memory_context": "",
        "knowledge_context": "",
    }

    start_time = time.monotonic()

    if stream:
        async def event_stream():
            config = {"configurable": {"thread_id": session_id}}
            async for event in supervisor_graph.astream(initial_state, config):
                event_type = list(event.keys())[0] if event else "unknown"
                yield f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"
            latency = int((time.monotonic() - start_time) * 1000)
            yield f"event: done\ndata: {json.dumps({'latency_ms': latency})}\n\n"

        return StreamingResponse(
            event_stream(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        config = {"configurable": {"thread_id": session_id}}
        try:
            final_state = await supervisor_graph.ainvoke(initial_state, config)
        except Exception as graph_err:
            import logging
            logging.getLogger(__name__).error(f"Agent graph execution failed: {graph_err}")
            latency = int((time.monotonic() - start_time) * 1000)
            return {
                "data": {
                    "execution_id": str(uuid4()),
                    "session_id": session_id,
                    "response": "I'm having trouble processing your request right now. Please try again in a moment.",
                    "intent": "error",
                    "intent_confidence": 0.0,
                    "tool_results": {},
                    "latency_ms": latency,
                }
            }
        latency = int((time.monotonic() - start_time) * 1000)

        # Log episodic memory
        try:
            from pathfinder.shared.infrastructure.database import get_sessionmaker
            from pathfinder.agent.domain.memory.entities import EpisodicMemory
            from pathfinder.agent.infrastructure.memory.repositories import SqlEpisodicRepository
            maker = get_sessionmaker()
            async with maker() as mem_session:
                ep_repo = SqlEpisodicRepository(mem_session)
                ep = EpisodicMemory.record_agent_execution(
                    user_id=current_user.id, session_id=UUID(session_id),
                    call_id=UUID(initial_state["call_id"]),
                    intent=final_state.get("intent", "unknown"),
                    user_message=user_message,
                    tool_results=[{"step": k, "result": v} for k, v in final_state.get("tool_results", {}).items()],
                    final_response=final_state.get("final_response", ""),
                    latency_ms=latency, is_success=not final_state.get("errors"),
                )
                from pathfinder.agent.infrastructure.memory.models import EpisodicMemoryModel
                model = EpisodicMemoryModel(
                    id=ep.id, tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
                    user_id=ep.user_id, session_id=ep.session_id,
                    episode_type=ep.episode_type.value, actor=ep.actor, action=ep.action,
                    payload=ep.payload, importance_score=ep.importance.value,
                    context_summary=ep.context_summary, is_consolidated=False,
                    created_at=ep.created_at, recorded_at=ep.created_at, expires_at=ep.expires_at,
                )
                mem_session.add(model)
                await mem_session.commit()
        except Exception:
            pass  # Memory logging is best-effort

        return {
            "data": {
                "execution_id": str(uuid4()),
                "session_id": session_id,
                "response": final_state.get("final_response", ""),
                "intent": final_state.get("intent"),
                "intent_confidence": final_state.get("intent_confidence"),
                "tool_results": {k: v for k, v in final_state.get("tool_results", {}).items()},
                "latency_ms": latency,
            }
        }


@router.get("/executions")
async def list_executions(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from pathfinder.agent.infrastructure.persistence.models import AgentExecutionModel

    stmt = (
        select(AgentExecutionModel)
        .where(AgentExecutionModel.user_id == current_user.id)
        .order_by(AgentExecutionModel.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    models = result.scalars().all()

    return {
        "data": [
            {
                "execution_id": str(m.id),
                "call_id": str(m.call_id) if m.call_id else None,
                "agent_type": m.agent_type,
                "action_type": m.action_type,
                "is_success": m.is_success,
                "latency_ms": m.latency_ms,
                "tokens_used": m.tokens_used,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in models
        ],
        "meta": {"count": len(models), "limit": limit},
    }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from pathfinder.agent.infrastructure.persistence.models import AgentExecutionModel

    model = await session.get(AgentExecutionModel, execution_id)
    if model is None or model.user_id != current_user.id:
        from pathfinder.shared.domain.exceptions import NotFoundError
        raise NotFoundError("Execution not found")

    return {
        "data": {
            "execution_id": str(model.id),
            "call_id": str(model.call_id) if model.call_id else None,
            "session_id": str(model.session_id) if model.session_id else None,
            "agent_type": model.agent_type,
            "action_type": model.action_type,
            "input_context": model.input_context,
            "output_summary": model.output_summary,
            "tools_called": model.tools_called,
            "llm_model": model.llm_model,
            "llm_provider": model.llm_provider,
            "tokens_used": model.tokens_used,
            "latency_ms": model.latency_ms,
            "is_success": model.is_success,
            "error_message": model.error_message,
            "error_type": model.error_type,
            "retry_count": model.retry_count,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "completed_at": model.completed_at.isoformat() if model.completed_at else None,
        }
    }
