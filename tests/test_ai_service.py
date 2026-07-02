import pytest

from services.ai_service import AIServiceError, SyllabusAIService, normalize_course_metadata


def test_normalize_course_metadata_handles_missing_fact_sheet_fields():
    metadata = normalize_course_metadata(
        {
            "course_name": "Intro to ML",
            "instructor": None,
            "course_schedule": ["Mondays 10 AM", "", None],
            "course_location": None,
            "instructor_contact": "prof@example.edu",
            "instructor_office_hours": None,
            "ta_contacts": [
                {
                    "name": "TA One",
                    "contact": "ta@example.edu",
                },
                {
                    "name": "",
                    "contact": "",
                },
            ],
            "ta_office_hours": [{"name": "TA One", "office_hours": "Tue 2-3 PM"}],
        }
    )

    assert metadata["course_name"] == "Intro to ML"
    assert metadata["instructor"] == "Not found in syllabus"
    assert metadata["course_schedule"] == ["Mondays 10 AM"]
    assert metadata["course_location"] == "Not found in syllabus"
    assert metadata["instructor_contact"] == "prof@example.edu"
    assert metadata["instructor_office_hours"] == "Not found in syllabus"
    assert metadata["ta_contacts"] == [{"name": "TA One", "contact": "ta@example.edu"}]
    assert metadata["ta_office_hours"] == [{"name": "TA One", "office_hours": "Tue 2-3 PM"}]


def test_gemini_success_is_used(monkeypatch):
    service = SyllabusAIService(gemini_api_key="key")

    monkeypatch.setattr(
        service,
        "_call_gemini",
        lambda prompt: {
            "course_name": "Gemini Course",
            "instructor": "Dr. Gemini",
            "course_schedule": [],
            "course_location": None,
            "instructor_contact": None,
            "instructor_office_hours": None,
            "ta_contacts": [],
            "ta_office_hours": [],
        },
    )

    metadata = service.extract_course_metadata("syllabus")

    assert metadata["course_name"] == "Gemini Course"
    assert metadata["instructor"] == "Dr. Gemini"


def test_gemini_failure_falls_back_to_ollama(monkeypatch):
    service = SyllabusAIService(gemini_api_key="key")

    def fail_gemini(prompt):
        raise AIServiceError("boom")

    monkeypatch.setattr(service, "_call_gemini", fail_gemini)
    monkeypatch.setattr(
        service,
        "_call_ollama",
        lambda prompt: {
            "course_name": "Ollama Course",
            "instructor": None,
            "course_schedule": [],
            "course_location": None,
            "instructor_contact": None,
            "instructor_office_hours": None,
            "ta_contacts": [],
            "ta_office_hours": [],
        },
    )

    metadata = service.extract_course_metadata("syllabus")

    assert metadata["course_name"] == "Ollama Course"
    assert metadata["instructor"] == "Not found in syllabus"


def test_all_ai_providers_fail_with_clear_error(monkeypatch):
    service = SyllabusAIService(gemini_api_key="key")

    def fail(prompt):
        raise AIServiceError("failed")

    monkeypatch.setattr(service, "_call_gemini", fail)
    monkeypatch.setattr(service, "_call_ollama", fail)

    with pytest.raises(AIServiceError) as error:
        service.extract_course_metadata("syllabus")

    assert "Gemini failed" in str(error.value)
    assert "Ollama failed" in str(error.value)
