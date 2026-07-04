from __future__ import annotations

import base64
import json
from ipaddress import IPv4Address, ip_address
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from app.core.config import settings


class FirewallError(Exception):
    pass


class FirewallConfigError(FirewallError):
    pass


class FirewallClientError(FirewallError):
    pass


def validate_block_ip(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise FirewallError("IP 不能为空")
    parsed = ip_address(candidate)
    if not isinstance(parsed, IPv4Address):
        raise FirewallError("当前山石地址簿封禁仅支持 IPv4")
    return str(parsed)


class HillstoneRestClient:
    """Hillstone StoneOS REST client for TapeManage-style address-book blocking."""

    def __init__(self) -> None:
        self.scheme = settings.HILLSTONE_SCHEME.strip() or "https"
        self.host = settings.HILLSTONE_HOST.strip()
        self.port = settings.HILLSTONE_PORT
        self.username = settings.HILLSTONE_USERNAME
        self.password = settings.HILLSTONE_PASSWORD
        self.verify_ssl = settings.HILLSTONE_VERIFY_SSL
        self.timeout = settings.HILLSTONE_TIMEOUT_SECONDS
        self.address_book_name = settings.HILLSTONE_ADDRESS_BOOK_NAME.strip()
        self.addrbook_path = settings.HILLSTONE_ADDRBOOK_PATH.strip() or "/api/addrbook"

    @property
    def is_configured(self) -> bool:
        return bool(settings.HILLSTONE_ENABLED and self.host and self.username and self.password and self.address_book_name)

    def _require_config(self) -> None:
        if not settings.HILLSTONE_ENABLED:
            raise FirewallConfigError("山石防火墙 API 封禁未启用")
        missing = []
        if not self.host:
            missing.append("HILLSTONE_HOST")
        if not self.username:
            missing.append("HILLSTONE_USERNAME")
        if not self.password:
            missing.append("HILLSTONE_PASSWORD")
        if not self.address_book_name:
            missing.append("HILLSTONE_ADDRESS_BOOK_NAME")
        if missing:
            raise FirewallConfigError("缺少山石防火墙配置：" + ", ".join(missing))

    def _base_url(self) -> str:
        port = f":{self.port}" if self.port else ""
        return f"{self.scheme}://{self.host}{port}/rest"

    def login_url(self) -> str:
        return f"{self._base_url()}/api/login"

    def addrbook_url(self) -> str:
        path = self.addrbook_path if self.addrbook_path.startswith("/") else f"/{self.addrbook_path}"
        return f"{self._base_url()}{path}"

    def _login_payload(self) -> Dict[str, str]:
        return {
            "lang": "zh_CN",
            "userName": base64.b64encode((self.username or "").encode("utf-8")).decode("ascii"),
            "password": base64.b64encode((self.password or "").encode("utf-8")).decode("ascii"),
        }

    def build_addrbook_payload(self, ip: str, reason: Optional[str], existing: Optional[Dict[str, Any]] = None) -> Any:
        description = (reason or f"Aegis block {ip}")[:120]
        member = list((existing or {}).get("member") or [])
        cidr = f"{ip}/32"
        if cidr not in member:
            member.append(cidr)

        return [{"name": self.address_book_name, "member": member}]

    def dry_run_plan(self, ip: str, reason: Optional[str]) -> Dict[str, Any]:
        normalized_ip = validate_block_ip(ip)
        return {
            "status": "dry_run",
            "dry_run": True,
            "vendor": "hillstone",
            "ip": normalized_ip,
            "firewall_host": self.host,
            "address_set": self.address_book_name,
            "login": {
                "method": "POST",
                "url": self.login_url(),
                "body": {
                    "lang": "zh_CN",
                    "userName": "<base64(HILLSTONE_USERNAME)>",
                    "password": "<base64(HILLSTONE_PASSWORD)>",
                },
            },
            "request": {
                "method": "GET + PUT/POST",
                "url": self.addrbook_url(),
                "body": self.build_addrbook_payload(normalized_ip, reason),
            },
            "message": "dry_run=true，未调用山石防火墙；按 TapeManage 逻辑将 IP 加入指定地址簿。",
        }

    def _login(self) -> Dict[str, str]:
        response = requests.post(
            self.login_url(),
            data=json.dumps(self._login_payload(), ensure_ascii=False),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirewallClientError(f"山石防火墙登录请求失败：{exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise FirewallClientError("山石防火墙登录返回非 JSON") from exc

        if not body.get("success"):
            raise FirewallClientError(f"山石防火墙登录失败：{body}")

        rows = body.get("result") or []
        if not rows or not isinstance(rows[0], dict):
            raise FirewallClientError("山石防火墙登录返回缺少 token/cookie 信息")

        login_info = rows[0]
        cookie = {key: str(login_info[key]) for key in ("token", "role", "vsysId", "fromrootvsys") if key in login_info}
        if "token" not in cookie:
            raise FirewallClientError("山石防火墙登录返回缺少 token")
        cookie["username"] = self.username or ""
        return cookie

    def _request_kwargs(self, cookie: Dict[str, str]) -> Dict[str, Any]:
        return {
            "cookies": cookie,
            "headers": {"Content-Type": "application/json"},
            "timeout": self.timeout,
            "verify": self.verify_ssl,
        }

    def _fetch_addrbook(self, cookie: Dict[str, str]) -> Optional[Dict[str, Any]]:
        query = quote(json.dumps({"start": 0, "limit": 500}, separators=(",", ":")))
        response = requests.get(f"{self.addrbook_url()}?query={query}", **self._request_kwargs(cookie))
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirewallClientError(f"查询山石地址簿失败：{exc}; response={response.text[:300]}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise FirewallClientError("查询山石地址簿返回非 JSON") from exc

        if isinstance(body, dict) and body.get("success") is False:
            raise FirewallClientError(f"查询山石地址簿失败：{body}")

        for item in body.get("result") or []:
            if isinstance(item, dict) and item.get("name") == self.address_book_name:
                return item
        return None

    def _send_addrbook_update(self, cookie: Dict[str, str], ip: str, reason: Optional[str]) -> tuple[str, requests.Response]:
        existing = self._fetch_addrbook(cookie)
        method = "PUT" if existing else "POST"
        request_kwargs = self._request_kwargs(cookie)
        request_kwargs["data"] = json.dumps(self.build_addrbook_payload(ip, reason, existing), ensure_ascii=False)
        if existing:
            return method, requests.put(self.addrbook_url(), **request_kwargs)
        return method, requests.post(self.addrbook_url(), **request_kwargs)

    def block_ip(self, ip: str, reason: Optional[str], dry_run: bool) -> Dict[str, Any]:
        normalized_ip = validate_block_ip(ip)
        if dry_run:
            return self.dry_run_plan(normalized_ip, reason)

        self._require_config()
        cookie = self._login()
        method, response = self._send_addrbook_update(cookie, normalized_ip, reason)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirewallClientError(f"调用山石地址簿封禁失败：{exc}; response={response.text[:300]}") from exc

        try:
            response_body = response.json()
        except ValueError:
            response_body = {"raw": response.text[:500]}

        if isinstance(response_body, dict) and response_body.get("success") is False:
            raise FirewallClientError(f"山石地址簿封禁失败：{response_body}")

        return {
            "status": "blocked",
            "dry_run": False,
            "vendor": "hillstone",
            "ip": normalized_ip,
            "firewall_host": self.host,
            "address_set": self.address_book_name,
            "method": method,
            "url": self.addrbook_url(),
            "http_status": response.status_code,
            "response": response_body,
            "message": "已通过山石 StoneOS REST API 将 IP 加入指定地址簿。",
        }


def block_ip_with_firewall(ip: str, reason: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
    return HillstoneRestClient().block_ip(ip=ip, reason=reason, dry_run=dry_run)
