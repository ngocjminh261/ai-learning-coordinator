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


def test_canvas_state_preserves_feature_two_state(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    storage.save_lecture_note(
        topic="EDA",
        note_text="EDA means exploring data before modeling.",
        sender="UINSTRUCTOR",
        channel="DINSTRUCTOR",
    )

    storage.save_course_canvas_state(
        course_map={
            "source_name": "syllabus.pdf",
            "course_name": "EDA Course",
            "canvas_title": "Course quick fact + FAQ",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        canvas_id="FCANVAS",
        channel_id="CCOURSE",
    )

    loaded_state = storage.load_course_state()
    assert loaded_state["faq_canvas"]["canvas_id"] == "FCANVAS"
    assert loaded_state["lecture_notes"][0]["topic"] == "EDA"


def test_feature_two_storage_helpers_round_trip(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")

    note = storage.save_lecture_note(
        topic="EDA",
        note_text="Visualize distributions with histograms.",
        sender="UINSTRUCTOR",
        channel="DINSTRUCTOR",
    )
    storage.set_pending_action("UINSTRUCTOR", "quiz_topic_number", topics=["EDA"])
    storage.save_quiz_draft(
        "UINSTRUCTOR",
        {
            "topic": "EDA",
            "questions": [
                {
                    "id": "q1",
                    "text": "What does a histogram show?",
                    "choices": {"one": "Distribution", "two": "Map", "three": "User ID"},
                    "correct_reaction": "one",
                }
            ],
        },
    )
    storage.save_active_quiz(
        "quiz-1",
        {
            "topic": "EDA",
            "sent_questions": [{"id": "q1", "channel": "DUSER", "ts": "123.456"}],
            "responses": {},
            "owner": "UINSTRUCTOR",
        },
    )

    assert note["topic"] == "EDA"
    assert storage.get_lecture_note_topics() == ["EDA"]
    assert storage.get_notes_for_topic("eda")[0]["text"].startswith("Visualize")
    assert storage.get_pending_action("UINSTRUCTOR")["state"] == "quiz_topic_number"
    assert storage.get_quiz_draft("UINSTRUCTOR")["topic"] == "EDA"

    quiz_id, quiz, question = storage.find_quiz_question_by_message("DUSER", "123.456")
    assert quiz_id == "quiz-1"
    assert quiz["topic"] == "EDA"
    assert question["id"] == "q1"
    current_quiz_id, current_quiz = storage.get_current_quiz_for_owner("UINSTRUCTOR")
    assert current_quiz_id == "quiz-1"
    assert current_quiz["topic"] == "EDA"

    storage.record_quiz_response("quiz-1", "q1", "USTUDENT", "one")
    assert storage.get_active_quizzes()["quiz-1"]["responses"]["USTUDENT"]["q1"] == "one"

    storage.clear_pending_action("UINSTRUCTOR")
    storage.clear_quiz_draft("UINSTRUCTOR")
    assert storage.get_pending_action("UINSTRUCTOR") is None
    assert storage.get_quiz_draft("UINSTRUCTOR") is None
