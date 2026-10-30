"""Thin Supabase REST client shared by the stores."""
from typing import Any, Dict, List, Optional

import httpx


class SupabaseRest:
    def __init__(self, url: str, key: str, timeout: float = 10.0):
        self.url = url.rstrip("/")
        self.key = key
        self.timeout = timeout

    def headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def endpoint(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    def request(
        self,
        method: str,
        table: str,
        *,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        prefer: Optional[str] = None,
    ) -> httpx.Response:
        return httpx.request(
            method,
            self.endpoint(table),
            json=json,
            params=params,
            headers=self.headers(prefer),
            timeout=self.timeout,
        )

    def get(
        self,
        table: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        response = self.request("GET", table, params=params, prefer="return=representation")
        if response.status_code >= 300:
            return []
        data = response.json()
        return data if isinstance(data, list) else []
