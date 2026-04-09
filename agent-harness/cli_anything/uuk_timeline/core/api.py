"""REST API client for uuk-timeline server."""

import json
import sys
import urllib.request
import urllib.error
from typing import Any


class APIError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class APIClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        import os, base64
        self.base_url = base_url.rstrip("/")
        user = os.environ.get("UUK_ADMIN_USER", "timelineAdmin")
        passwd = os.environ.get("UUK_ADMIN_PASS", "hwbUNWHqR9N4mT")
        self._auth = "Basic " + base64.b64encode(f"{user}:{passwd}".encode()).decode()

    def _request(self, method: str, path: str, body: Any = None, content_type: str = "application/json") -> Any:
        url = self.base_url + path
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header("Content-Type", content_type)
        req.add_header("Accept", "application/json")
        req.add_header("Authorization", self._auth)

        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                if raw:
                    return json.loads(raw)
                return None
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise APIError(f"HTTP {e.code}: {raw}", status=e.code)
        except urllib.error.URLError as e:
            raise APIError(f"Cannot connect to {self.base_url}: {e.reason}")

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def put(self, path: str, body: Any) -> Any:
        return self._request("PUT", path, body)

    def post(self, path: str, body: Any = None) -> Any:
        return self._request("POST", path, body)

    def upload_file(self, file_path: str) -> Any:
        """Upload an image file via multipart/form-data."""
        import mimetypes
        import os
        import uuid

        boundary = uuid.uuid4().hex
        filename = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            file_data = f.read()

        body_parts = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        body = b"".join(body_parts)

        url = self.base_url + "/api/upload"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise APIError(f"HTTP {e.code}: {raw}", status=e.code)
        except urllib.error.URLError as e:
            raise APIError(f"Cannot connect to {self.base_url}: {e.reason}")
