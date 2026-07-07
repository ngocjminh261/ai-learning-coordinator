from flask import Flask

from events.slack_events import handle_slack_event_payload
from services.storage_service import InMemoryStorage


class FakeStudyGroupOrchestrator:
    def __init__(self):
        self.calls = []

    def auto_orchestrate_study_group(self, topic, user_id, channel_id=None):
        self.calls.append(
            {
                "topic": topic,
                "user_id": user_id,
                "channel_id": channel_id,
            }
        )


class FakeQuizMaker:
    def __init__(self):
        self.message_events = []

    def handle_message_event(self, event):
        self.message_events.append(event)
        return {"handled": True, "status": "handled"}


def test_record_question_dedupes_by_message_key(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")

    first_count, first_recorded = storage.record_question(
        "USTUDENT",
        "machine learning",
        "How does regression work?",
        "CQUESTIONS:123.456",
    )
    duplicate_count, duplicate_recorded = storage.record_question(
        "USTUDENT",
        "machine learning",
        "How does regression work?",
        "CQUESTIONS:123.456",
    )

    assert first_count == 1
    assert first_recorded is True
    assert duplicate_count == 1
    assert duplicate_recorded is False
    assert storage.get_question_history("USTUDENT", "machine learning") == [
        "How does regression work?"
    ]


def test_duplicate_slack_event_does_not_retrigger_threshold(tmp_path):
    app = Flask(__name__)
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    orchestrator = FakeStudyGroupOrchestrator()

    events = [
        {
            "type": "message",
            "user": "USTUDENT",
            "channel": "CQUESTIONS",
            "ts": "1.000",
            "text": "How does regression work?",
        },
        {
            "type": "message",
            "user": "USTUDENT",
            "channel": "CQUESTIONS",
            "ts": "2.000",
            "text": "Can my model overfit?",
        },
        {
            "type": "message",
            "user": "USTUDENT",
            "channel": "CQUESTIONS",
            "ts": "3.000",
            "text": "Why does classification fail?",
        },
        {
            "type": "message",
            "user": "USTUDENT",
            "channel": "CQUESTIONS",
            "ts": "3.000",
            "text": "Why does classification fail?",
        },
    ]

    for event in events:
        with app.test_request_context(json={"event": event}):
            handle_slack_event_payload(storage, orchestrator)

    assert storage.get_topic_count("USTUDENT", "machine learning") == 3
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]["topic"] == "machine learning"
    assert orchestrator.calls[0]["user_id"] == "USTUDENT"
    assert orchestrator.calls[0]["channel_id"] == "CQUESTIONS"


def test_duplicate_slack_command_event_is_only_routed_once(tmp_path):
    app = Flask(__name__)
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    orchestrator = FakeStudyGroupOrchestrator()
    quiz_maker = FakeQuizMaker()
    payload = {
        "event_id": "EvLECTURENOTE",
        "event": {
            "type": "message",
            "user": "UINSTRUCTOR",
            "channel": "DINSTRUCTOR",
            "channel_type": "im",
            "ts": "123.456",
            "text": "lecture note",
        },
    }

    for _ in range(2):
        with app.test_request_context(json=payload):
            handle_slack_event_payload(
                storage,
                orchestrator,
                quiz_maker=quiz_maker,
            )

    assert len(quiz_maker.message_events) == 1
