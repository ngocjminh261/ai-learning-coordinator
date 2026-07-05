import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API_URL = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_MCP_SERVER_URL = "https://drivemcp.googleapis.com/mcp/v1"
MCP_PROTOCOL_VERSION = "2025-06-18"
GOOGLE_DRIVE_MCP_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleDriveOAuthError(Exception):
    pass


class GoogleDriveMCPError(Exception):
    pass


class GoogleDriveOAuthService:
    def __init__(
        self,
        client_id=None,
        client_secret=None,
        redirect_uri=None,
        token_path="data/google_oauth_token.json",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_path = Path(token_path)

    def is_configured(self):
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def build_authorization_url(self, state="drive-mcp"):
        self._ensure_configured()
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(GOOGLE_DRIVE_MCP_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
        return f"{GOOGLE_OAUTH_AUTH_URL}?{query}"

    def exchange_code_for_token(self, code):
        self._ensure_configured()
        if not code:
            raise GoogleDriveOAuthError("Missing OAuth code")

        payload = urlencode(
            {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        response = self._post_form(GOOGLE_OAUTH_TOKEN_URL, payload)
        response["saved_at"] = int(time.time())
        self.save_token(response)
        return response

    def save_token(self, token):
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with self.token_path.open("w") as token_file:
            json.dump(token, token_file, indent=2)
            token_file.write("\n")

    def load_token(self):
        if not self.token_path.exists():
            return None

        with self.token_path.open() as token_file:
            return json.load(token_file)

    def _ensure_configured(self):
        if not self.is_configured():
            raise GoogleDriveOAuthError(
                "Missing Google OAuth config. Set GOOGLE_OAUTH_CLIENT_ID, "
                "GOOGLE_OAUTH_CLIENT_SECRET, and GOOGLE_OAUTH_REDIRECT_URI."
            )

    def _post_form(self, url, payload):
        request = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise GoogleDriveOAuthError(error_body) from exc
        except URLError as exc:
            raise GoogleDriveOAuthError(str(exc)) from exc


class GoogleDriveMCPService:
    def __init__(
        self,
        oauth_service,
        server_url=GOOGLE_DRIVE_MCP_SERVER_URL,
        lecture_file_id=None,
    ):
        self.oauth_service = oauth_service
        self.server_url = server_url
        self.lecture_file_id = lecture_file_id
        self.last_read_source = None

    def list_recent_files(self, page_size=5):
        if self.lecture_file_id:
            return [self.get_file_metadata(self.lecture_file_id)]

        try:
            result = self.call_tool(
                "list_recent_files",
                {
                    "pageSize": page_size,
                    "excludeContentSnippets": True,
                },
            )
            return normalize_drive_files(extract_tool_payload(result))
        except GoogleDriveMCPError:
            return self.list_recent_files_with_drive_api(page_size)

    def read_file_content(self, file_id):
        self.last_read_source = "google_drive_mcp"
        try:
            result = self.call_tool(
                "read_file_content",
                {
                    "fileId": file_id,
                    "includeComments": False,
                },
            )
            return extract_tool_text(result).strip()
        except GoogleDriveMCPError:
            self.last_read_source = "google_drive_api_fallback"
            return self.read_file_content_with_drive_api(file_id)

    def list_recent_files_with_drive_api(self, page_size=5):
        query = urlencode(
            {
                "pageSize": page_size,
                "fields": "files(id,name,mimeType,webViewLink)",
            }
        )
        payload = self._drive_api_json(f"{GOOGLE_DRIVE_API_URL}/files?{query}")
        return normalize_drive_files(payload.get("files", []))

    def get_file_metadata(self, file_id):
        query = urlencode({"fields": "id,name,mimeType,webViewLink"})
        payload = self._drive_api_json(f"{GOOGLE_DRIVE_API_URL}/files/{file_id}?{query}")
        files = normalize_drive_files([payload])
        if not files:
            raise GoogleDriveMCPError(f"Google Drive file not found: {file_id}")
        return files[0]

    def read_file_content_with_drive_api(self, file_id):
        metadata = self.get_file_metadata(file_id)
        mime_type = metadata.get("mimeType") or ""
        if mime_type.startswith("application/vnd.google-apps"):
            query = urlencode({"mimeType": "text/plain"})
            content = self._drive_api_bytes(
                f"{GOOGLE_DRIVE_API_URL}/files/{file_id}/export?{query}"
            )
            return content.decode("utf-8", errors="replace").strip()

        query = urlencode({"alt": "media"})
        content = self._drive_api_bytes(f"{GOOGLE_DRIVE_API_URL}/files/{file_id}?{query}")
        if mime_type == "application/pdf":
            return extract_pdf_text(content)

        return content.decode("utf-8", errors="replace").strip()

    def call_tool(self, name, arguments):
        self.initialize()
        result = self._mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        ).get("result", {})

        if result.get("isError"):
            raise GoogleDriveMCPError(extract_tool_text(result) or f"{name} failed")

        return result

    def initialize(self):
        self._mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "ai-learning-coordinator",
                        "version": "0.1.0",
                    },
                },
            }
        )
        self._mcp_notification({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _mcp_request(self, payload):
        request = Request(
            self.server_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise GoogleDriveMCPError(error_body) from exc
        except URLError as exc:
            raise GoogleDriveMCPError(str(exc)) from exc

        return _parse_mcp_body(body)

    def _mcp_notification(self, payload):
        request = Request(
            self.server_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                response.read()
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise GoogleDriveMCPError(error_body) from exc
        except URLError as exc:
            raise GoogleDriveMCPError(str(exc)) from exc

    def _headers(self):
        access_token = self._get_access_token()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {access_token}",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }

    def _drive_api_json(self, url):
        request = Request(url, headers={"Authorization": f"Bearer {self._get_access_token()}"})
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise GoogleDriveMCPError(error_body) from exc
        except URLError as exc:
            raise GoogleDriveMCPError(str(exc)) from exc

    def _drive_api_bytes(self, url):
        request = Request(url, headers={"Authorization": f"Bearer {self._get_access_token()}"})
        try:
            with urlopen(request, timeout=30) as response:
                return response.read()
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise GoogleDriveMCPError(error_body) from exc
        except URLError as exc:
            raise GoogleDriveMCPError(str(exc)) from exc

    def _get_access_token(self):
        token = self.oauth_service.load_token()
        if not token or not token.get("access_token"):
            raise GoogleDriveMCPError(
                "Google Drive is not connected yet. Open /google/oauth/start first."
            )

        if token_is_expiring(token) and token.get("refresh_token"):
            token = self.refresh_token(token["refresh_token"])

        return token["access_token"]

    def refresh_token(self, refresh_token):
        self.oauth_service._ensure_configured()
        payload = urlencode(
            {
                "client_id": self.oauth_service.client_id,
                "client_secret": self.oauth_service.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        refreshed = self.oauth_service._post_form(GOOGLE_OAUTH_TOKEN_URL, payload)
        current_token = self.oauth_service.load_token() or {}
        current_token.update(refreshed)
        current_token["refresh_token"] = refresh_token
        current_token["saved_at"] = int(time.time())
        self.oauth_service.save_token(current_token)
        return current_token


def token_is_expiring(token, buffer_seconds=60):
    saved_at = int(token.get("saved_at") or 0)
    expires_in = int(token.get("expires_in") or 0)
    if not saved_at or not expires_in:
        return False

    return time.time() >= saved_at + expires_in - buffer_seconds


def extract_tool_payload(result):
    text = extract_tool_text(result)
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def extract_tool_text(result):
    content = result.get("content", [])
    text_parts = [
        item.get("text", "")
        for item in content
        if item.get("type") == "text" and item.get("text")
    ]
    return "\n".join(text_parts)


def normalize_drive_files(payload):
    if isinstance(payload, dict):
        candidates = payload.get("files") or payload.get("items") or []
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = []

    files = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        file_id = item.get("id") or item.get("fileId")
        title = item.get("title") or item.get("name")
        if not file_id or not title:
            continue

        files.append(
            {
                "id": file_id,
                "title": title,
                "mimeType": item.get("mimeType"),
                "viewUrl": item.get("viewUrl") or item.get("webViewLink"),
            }
        )
    return files


def _parse_mcp_body(body):
    stripped = body.strip()
    if not stripped:
        return {}

    if stripped.startswith("event:") or stripped.startswith("data:"):
        for line in stripped.splitlines():
            if line.startswith("data:"):
                return json.loads(line.removeprefix("data:").strip())

    return json.loads(stripped)


def extract_pdf_text(pdf_bytes):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise GoogleDriveMCPError("Install pypdf to read PDF lecture notes.") from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(pdf_bytes))
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return "\n".join(page_text).strip()
