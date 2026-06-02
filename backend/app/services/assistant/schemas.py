from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    risk_level: str = "low"
    requires_confirmation: bool = False
    roles: List[str] = field(default_factory=list)
    handler: Optional[Callable[..., Dict[str, Any]]] = None
    arguments_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    intent: str
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    reply: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    cards: List[Dict[str, Any]] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
