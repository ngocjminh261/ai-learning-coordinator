from services.storage_service import InMemoryStorage


def test_course_state_json_is_written_and_replaced(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")

    first_state = storage.save_course_canvas_state(
        course_map={
            "source_name": "syllabus-a.pdf",
            "course_name": "Course A",
            "canvas_title": "Course A FAQ",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        canvas_id="FCOURSEA",
        channel_id="CGENERAL",
    )
    second_state = storage.save_course_canvas_state(
        course_map={
            "source_name": "syllabus-b.pdf",
            "course_name": "Course B",
            "canvas_title": "Course B FAQ",
            "created_at": "2026-01-02T00:00:00+00:00",
        },
        canvas_id="FCOURSEB",
        channel_id="CGENERAL",
    )

    assert first_state["faq_canvas"]["canvas_id"] == "FCOURSEA"
    assert second_state["faq_canvas"]["canvas_id"] == "FCOURSEB"

    loaded_state = storage.load_course_state()
    assert loaded_state["course_map"]["source_name"] == "syllabus-b.pdf"
    assert loaded_state["course_map"]["course_name"] == "Course B"
    assert loaded_state["faq_canvas"]["canvas_id"] == "FCOURSEB"
