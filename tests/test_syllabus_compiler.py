from features.syllabus_compiler import (
    SyllabusCompiler,
    build_canvas_markdown,
    build_canvas_title,
    build_upload_key,
    format_existing_canvas_message,
    format_success_message,
    is_pdf_file,
)
from services.storage_service import InMemoryStorage


class FakeSlackService:
    def __init__(self):
        self.messages = []
        self.created_canvases = []

    def post_message(self, channel_id, text):
        self.messages.append({"channel": channel_id, "text": text})

    def download_file(self, url):
        return b"fake pdf bytes"

    def create_canvas(self, channel_id, title, markdown):
        self.created_canvases.append(
            {
                "channel_id": channel_id,
                "title": title,
                "markdown": markdown,
            }
        )
        return {"ok": True, "canvas_id": "F123CANVAS"}


class FakeAIService:
    def extract_course_metadata(self, syllabus_text):
        return {
            "course_name": "Intro to Data Engineering",
            "instructor": "Dr. Ada Lovelace",
            "course_schedule": ["Mondays and Wednesdays 10:00-11:30 AM"],
            "course_location": "Room 204",
            "instructor_contact": "ada@example.edu",
            "instructor_office_hours": "Tuesdays 2:00-3:00 PM",
            "ta_contacts": [
                {"name": "Grace Hopper", "contact": "grace@example.edu"},
            ],
            "ta_office_hours": [
                {"name": "Grace Hopper", "office_hours": "Fridays 1:00-2:00 PM"},
            ],
        }


def build_compiler(tmp_path, admin_ids=None):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    slack_service = FakeSlackService()
    compiler = SyllabusCompiler(
        storage=storage,
        slack_service=slack_service,
        ai_service=FakeAIService(),
        admin_slack_ids=admin_ids or ["UADMIN"],
        course_channel_id="CGENERAL",
    )
    return compiler, storage, slack_service


def pdf_file_event(user_id="UADMIN"):
    return {
        "type": "message",
        "subtype": "file_share",
        "channel_type": "im",
        "channel": "DADMIN",
        "user": user_id,
        "files": [
            {
                "name": "syllabus.pdf",
                "id": "FSLACKPDF",
                "mimetype": "application/pdf",
                "url_private_download": "https://files.slack.test/syllabus.pdf",
            }
        ],
    }


def test_admin_pdf_upload_creates_canvas_and_state(tmp_path, monkeypatch):
    compiler, storage, slack_service = build_compiler(tmp_path)
    monkeypatch.setattr(
        "features.syllabus_compiler.extract_pdf_text",
        lambda pdf_bytes: "Syllabus text",
    )

    result = compiler.handle_slack_file_event(pdf_file_event())

    assert result == {"handled": True, "status": "created", "canvas_id": "F123CANVAS"}
    assert slack_service.created_canvases[0]["channel_id"] == "CGENERAL"
    assert slack_service.created_canvases[0]["title"] == "Course quick fact + FAQ"
    assert "## Instructor" in slack_service.created_canvases[0]["markdown"]
    assert "Dr. Ada Lovelace" in slack_service.created_canvases[0]["markdown"]
    assert "Mondays and Wednesdays 10:00-11:30 AM" in slack_service.created_canvases[0]["markdown"]
    assert "Room 204" in slack_service.created_canvases[0]["markdown"]
    assert "ada@example.edu" in slack_service.created_canvases[0]["markdown"]
    assert "Grace Hopper: grace@example.edu" in slack_service.created_canvases[0]["markdown"]
    assert "Created syllabus canvas `F123CANVAS`" in slack_service.messages[0]["text"]

    state = storage.load_course_state()
    assert state["course_map"]["source_name"] == "syllabus.pdf"
    assert state["course_map"]["course_name"] == "Intro to Data Engineering"
    assert state["course_map"]["instructor"] == "Dr. Ada Lovelace"
    assert state["course_map"]["course_location"] == "Room 204"
    assert state["faq_canvas"]["canvas_id"] == "F123CANVAS"
    assert state["faq_canvas"]["channel_id"] == "CGENERAL"


def test_non_admin_upload_is_rejected(tmp_path):
    compiler, storage, slack_service = build_compiler(tmp_path)

    result = compiler.handle_slack_file_event(pdf_file_event(user_id="USTUDENT"))

    assert result == {"handled": True, "status": "rejected_non_admin"}
    assert not slack_service.created_canvases
    assert not storage.load_course_state()
    assert "Only configured professor/admin" in slack_service.messages[0]["text"]


def test_same_file_id_upload_only_creates_one_canvas(tmp_path, monkeypatch):
    compiler, storage, slack_service = build_compiler(tmp_path)
    monkeypatch.setattr(
        "features.syllabus_compiler.extract_pdf_text",
        lambda pdf_bytes: "Syllabus text",
    )

    first_result = compiler.handle_slack_file_event(pdf_file_event())
    second_result = compiler.handle_slack_file_event(pdf_file_event())

    assert first_result["status"] == "created"
    assert second_result == {"handled": True, "status": "duplicate_completed"}
    assert len(slack_service.created_canvases) == 1
    assert storage.load_course_state()["faq_canvas"]["canvas_id"] == "F123CANVAS"


