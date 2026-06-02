from __future__ import annotations

from typing import Dict, List, Optional

from .schemas import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[ToolSpec]:
        return list(self._tools.values())


registry = ToolRegistry()
