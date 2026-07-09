#!/usr/bin/env python3
"""WordPress REST API クライアント"""

import base64
import json
import urllib.error
import urllib.request
from typing import Any


class WPApiError(Exception):
    def __init__(self, status: int, message: str, body: str = ""):
        self.status = status
        self.message = message
        self.body = body
        super().__init__(f"HTTP {status}: {message}")


class WPApiClient:
    def __init__(self, base_url: str, user: str, app_password: str):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.app_password = app_password.replace(" ", "")

    def _auth_header(self) -> str:
        creds = f"{self.user}:{self.app_password}"
        encoded = base64.b64encode(creds.encode()).decode()
        return f"Basic {encoded}"

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        timeout: int = 30,
    ) -> Any:
        url = f"{self.base_url}/wp-json/wp/v2/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "User-Agent": "WPAIPublisher/1.0",
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            raise WPApiError(e.code, e.reason, body_text) from e

    def get(self, endpoint: str) -> Any:
        return self._request("GET", endpoint)

    def post(self, endpoint: str, data: dict) -> Any:
        return self._request("POST", endpoint, data)

    def put(self, endpoint: str, data: dict) -> Any:
        return self._request("PUT", endpoint, data)

    def health_check(self) -> bool:
        url = f"{self.base_url}/wp-json/"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False

    def get_page_by_slug(self, slug: str) -> dict | None:
        pages = self.get(f"pages?slug={slug}")
        return pages[0] if pages else None

    def update_page_content(self, page_id: int, content: str, status: str = "draft") -> dict:
        return self.put(f"pages/{page_id}", {"content": content, "status": status})

    def create_page(self, title: str, slug: str, content: str, status: str = "draft") -> dict:
        return self.post("pages", {
            "title": title,
            "slug": slug,
            "content": content,
            "status": status,
        })
