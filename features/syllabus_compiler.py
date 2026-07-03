from datetime import datetime, timezone
from io import BytesIO


STAFF_TITLES = {"Instructor", "Teaching Assistant"}


class SyllabusCompiler:
    def __init__(self, storage, slack_service, ai_service, admin_slack_ids, course_channel_id):
        self.storage = storage
        self.slack_service = slack_service
        self.ai_service = ai_service
        self.admin_slack_ids = set(admin_slack_ids)
        self.course_channel_id = course_channel_id

    def handle_slack_file_event(self, event):
        if not is_dm_file_share_event(event):
            return {"handled": False}

        user_id = event.get("user")
        response_channel = event.get("channel")

        if not self.is_staff_user(user_id):
            self.slack_service.post_message(
                response_channel,
                "Only users with the Instructor or Teaching Assistant title can upload a syllabus.",
            )
            return {"handled": True, "status": "rejected_non_staff"}

        files = event.get("files", [])
        syllabus_files = [file_data for file_data in files if is_syllabus_upload(event, file_data)]
        if not syllabus_files:
            return {"handled": False}

        pdf_file = next((file_data for file_data in syllabus_files if is_pdf_file(file_data)), None)
        if not pdf_file:
            self.slack_service.post_message(
                response_channel,
                "Please upload a PDF syllabus.",
            )
            return {"handled": True, "status": "rejected_non_pdf"}

        upload_key = build_upload_key(event, pdf_file)
        upload_status = self.storage.begin_upload(upload_key)
        if upload_status != "started":
            return {"handled": True, "status": upload_status}

        try:
            active_canvas_id = self.storage.get_active_canvas_id()
            if active_canvas_id:
                self.slack_service.post_message(
                    response_channel,
                    format_existing_canvas_message(active_canvas_id),
                )
                self.storage.complete_upload(upload_key)
                return {
                    "handled": True,
                    "status": "blocked_existing_canvas",
                    "canvas_id": active_canvas_id,
                }

            course_state = self.create_canvas_from_pdf_file(pdf_file)
        except Exception as exc:
            self.storage.fail_upload(upload_key)
            self.slack_service.post_message(
                response_channel,
                f"Could not create the syllabus canvas: {exc}",
            )
            return {"handled": True, "status": "failed", "error": str(exc)}

        self.storage.complete_upload(upload_key)
        canvas_id = course_state["faq_canvas"]["canvas_id"]
        course_map = course_state["course_map"]
        self.slack_service.post_message(
            response_channel,
            format_success_message(course_map, canvas_id),
        )
        return {"handled": True, "status": "created", "canvas_id": canvas_id}

    def is_staff_user(self, user_id):
        if user_id in self.admin_slack_ids:
            return True

        try:
            user_title = self.slack_service.get_user_profile_title(user_id)
        except Exception as exc:
            print(f"Could not read Slack profile title for <@{user_id}>: {exc}")
            return False

        return normalize_profile_title(user_title) in STAFF_TITLES

    def create_canvas_from_pdf_file(self, pdf_file):
        pdf_bytes = self.slack_service.download_file(get_file_download_url(pdf_file))
        syllabus_text = extract_pdf_text(pdf_bytes)
        if not syllabus_text.strip():
            raise ValueError("No readable text found in the PDF.")

        metadata = self.ai_service.extract_course_metadata(syllabus_text)
        created_at = datetime.now(timezone.utc).isoformat()
        course_map = {
            "source_name": pdf_file.get("name") or pdf_file.get("title") or "syllabus.pdf",
            "course_name": metadata["course_name"],
            "instructor": metadata["instructor"],
            "course_schedule": metadata["course_schedule"],
            "course_location": metadata["course_location"],
            "instructor_contact": metadata["instructor_contact"],
            "instructor_office_hours": metadata["instructor_office_hours"],
            "ta_contacts": metadata["ta_contacts"],
            "ta_office_hours": metadata["ta_office_hours"],
            "canvas_title": build_canvas_title(metadata["course_name"]),
            "created_at": created_at,
        }
        canvas_markdown = build_canvas_markdown(course_map)
        canvas_response = self.slack_service.create_canvas(
            self.course_channel_id,
            course_map["canvas_title"],
            canvas_markdown,
        )
        if not canvas_response.get("ok"):
            raise RuntimeError(canvas_response.get("error", "Slack canvas creation failed"))

        return self.storage.save_course_canvas_state(
            course_map=course_map,
            canvas_id=canvas_response["canvas_id"],
            channel_id=self.course_channel_id,
        )


