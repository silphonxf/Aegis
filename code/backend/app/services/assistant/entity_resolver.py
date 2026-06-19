from __future__ import annotations

import re
from typing import Any, Dict, Optional

import app.db.session as db_session_module
from app.models.system import System


NOISE_PREFIXES = [
    "帮我看看",
    "帮我看下",
    "帮我看",
    "帮我查一下",
    "帮我查下",
    "帮我查",
    "帮我查询",
    "帮我为",
    "请帮我看看",
    "请帮我看",
    "请帮我查",
    "给我看一下",
    "给我看下",
    "给我看",
    "给我查",
    "麻烦帮我看",
    "麻烦帮我查",
    "看看",
    "查一下",
    "查下",
    "查询",
    "查看",
    "看下",
    "看一下",
]

NOISE_SUFFIXES = [
    "的系统状态",
    "系统状态",
    "最近巡检记录",
    "最近巡检",
    "巡检记录",
    "最近自检记录",
    "最近自检",
    "自检记录",
    "发起重启审批",
    "重启审批",
    "审批",
    "状态",
]

REFERENCE_WORDS = {"这个系统", "该系统", "它", "这个", "这个业务系统"}
SYSTEM_SEGMENT_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9_-]{2,40}?系统)")
SYSTEM_LIST_PHRASES = {"有哪些系统", "有哪几个系统", "系统列表", "系统清单", "接入了哪些系统", "已接入系统"}


class EntityResolver:
    def _normalize_candidate(self, text: str) -> str:
        value = (text or "").strip()
        changed = True
        while changed and value:
            changed = False
            for prefix in NOISE_PREFIXES:
                if value.startswith(prefix):
                    value = value[len(prefix):].strip()
                    changed = True
            for suffix in NOISE_SUFFIXES:
                if value.endswith(suffix):
                    value = value[: -len(suffix)].strip()
                    changed = True
        return value.strip("，。；：:、 让我给把将")

    def _looks_like_system_list_query(self, text: str) -> bool:
        value = (text or "").strip()
        return any(phrase in value for phrase in SYSTEM_LIST_PHRASES)

    def _find_system_by_name(self, raw_name: str) -> Optional[Dict[str, Any]]:
        candidate = self._normalize_candidate(raw_name)
        if not candidate or self._looks_like_system_list_query(candidate):
            return None

        db = db_session_module.SessionLocal()
        try:
            exact = db.query(System).filter(System.name == candidate).order_by(System.id.asc()).first()
            if exact:
                return {"system_id": exact.id, "system_name": exact.name}

            fuzzy = db.query(System).filter(System.name.like(f"%{candidate}%")).order_by(System.id.asc()).first()
            if fuzzy:
                return {"system_id": fuzzy.id, "system_name": fuzzy.name}
            return None
        finally:
            db.close()

    def _extract_system_segment(self, text: str) -> Optional[str]:
        match = SYSTEM_SEGMENT_RE.search(text or "")
        if not match:
            return None
        return self._normalize_candidate(match.group(1))

    def resolve(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        route_arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = (message or "").strip()
        context = context or {}
        args = dict(route_arguments or {})

        if text in REFERENCE_WORDS or any(word in text for word in REFERENCE_WORDS):
            if context.get("last_system_name"):
                args["system_name"] = context.get("last_system_name")
            if context.get("last_system_id"):
                args["system_id"] = context.get("last_system_id")
            return args

        raw_name = args.get("system_name")
        if raw_name:
            matched = self._find_system_by_name(raw_name)
            if matched:
                args.update(matched)
                return args

        extracted = self._extract_system_segment(text)
        if extracted and not self._looks_like_system_list_query(extracted):
            matched = self._find_system_by_name(extracted)
            if matched:
                args.update(matched)
                return args
            args["system_name"] = extracted
            return args

        matched = self._find_system_by_name(text)
        if matched:
            args.update(matched)
            return args

        normalized = self._normalize_candidate(text)
        if normalized and normalized != text and not self._looks_like_system_list_query(normalized):
            matched = self._find_system_by_name(normalized)
            if matched:
                args.update(matched)
                return args
            args["system_name"] = normalized

        return args


entity_resolver = EntityResolver()
