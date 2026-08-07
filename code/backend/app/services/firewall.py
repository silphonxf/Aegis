from __future__ import annotations

import base64
import json
import threading
from ipaddress import IPv4Address, ip_address
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.firewall_config import FirewallRuntimeConfig, get_runtime_firewall_config


_TARGET_LOCKS: Dict[str, threading.Lock] = {}
_TARGET_LOCKS_GUARD = threading.Lock()


def _target_lock(key: str) -> threading.Lock:
    with _TARGET_LOCKS_GUARD:
        if key not in _TARGET_LOCKS:
            _TARGET_LOCKS[key] = threading.Lock()
        return _TARGET_LOCKS[key]


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
    try:
        parsed = ip_address(candidate)
    except ValueError as exc:
        raise FirewallError(f"非法 IP：{candidate}") from exc
    if not isinstance(parsed, IPv4Address):
        raise FirewallError("当前山石地址簿封禁仅支持 IPv4")
    return str(parsed)


class HillstoneRestClient:
    """Hillstone StoneOS REST client for TapeManage-style address-book blocking."""

    def __init__(self, config: Optional[FirewallRuntimeConfig] = None) -> None:
        runtime = config or get_runtime_firewall_config(None)
        self.target_code = runtime.target_code
        self.target_name = runtime.target_name
        self.is_test_target = runtime.is_test_target
        self.enabled = runtime.enabled
        self.scheme = runtime.scheme.strip() or "https"
        self.host = runtime.host.strip()
        self.port = runtime.port
        self.username = runtime.username
        self.password = runtime.password
        self.verify_ssl = runtime.verify_ssl
        self.timeout = runtime.timeout_seconds
        self.address_book_name = runtime.address_book_name.strip()
        self.addrbook_path = runtime.addrbook_path.strip() or "/api/addrbook"

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.host and self.username and self.password and self.address_book_name)

    def _require_config(self) -> None:
        if not self.enabled:
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

    def _addrbook_int(self, value: Any, default: int) -> int:
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_ip_entries(self, existing: Optional[Dict[str, Any]], ip: str) -> List[Dict[str, Any]]:
        return self._normalize_ip_entries_many(existing, [ip])

    def _normalize_ip_entries_many(
        self,
        existing: Optional[Dict[str, Any]],
        ips: List[str],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for item in (existing or {}).get("ip") or []:
            if not isinstance(item, dict):
                continue
            ip_addr = str(item.get("ip_addr") or item.get("ip") or "").strip()
            if not ip_addr:
                continue
            try:
                ip_addr = validate_block_ip(ip_addr)
            except FirewallError:
                continue
            if ip_addr in seen:
                continue
            seen.add(ip_addr)
            entries.append(
                {
                    "ip_addr": ip_addr,
                    "netmask": self._addrbook_int(item.get("netmask"), 32),
                    "flag": self._addrbook_int(item.get("flag"), 0),
                }
            )

        # Older docs/tests used member: ["1.2.3.4/32"]. Keep this fallback so
        # the client can migrate data returned by mixed StoneOS versions.
        for member in (existing or {}).get("member") or []:
            cidr = str(member).strip()
            if not cidr:
                continue
            ip_part, _, mask_part = cidr.partition("/")
            try:
                ip_addr = validate_block_ip(ip_part)
            except FirewallError:
                continue
            if ip_addr in seen:
                continue
            seen.add(ip_addr)
            entries.append(
                {
                    "ip_addr": ip_addr,
                    "netmask": self._addrbook_int(mask_part, 32),
                    "flag": 0,
                }
            )

        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                entries.append({"ip_addr": ip, "netmask": 32, "flag": 0})
        return entries

    def build_addrbook_payload(self, ip: str, reason: Optional[str], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.build_addrbook_payload_many([ip], reason, existing)

    def build_addrbook_payload_many(
        self,
        ips: List[str],
        reason: Optional[str],
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        current = existing or {}
        return {
            "is_ipv6": self._addrbook_int(current.get("is_ipv6"), 0),
            "type": self._addrbook_int(current.get("type"), 0),
            "name": str(current.get("name") or self.address_book_name),
            "description": str(current.get("description") or ""),
            "entry": list(current.get("entry") or []),
            "ip": self._normalize_ip_entries_many(current, ips),
            "range": list(current.get("range") or []),
            "host": list(current.get("host") or []),
            "wildcard": list(current.get("wildcard") or []),
            "country": list(current.get("country") or []),
        }

    def block_ips(self, ips: List[str], reason: Optional[str], dry_run: bool) -> Dict[str, Any]:
        normalized_ips = list(dict.fromkeys(validate_block_ip(ip) for ip in ips))
        if not normalized_ips:
            raise FirewallError("至少需要一个待封禁 IP")
        if dry_run:
            return {
                "status": "dry_run",
                "dry_run": True,
                "vendor": "hillstone",
                "target_code": self.target_code,
                "target_name": self.target_name,
                "is_test_target": self.is_test_target,
                "ips": normalized_ips,
                "firewall_host": self.host,
                "address_set": self.address_book_name,
                "request": {
                    "method": "LOGIN + GET + PUT + GET_VERIFY",
                    "url": self.addrbook_url(),
                    "body": self.build_addrbook_payload_many(normalized_ips, reason),
                },
                "message": "演练模式，未连接山石；真实执行将单次登录、单次合并更新并回读核验。",
            }

        self._require_config()
        lock_key = f"{self.host}:{self.port}:{self.address_book_name}"
        with _target_lock(lock_key):
            cookie = self._login()
            existing = self._fetch_addrbook(cookie)
            if not existing:
                raise FirewallClientError(f"山石地址簿不存在：{self.address_book_name}")
            before_entries = self._normalize_ip_entries_many(existing, [])
            before = {item["ip_addr"] for item in before_entries}
            added = [ip for ip in normalized_ips if ip not in before]
            response_body: Dict[str, Any] = {"success": True, "noop": True}
            http_status = 200
            if added:
                request_kwargs = self._request_kwargs(cookie)
                request_kwargs["data"] = json.dumps(
                    self.build_addrbook_payload_many(normalized_ips, reason, existing),
                    ensure_ascii=False,
                )
                response = requests.put(self.addrbook_url(), **request_kwargs)
                http_status = response.status_code
                try:
                    response.raise_for_status()
                except requests.RequestException as exc:
                    raise FirewallClientError(
                        f"调用山石地址簿批量封禁失败：{exc}; response={response.text[:300]}"
                    ) from exc
                try:
                    response_body = response.json()
                except ValueError:
                    response_body = {"raw": response.text[:500]}
                if isinstance(response_body, dict) and response_body.get("success") is False:
                    raise FirewallClientError(f"山石地址簿批量封禁失败：{response_body}")

            verified_book = self._fetch_addrbook(cookie)
            verified = {
                item["ip_addr"]
                for item in self._normalize_ip_entries_many(verified_book, [])
            }
            missing = [ip for ip in normalized_ips if ip not in verified]
            if missing:
                raise FirewallClientError(f"山石地址簿回读核验失败，缺少：{', '.join(missing)}")
            return {
                "status": "blocked",
                "dry_run": False,
                "vendor": "hillstone",
                "target_code": self.target_code,
                "target_name": self.target_name,
                "is_test_target": self.is_test_target,
                "ips": normalized_ips,
                "existing_ips": [ip for ip in normalized_ips if ip in before],
                "added_ips": added,
                "verified_ips": normalized_ips,
                "before_count": len(before),
                "after_count": len(verified),
                "firewall_host": self.host,
                "address_set": self.address_book_name,
                "http_status": http_status,
                "response": response_body,
                "message": "已永久加入山石地址簿并完成回读核验。",
            }

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
                "method": "LOGIN + GET + PUT",
                "url": self.addrbook_url(),
                "body": self.build_addrbook_payload(normalized_ip, reason),
            },
            "message": "dry_run=true，未调用山石防火墙；真实执行时会先登录，再查询地址簿并把 IP 合并到 ip 数组后整体 PUT 更新。",
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
        if not existing:
            raise FirewallClientError(f"山石地址簿不存在：{self.address_book_name}")
        method = "PUT"
        request_kwargs = self._request_kwargs(cookie)
        request_kwargs["data"] = json.dumps(self.build_addrbook_payload(ip, reason, existing), ensure_ascii=False)
        return method, requests.put(self.addrbook_url(), **request_kwargs)

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


def block_ip_with_firewall(ip: str, reason: Optional[str] = None, dry_run: bool = True, db: Optional[Session] = None) -> Dict[str, Any]:
    return HillstoneRestClient(get_runtime_firewall_config(db)).block_ip(ip=ip, reason=reason, dry_run=dry_run)


def block_ips_with_firewall(
    ips: List[str],
    reason: Optional[str] = None,
    dry_run: bool = True,
    db: Optional[Session] = None,
    target_code: Optional[str] = None,
) -> Dict[str, Any]:
    return HillstoneRestClient(get_runtime_firewall_config(db, target_code)).block_ips(
        ips=ips,
        reason=reason,
        dry_run=dry_run,
    )
