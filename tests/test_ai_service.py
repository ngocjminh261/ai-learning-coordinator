import pytest

from services.ai_service import (
    AIServiceError,
    SyllabusAIService,
    build_quiz_prompt,
    normalize_course_metadata,
    normalize_quiz_draft,
)


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


def test_build_quiz_prompt_includes_topic_and_notes():
    prompt = build_quiz_prompt(
        "EDA",
        [
            {
                "text": "Histograms show numeric distributions.",
            }
        ],
    )

    assert "EDA" in prompt
    assert "Histograms show numeric distributions." in prompt
    assert '"correct_reaction": "one"' in prompt


def test_normalize_quiz_draft_accepts_valid_questions():
    draft = normalize_quiz_draft(
        "EDA",
        {
            "topic": "EDA",
            "questions": [
                {
                    "text": "What does a histogram show?",
                    "choices": {
                        "one": "Distribution",
                        "two": "A single category",
                        "three": "A user profile",
                    },
                    "correct_reaction": "one",
                },
                {
                    "text": "Which chart compares category counts?",
                    "choices": {
                        "one": "Scatter plot",
                        "two": "Bar chart",
                        "three": "Line chart",
                    },
                    "correct_reaction": "two",
                },
            ],
        },
    )

    assert draft["topic"] == "EDA"
    assert draft["questions"][0]["id"] == "q1"
    assert draft["questions"][1]["correct_reaction"] == "two"


def test_normalize_quiz_draft_rejects_too_few_valid_questions():
    with pytest.raises(AIServiceError):
        normalize_quiz_draft(
            "EDA",
            {
                "questions": [
                    {
                        "text": "Only one question?",
                        "choices": {"one": "Yes", "two": "No", "three": "Maybe"},
                        "correct_reaction": "one",
                    }
                ]
            },
        )


def test_generate_quiz_draft_uses_ai_provider(monkeypatch):
    service = SyllabusAIService(gemini_api_key="key")

    monkeypatch.setattr(
        service,
        "_call_gemini",
        lambda prompt: {
            "topic": "EDA",
            "questions": [
                {
                    "text": "What does EDA help us inspect?",
                    "choices": {
                        "one": "Data patterns",
                        "two": "Production servers",
                        "three": "Passwords",
                    },
                    "correct_reaction": "one",
                },
                {
                    "text": "Which plot shows outliers?",
                    "choices": {
                        "one": "Pie chart",
                        "two": "Box plot",
                        "three": "Logo",
                    },
                    "correct_reaction": "two",
                },
            ],
        },
    )

    draft = service.generate_quiz_draft("EDA", [{"text": "EDA notes"}])

    assert draft["questions"][0]["choices"]["one"] == "Data patterns"
