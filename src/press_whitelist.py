"""Lọc báo theo Chinh_thong.json."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse


def _norm_domain(host: str) -> str:
    h = str(host or "").lower().strip()
    if h.startswith("www."):
        h = h[4:]
    return h


class PressWhitelist:
    def __init__(self, entries: List[Dict[str, Any]]) -> None:
        self.entries = entries
        self.domains: Set[str] = set()
        self.domain_to_name: Dict[str, str] = {}
        for row in entries:
            if not isinstance(row, dict):
                continue
            url = str(row.get("homepage_url") or row.get("url") or "").strip()
            name = str(row.get("name") or "").strip()
            if not url:
                continue
            dom = _norm_domain(urlparse(url).netloc)
            if not dom:
                continue
            self.domains.add(dom)
            if name:
                self.domain_to_name.setdefault(dom, name)

    @classmethod
    def from_file(cls, path: str) -> "PressWhitelist":
        if not os.path.isfile(path):
            return cls([])
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return cls([])
        if isinstance(data, list):
            return cls(data)
        return cls([])

    @staticmethod
    def _host_matches(dom: str, allowed: str) -> bool:
        if not dom or not allowed:
            return False
        if dom == allowed:
            return True
        if dom.endswith("." + allowed):
            return True
        dom_base = dom[4:] if dom.startswith("www.") else dom
        allow_base = allowed[4:] if allowed.startswith("www.") else allowed
        if dom_base == allow_base:
            return True
        if dom_base.endswith("." + allow_base):
            return True
        return False

    def is_allowed_url(self, url: str) -> bool:
        if not self.domains:
            return False
        dom = _norm_domain(urlparse(str(url or "")).netloc)
        if not dom:
            return False
        if dom in self.domains:
            return True
        for allowed in self.domains:
            if self._host_matches(dom, allowed):
                return True
        return False

    def press_for_url(self, url: str) -> Dict[str, str]:
        dom = _norm_domain(urlparse(str(url or "")).netloc)
        name = self.domain_to_name.get(dom, "")
        return {"press_name": name, "press_domain": dom}