def is_dm_file_share_event(event):
    if event.get("type") != "message":
        return False
    if event.get("subtype") != "file_share":
        return False
    if event.get("bot_id"):
        return False
    return event.get("channel_type") == "im" or str(event.get("channel", "")).startswith("D")


def is_pdf_file(file_data):
    file_name = (file_data.get("name") or file_data.get("title") or "").lower()
    return (
        file_data.get("mimetype") == "application/pdf"
        or file_data.get("filetype") == "pdf"
        or file_name.endswith(".pdf")
    )


def is_syllabus_upload(event, file_data):
    text = event.get("text", "")
    file_name = file_data.get("name") or file_data.get("title") or ""
    return "syllabus" in f"{text} {file_name}".lower()


def normalize_profile_title(title):
    return " ".join((title or "").split())


def get_file_download_url(file_data):
    url = file_data.get("url_private_download") or file_data.get("url_private")
    if not url:
        raise ValueError("Slack did not include a private download URL for the file.")
    return url


def build_upload_key(event, file_data):
    if file_data.get("id"):
        return f"file:{file_data['id']}"
    if event.get("event_id"):
        return f"event:{event['event_id']}"

    channel = event.get("channel", "unknown-channel")
    user_id = event.get("user", "unknown-user")
    timestamp = event.get("ts") or event.get("event_ts") or "unknown-ts"
    file_name = file_data.get("name") or file_data.get("title") or "unknown-file"
    return f"fallback:{channel}:{user_id}:{timestamp}:{file_name}"


def extract_pdf_text(pdf_bytes):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to extract syllabus PDF text.") from exc

    reader = PdfReader(BytesIO(pdf_bytes))
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    return "\n".join(page_text).strip()


def build_canvas_title(course_name):
    # TODO: Make this dynamic again once the course fact sheet and FAQ sections are stable.
    return "Course quick fact + FAQ"


def build_canvas_markdown(course_map):
    course_name = course_map.get("course_name") or "Not found in syllabus"
    instructor = course_map.get("instructor") or "Not found in syllabus"
    schedule_lines = format_string_list(course_map.get("course_schedule"))
    location = course_map.get("course_location") or "Not found in syllabus"
    instructor_contact = course_map.get("instructor_contact") or "Not found in syllabus"
    instructor_office_hours = course_map.get("instructor_office_hours") or "Not found in syllabus"
    ta_contacts = format_contact_entries(course_map.get("ta_contacts"))
    ta_office_hours = format_office_hour_entries(course_map.get("ta_office_hours"))

    return f"""# {build_canvas_title(course_name)}

## Course

{course_name}

## Instructor

{instructor}

## Schedule

{schedule_lines}

## Location

{location}

## Instructor Contact

{instructor_contact}

## Instructor Office Hours

{instructor_office_hours}

## TA Contact

{ta_contacts}

## TA Office Hours

{ta_office_hours}
"""


def format_success_message(course_map, canvas_id):
    course_name = course_map.get("course_name") or "Not found in syllabus"
    instructor = course_map.get("instructor") or "Not found in syllabus"
    return (
        f"Created syllabus canvas `{canvas_id}` for *{course_name}*.\n"
        f"Instructor: {instructor}"
    )


def format_existing_canvas_message(canvas_id):
    return (
        f"A course canvas already exists: `{canvas_id}`.\n"
        "Delete the canvas and clear `data/course_state.json` before uploading a new syllabus."
    )


def format_string_list(items):
    if not items:
        return "Not found in syllabus"
    return "\n".join(f"- {item}" for item in items)


def format_contact_entries(entries):
    if not entries:
        return "Not found in syllabus"

    lines = []
    for entry in entries:
        name = entry.get("name") or "Not found in syllabus"
        contact = entry.get("contact") or "Not found in syllabus"
        lines.append(f"- {name}: {contact}")
    return "\n".join(lines)


def format_office_hour_entries(entries):
    if not entries:
        return "Not found in syllabus"

    lines = []
    for entry in entries:
        name = entry.get("name") or "Not found in syllabus"
        office_hours = entry.get("office_hours") or "Not found in syllabus"
        lines.append(f"- {name}: {office_hours}")
    return "\n".join(lines)
