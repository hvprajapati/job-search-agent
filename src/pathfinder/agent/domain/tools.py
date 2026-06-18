"""Tool Registry — wraps existing services as agent-callable tools."""
from __future__ import annotations
import time
from typing import Callable
from pathfinder.agent.domain.value_objects import ToolDefinition, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_definition(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_all_definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute(self, name: str, **kwargs) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(tool_name=name, success=False,
                            error=f"Unknown tool: '{name}'")
        start = time.monotonic()
        try:
            result_data = await handler(**kwargs)
            latency = int((time.monotonic() - start) * 1000)
            return ToolResult(tool_name=name, success=True,
                            data=result_data if isinstance(result_data, dict) else {"result": str(result_data)},
                            latency_ms=latency)
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return ToolResult(tool_name=name, success=False,
                            error=str(e)[:500], latency_ms=latency)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


tool_registry = ToolRegistry()
