from urllib.parse import parse_qs, urlparse

import pytest

from services.google_drive_mcp_service import (
    GOOGLE_DRIVE_MCP_SCOPES,
    GoogleDriveOAuthError,
    GoogleDriveMCPError,
    GoogleDriveMCPService,
    GoogleDriveOAuthService,
    extract_tool_payload,
    normalize_drive_files,
    token_is_expiring,
)


def test_authorization_url_contains_drive_scopes():
    service = GoogleDriveOAuthService(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8080/google/oauth/callback",
    )

    url = service.build_authorization_url()
    query = parse_qs(urlparse(url).query)

    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["http://localhost:8080/google/oauth/callback"]
    assert query["response_type"] == ["code"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["scope"] == [" ".join(GOOGLE_DRIVE_MCP_SCOPES)]


def test_authorization_url_requires_config():
    service = GoogleDriveOAuthService()

    with pytest.raises(GoogleDriveOAuthError):
        service.build_authorization_url()


def test_save_and_load_token(tmp_path):
    service = GoogleDriveOAuthService(token_path=tmp_path / "google_token.json")
    token = {"access_token": "token", "refresh_token": "refresh"}

    service.save_token(token)

    assert service.load_token() == token


def test_token_is_expiring_uses_saved_at_and_expiry():
    assert token_is_expiring({"saved_at": 100, "expires_in": 3600}, buffer_seconds=60) is True
    assert token_is_expiring({"access_token": "token"}) is False


def test_extract_tool_payload_parses_text_json():
    payload = extract_tool_payload(
        {
            "content": [
                {
                    "type": "text",
                    "text": '{"files": [{"id": "file-1", "title": "Week 1"}]}',
                }
            ]
        }
    )

    assert payload["files"][0]["id"] == "file-1"


def test_normalize_drive_files_accepts_files_or_items():
    files = normalize_drive_files(
        {
            "items": [
                {
                    "id": "file-1",
                    "name": "Week 1",
                    "mimeType": "text/plain",
                    "viewUrl": "https://example.com/file-1",
                }
            ]
        }
    )

    assert files == [
        {
            "id": "file-1",
            "title": "Week 1",
            "mimeType": "text/plain",
            "viewUrl": "https://example.com/file-1",
        }
    ]


def test_configured_lecture_file_skips_mcp_file_list(monkeypatch, tmp_path):
    oauth_service = GoogleDriveOAuthService(token_path=tmp_path / "google_token.json")
    service = GoogleDriveMCPService(oauth_service, lecture_file_id="file-1")

    monkeypatch.setattr(
        service,
        "get_file_metadata",
        lambda file_id: {
            "id": file_id,
            "title": "Week 1",
            "mimeType": "application/vnd.google-apps.document",
            "viewUrl": "https://example.com/file-1",
        },
    )

    assert service.list_recent_files() == [
        {
            "id": "file-1",
            "title": "Week 1",
            "mimeType": "application/vnd.google-apps.document",
            "viewUrl": "https://example.com/file-1",
        }
    ]


def test_read_file_content_falls_back_to_drive_api(monkeypatch, tmp_path):
    oauth_service = GoogleDriveOAuthService(token_path=tmp_path / "google_token.json")
    service = GoogleDriveMCPService(oauth_service)

    def fail_mcp_tool(name, arguments):
        raise GoogleDriveMCPError("The caller does not have permission")

    monkeypatch.setattr(service, "call_tool", fail_mcp_tool)
    monkeypatch.setattr(
        service,
        "read_file_content_with_drive_api",
        lambda file_id: "Lecture note text",
    )

    assert service.read_file_content("file-1") == "Lecture note text"
    assert service.last_read_source == "google_drive_api_fallback"


def test_mcp_service_requires_saved_token(tmp_path):
    oauth_service = GoogleDriveOAuthService(token_path=tmp_path / "missing.json")
    mcp_service = GoogleDriveMCPService(oauth_service)

    with pytest.raises(Exception, match="Google Drive is not connected"):
        mcp_service._get_access_token()
