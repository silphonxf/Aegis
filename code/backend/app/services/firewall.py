from __future__ import annotations

from html import escape
from ipaddress import IPv4Address, ip_address
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote
from xml.etree import ElementTree as ET

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
        raise FirewallError("当前华为地址集封禁仅支持 IPv4")
    return str(parsed)


def _xml_text(root: ET.Element, path: str, namespace: str) -> Optional[str]:
    node = root.find(path, {"hw": namespace})
    if node is None or node.text is None:
        return None
    return node.text.strip()


class HuaweiUSGRestconfClient:
    namespace = "urn:huawei:yang:huawei-address-set"

    def __init__(self) -> None:
        self.scheme = settings.FIREWALL_RESTCONF_SCHEME.strip() or "https"
        self.host = settings.FIREWALL_RESTCONF_HOST.strip()
        self.port = settings.FIREWALL_RESTCONF_PORT
        self.username = settings.FIREWALL_RESTCONF_USERNAME
        self.password = settings.FIREWALL_RESTCONF_PASSWORD
        self.verify_ssl = settings.FIREWALL_RESTCONF_VERIFY_SSL
        self.timeout = settings.FIREWALL_RESTCONF_TIMEOUT_SECONDS
        self.vsys = settings.FIREWALL_RESTCONF_VSYS.strip() or "public"
        self.address_set_name = settings.FIREWALL_ADDRESS_SET_NAME.strip()

    @property
    def is_configured(self) -> bool:
        return bool(settings.FIREWALL_RESTCONF_ENABLED and self.host and self.username and self.password and self.address_set_name)

    def _require_config(self) -> None:
        if not settings.FIREWALL_RESTCONF_ENABLED:
            raise FirewallConfigError("防火墙 RESTCONF 封禁未启用")
        missing = []
        if not self.host:
            missing.append("FIREWALL_RESTCONF_HOST")
        if not self.username:
            missing.append("FIREWALL_RESTCONF_USERNAME")
        if not self.password:
            missing.append("FIREWALL_RESTCONF_PASSWORD")
        if not self.address_set_name:
            missing.append("FIREWALL_ADDRESS_SET_NAME")
        if missing:
            raise FirewallConfigError("缺少防火墙配置：" + ", ".join(missing))

    def _base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}/restconf/data"

    def address_object_collection_url(self) -> str:
        vsys = quote(self.vsys, safe="")
        return (
            f"{self._base_url()}/huawei-vsys-instance:vsys-instance/vsyses/vsys={vsys}"
            "/vsys-config/huawei-address-set:address-set/address-objects/address-object"
        )

    def address_object_url(self) -> str:
        name = quote(self.address_set_name, safe="")
        return f"{self.address_object_collection_url()}={name}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/yang-data+xml",
            "Content-Type": "application/yang-data+xml",
        }

    def _auth(self) -> Tuple[str, str]:
        return (self.username or "", self.password or "")

    def build_address_object_xml(self, ip: str, elem_id: int, description: Optional[str]) -> str:
        description_text = escape((description or f"Aegis block {ip}")[:120])
        address_set_name = escape(self.address_set_name)
        return (
            '<address-object xmlns="urn:huawei:yang:huawei-address-set">'
            f"<name>{address_set_name}</name>"
            "<elements>"
            "<element>"
            f"<elem-id>{elem_id}</elem-id>"
            f"<description>{description_text}</description>"
            f"<address-ipv4>{ip}</address-ipv4>"
            "<mask>255.255.255.255</mask>"
            "</element>"
            "</elements>"
            "</address-object>"
        )

    def _fallback_elem_id(self, ip: str) -> int:
        return (int(IPv4Address(ip)) % 2_000_000_000) + 1

    def _next_elem_id_from_xml(self, content: bytes, ip: str) -> int:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return self._fallback_elem_id(ip)

        max_id = 0
        for element in root.findall(".//hw:element", {"hw": self.namespace}):
            elem_id_text = _xml_text(element, "hw:elem-id", self.namespace)
            address_ipv4 = _xml_text(element, "hw:address-ipv4", self.namespace)
            if elem_id_text and address_ipv4 == ip:
                return int(elem_id_text)
            if elem_id_text and elem_id_text.isdigit():
                max_id = max(max_id, int(elem_id_text))
        return max_id + 1 if max_id else self._fallback_elem_id(ip)

    def _fetch_next_elem_id(self, ip: str) -> int:
        response = requests.get(
            self.address_object_url(),
            headers=self._headers(),
            auth=self._auth(),
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        if response.status_code == 404:
            return self._fallback_elem_id(ip)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirewallClientError(f"查询防火墙地址集失败：{exc}") from exc
        return self._next_elem_id_from_xml(response.content, ip)

    def block_ip(self, ip: str, reason: Optional[str], dry_run: bool) -> Dict[str, Any]:
        normalized_ip = validate_block_ip(ip)
        elem_id = self._fallback_elem_id(normalized_ip)
        request_url = self.address_object_url()
        planned_body = self.build_address_object_xml(normalized_ip, elem_id, reason)

        if dry_run:
            return {
                "status": "dry_run",
                "dry_run": True,
                "ip": normalized_ip,
                "firewall_host": self.host,
                "address_set": self.address_set_name,
                "method": "PATCH",
                "url": request_url,
                "body": planned_body,
                "message": "dry_run=true，未调用防火墙。",
            }

        self._require_config()
        elem_id = self._fetch_next_elem_id(normalized_ip)
        request_body = self.build_address_object_xml(normalized_ip, elem_id, reason)
        try:
            response = requests.patch(
                request_url,
                data=request_body.encode("utf-8"),
                headers=self._headers(),
                auth=self._auth(),
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FirewallClientError(f"调用防火墙封禁失败：{exc}") from exc

        return {
            "status": "blocked",
            "dry_run": False,
            "ip": normalized_ip,
            "firewall_host": self.host,
            "address_set": self.address_set_name,
            "elem_id": elem_id,
            "method": "PATCH",
            "url": request_url,
            "http_status": response.status_code,
            "message": "已通过华为 USG RESTCONF 地址集封禁 IP。",
        }


def block_ip_with_firewall(ip: str, reason: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
    return HuaweiUSGRestconfClient().block_ip(ip=ip, reason=reason, dry_run=dry_run)