def test_duplicate_upload_while_in_progress_creates_no_canvas(tmp_path):
    compiler, storage, slack_service = build_compiler(tmp_path)
    event = pdf_file_event()
    upload_key = build_upload_key(event, event["files"][0])
    storage.begin_upload(upload_key)

    result = compiler.handle_slack_file_event(event)

    assert result == {"handled": True, "status": "duplicate_in_progress"}
    assert not slack_service.created_canvases
    assert not storage.load_course_state()


def test_duplicate_upload_after_completion_creates_no_canvas(tmp_path):
    compiler, storage, slack_service = build_compiler(tmp_path)
    event = pdf_file_event()
    upload_key = build_upload_key(event, event["files"][0])
    storage.begin_upload(upload_key)
    storage.complete_upload(upload_key)

    result = compiler.handle_slack_file_event(event)

    assert result == {"handled": True, "status": "duplicate_completed"}
    assert not slack_service.created_canvases
    assert not storage.load_course_state()


def test_existing_active_canvas_blocks_new_canvas_creation(tmp_path):
    compiler, storage, slack_service = build_compiler(tmp_path)
    storage.save_course_state(
        {
            "course_map": {"course_name": "Existing Course"},
            "faq_canvas": {
                "canvas_id": "FEXISTING",
                "channel_id": "CGENERAL",
                "title": "Existing Course FAQ",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        }
    )

    event = pdf_file_event()
    event["files"][0]["id"] = "FNEWPDF"
    result = compiler.handle_slack_file_event(event)

    assert result == {
        "handled": True,
        "status": "blocked_existing_canvas",
        "canvas_id": "FEXISTING",
    }
    assert not slack_service.created_canvases
    assert "A course canvas already exists: `FEXISTING`." in slack_service.messages[0]["text"]
    assert storage.load_course_state()["faq_canvas"]["canvas_id"] == "FEXISTING"


def test_non_pdf_upload_is_rejected(tmp_path):
    compiler, storage, slack_service = build_compiler(tmp_path)
    event = pdf_file_event()
    event["files"][0] = {
        "name": "notes.txt",
        "id": "FTXT",
        "mimetype": "text/plain",
        "url_private_download": "https://files.slack.test/notes.txt",
    }

    result = compiler.handle_slack_file_event(event)

    assert result == {"handled": True, "status": "rejected_non_pdf"}
    assert not slack_service.created_canvases
    assert not storage.load_course_state()
    assert "Please upload a PDF syllabus." in slack_service.messages[0]["text"]


def test_empty_pdf_text_fails_with_clear_dm(tmp_path, monkeypatch):
    compiler, storage, slack_service = build_compiler(tmp_path)
    monkeypatch.setattr("features.syllabus_compiler.extract_pdf_text", lambda pdf_bytes: "")

    result = compiler.handle_slack_file_event(pdf_file_event())

    assert result["status"] == "failed"
    assert "No readable text found" in result["error"]
    assert not slack_service.created_canvases
    assert not storage.load_course_state()
    assert "Could not create the syllabus canvas" in slack_service.messages[0]["text"]


def test_pdf_detection_accepts_multiple_slack_shapes():
    assert is_pdf_file({"name": "syllabus.pdf"})
    assert is_pdf_file({"filetype": "pdf"})
    assert is_pdf_file({"mimetype": "application/pdf"})
    assert not is_pdf_file({"name": "syllabus.docx"})


def test_upload_key_prefers_file_id_and_has_fallback():
    event = pdf_file_event()
    assert build_upload_key(event, event["files"][0]) == "file:FSLACKPDF"

    file_data = {"name": "syllabus.pdf"}
    fallback_event = {
        "channel": "DADMIN",
        "user": "UADMIN",
        "ts": "123.456",
    }
    assert (
        build_upload_key(fallback_event, file_data)
        == "fallback:DADMIN:UADMIN:123.456:syllabus.pdf"
    )


def test_canvas_title_and_markdown_fallbacks():
    assert build_canvas_title("Intro to AI") == "Course quick fact + FAQ"
    assert build_canvas_title("") == "Course quick fact + FAQ"
    assert build_canvas_title("Course") == "Course quick fact + FAQ"

    markdown = build_canvas_markdown(
        {
            "course_name": "Not found in syllabus",
            "instructor": "Not found in syllabus",
            "course_schedule": [],
            "course_location": "Not found in syllabus",
            "instructor_contact": "Not found in syllabus",
            "instructor_office_hours": "Not found in syllabus",
            "ta_contacts": [],
            "ta_office_hours": [],
        }
    )
    assert "# Course quick fact + FAQ" in markdown
    assert "## Instructor" in markdown
    assert "## Schedule" in markdown
    assert "## Location" in markdown
    assert "## TA Contact" in markdown
    assert "Not found in syllabus" in markdown


def test_success_message_includes_course_and_instructor():
    message = format_success_message(
        {
            "course_name": "Intro to AI",
            "instructor": "Not found in syllabus",
        },
        "F123",
    )
    assert "Intro to AI" in message
    assert "Instructor: Not found in syllabus" in message


def test_existing_canvas_message_mentions_manual_reset():
    message = format_existing_canvas_message("F123")
    assert "A course canvas already exists: `F123`." in message
    assert "clear `data/course_state.json`" in message
