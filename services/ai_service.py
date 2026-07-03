import json
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class AIServiceError(Exception):
    pass


class SyllabusAIService:
    def __init__(
        self,
        gemini_api_key=None,
        gemini_model="gemini-1.5-flash",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1",
    ):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.ollama_model = ollama_model

    def extract_course_metadata(self, syllabus_text):
        prompt = build_syllabus_prompt(syllabus_text)
        errors = []

        if self.gemini_api_key:
            try:
                return normalize_course_metadata(self._call_gemini(prompt))
            except Exception as exc:
                errors.append(f"Gemini failed: {exc}")

        try:
            return normalize_course_metadata(self._call_ollama(prompt))
        except Exception as exc:
            errors.append(f"Ollama failed: {exc}")

        raise AIServiceError("; ".join(errors) or "No AI provider configured")

    def _call_gemini(self, prompt):
        model_name = quote(self.gemini_model, safe="")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
            },
        }
        response = _post_json(url, payload)
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_response(text)

    def _call_ollama(self, prompt):
        response = _post_json(
            f"{self.ollama_base_url}/api/generate",
            {
                "model": self.ollama_model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
        )
        return _parse_json_response(response.get("response", "{}"))


def build_syllabus_prompt(syllabus_text):
    return f"""
Extract a student-facing quick fact sheet from this syllabus.

Return only valid JSON with this shape:
{{
  "course_name": "string or null",
  "instructor": "string or null",
  "course_schedule": ["meeting time, date range, or schedule item"],
  "course_location": "string or null",
  "instructor_contact": "string or null",
  "instructor_office_hours": "string or null",
  "ta_contacts": [
    {{
      "name": "TA name or null",
      "contact": "email or other contact string or null"
    }}
  ],
  "ta_office_hours": [
    {{
      "name": "TA name or null",
      "office_hours": "office hours string or null"
    }}
  ]
}}

Rules:
- Only use information found in the syllabus.
- If a single-value field is not found, use null.
- If a list field has no items, use an empty list.
- Keep schedule, contact, and office hour text concise but specific.

Syllabus text:
{syllabus_text[:20000]}
""".strip()


def normalize_course_metadata(metadata):
    return {
        "course_name": _clean_string(metadata.get("course_name")) or "Not found in syllabus",
        "instructor": _clean_string(metadata.get("instructor")) or "Not found in syllabus",
        "course_schedule": _clean_string_list(metadata.get("course_schedule")),
        "course_location": _clean_string(metadata.get("course_location")) or "Not found in syllabus",
        "instructor_contact": _clean_string(metadata.get("instructor_contact"))
        or "Not found in syllabus",
        "instructor_office_hours": _clean_string(metadata.get("instructor_office_hours"))
        or "Not found in syllabus",
        "ta_contacts": _clean_contact_entries(metadata.get("ta_contacts")),
        "ta_office_hours": _clean_office_hour_entries(metadata.get("ta_office_hours")),
    }


def _post_json(url, payload):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise AIServiceError(str(exc)) from exc


def _parse_json_response(text):
    if isinstance(text, dict):
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _clean_string(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _clean_string_list(value):
    if not isinstance(value, list):
        return []

    cleaned = []
    for item in value:
        clean_item = _clean_string(item)
        if clean_item:
            cleaned.append(clean_item)
    return cleaned


def _clean_contact_entries(value):
    if not isinstance(value, list):
        return []

    entries = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_string(item.get("name"))
        contact = _clean_string(item.get("contact"))
        if not name and not contact:
            continue
        entries.append(
            {
                "name": name or "Not found in syllabus",
                "contact": contact or "Not found in syllabus",
            }
        )
    return entries


def _clean_office_hour_entries(value):
    if not isinstance(value, list):
        return []

    entries = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_string(item.get("name"))
        office_hours = _clean_string(item.get("office_hours"))
        if not name and not office_hours:
            continue
        entries.append(
            {
                "name": name or "Not found in syllabus",
                "office_hours": office_hours or "Not found in syllabus",
            }
        )
    return entries
