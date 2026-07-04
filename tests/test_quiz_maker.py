from features.quiz_maker import (
    QuizMaker,
    format_quiz_draft,
    format_student_quiz_intro,
    format_student_question,
    parse_structured_lecture_note,
)
from services.storage_service import InMemoryStorage


class FakeSlackService:
    def __init__(self):
        self.messages = []
        self.dms = []
        self.before_post_dm = None
        self.reactions_by_message = {}
        self.user_titles = {
            "UINSTRUCTOR": "Instructor",
            "USTUDENT1": "",
            "USTUDENT2": "",
            "UBOT": "",
        }
        self.bot_users = {"UBOT"}
        self.channel_members = ["UINSTRUCTOR", "USTUDENT1", "USTUDENT2", "UBOT"]

    def post_message(self, channel_id, text):
        self.messages.append({"channel": channel_id, "text": text})
        return {"ok": True, "channel": channel_id, "ts": f"{len(self.messages)}.000"}

    def post_dm(self, user_id, text):
        if self.before_post_dm:
            callback = self.before_post_dm
            self.before_post_dm = None
            callback()

        channel_id = f"D{user_id}"
        self.dms.append({"user": user_id, "channel": channel_id, "text": text})
        return {"ok": True, "channel": channel_id, "ts": f"{len(self.dms)}.000"}

    def get_user_profile_title(self, user_id):
        return self.user_titles.get(user_id, "")

    def list_channel_members(self, channel_id):
        return list(self.channel_members)

    def is_bot_user(self, user_id):
        return user_id in self.bot_users

    def get_message_reactions(self, channel_id, message_ts):
        return self.reactions_by_message.get((channel_id, message_ts), [])


class FakeAIService:
    def __init__(self):
        self.calls = []
        self.before_generate = None

    def generate_quiz_draft(self, topic, notes):
        self.calls.append({"topic": topic, "notes": notes})
        if self.before_generate:
            callback = self.before_generate
            self.before_generate = None
            callback()

        return {
            "topic": topic,
            "questions": [
                {
                    "id": "q1",
                    "text": "What does EDA help analysts inspect?",
                    "choices": {
                        "one": "Data patterns",
                        "two": "Access tokens",
                        "three": "Server uptime",
                    },
                    "correct_reaction": "one",
                },
                {
                    "id": "q2",
                    "text": "Which chart shows numeric distributions?",
                    "choices": {
                        "one": "Logo",
                        "two": "Histogram",
                        "three": "Org chart",
                    },
                    "correct_reaction": "two",
                },
            ],
        }


def build_quiz_maker(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    slack_service = FakeSlackService()
    ai_service = FakeAIService()
    quiz_maker = QuizMaker(
        storage=storage,
        slack_service=slack_service,
        ai_service=ai_service,
        course_channel_id="CCOURSE",
    )
    return quiz_maker, storage, slack_service, ai_service


def message_event(text, user_id="UINSTRUCTOR", channel_id="DINSTRUCTOR", ts=None):
    event = {
        "type": "message",
        "channel_type": "im",
        "channel": channel_id,
        "user": user_id,
        "text": text,
    }
    if ts:
        event["ts"] = ts
    return event


def test_parse_structured_lecture_note():
    parsed = parse_structured_lecture_note(
        "Topic: EDA\nNote:\nHistograms show distributions."
    )

    assert parsed == {"topic": "EDA", "text": "Histograms show distributions."}
    assert parse_structured_lecture_note("EDA notes") is None


def test_lecture_note_command_stores_structured_note(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)

    start_result = quiz_maker.handle_message_event(message_event("lecture note"))
    save_result = quiz_maker.handle_message_event(
        message_event("Topic: EDA\nNote:\nHistograms show distributions.")
    )

    assert start_result["status"] == "waiting_for_lecture_note"
    assert save_result["status"] == "saved_lecture_note"
    assert storage.get_lecture_note_topics() == ["EDA"]
    assert storage.get_pending_action("UINSTRUCTOR") is None
    assert "Saved lecture note" in slack_service.messages[-1]["text"]


def test_quiz_topic_selection_generates_draft(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_lecture_note("EDA", "Histograms show distributions.", "UINSTRUCTOR", "DINSTRUCTOR")

    topic_result = quiz_maker.handle_message_event(message_event("quiz"))
    draft_result = quiz_maker.handle_message_event(message_event("1"))

    assert topic_result["status"] == "waiting_for_quiz_topic_number"
    assert "1. EDA" in slack_service.messages[-2]["text"]
    assert draft_result["status"] == "sent_quiz_draft"
    assert ai_service.calls[0]["topic"] == "EDA"
    assert storage.get_pending_action("UINSTRUCTOR")["state"] == "quiz_approval"
    assert "Correct answer: :one:" in slack_service.messages[-1]["text"]


def test_duplicate_topic_number_does_not_generate_draft_twice(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_lecture_note("EDA", "Histograms show distributions.", "UINSTRUCTOR", "DINSTRUCTOR")
    duplicate_result = {}

    def duplicate_topic_number():
        duplicate_result.update(quiz_maker.handle_message_event(message_event("1")))

    quiz_maker.handle_message_event(message_event("quiz"))
    ai_service.before_generate = duplicate_topic_number
    first_result = quiz_maker.handle_message_event(message_event("1"))

    assert first_result["status"] == "sent_quiz_draft"
    assert duplicate_result["status"] == "quiz_generation_in_progress"
    assert len(ai_service.calls) == 1
    draft_previews = [
        message
        for message in slack_service.messages
        if message["text"].startswith("Quiz draft:")
    ]
    assert len(draft_previews) == 1


def test_approve_sends_one_dm_per_question_to_non_staff_students(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_quiz_draft("UINSTRUCTOR", ai_service.generate_quiz_draft("EDA", []))

    result = quiz_maker.handle_message_event(message_event("approve"))

    assert result["status"] == "sent_quiz"
    assert [dm["user"] for dm in slack_service.dms] == [
        "USTUDENT1",
        "USTUDENT1",
        "USTUDENT1",
        "USTUDENT2",
        "USTUDENT2",
        "USTUDENT2",
    ]
    assert "*QUIZ: EDA*" in slack_service.dms[0]["text"]
    assert "React to each question message" in slack_service.dms[0]["text"]
    assert "*_Question 1/2: What does EDA help analysts inspect?_*" in slack_service.dms[1]["text"]
    assert "QUIZ: EDA" not in slack_service.dms[1]["text"]
    assert storage.get_quiz_draft("UINSTRUCTOR") is None
    active_quiz = next(iter(storage.get_active_quizzes().values()))
    assert len(active_quiz["sent_questions"]) == 4


def test_duplicate_approve_does_not_send_quiz_twice(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_quiz_draft("UINSTRUCTOR", ai_service.generate_quiz_draft("EDA", []))

    first_result = quiz_maker.handle_message_event(message_event("approve"))
    second_result = quiz_maker.handle_message_event(message_event("approve"))

    assert first_result["status"] == "sent_quiz"
    assert second_result["status"] == "no_draft_to_approve"
    assert len(slack_service.dms) == 6
    assert len(storage.get_active_quizzes()) == 1


def test_duplicate_approve_during_send_reports_in_progress(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_quiz_draft("UINSTRUCTOR", ai_service.generate_quiz_draft("EDA", []))
    duplicate_result = {}

    def duplicate_approve():
        duplicate_result.update(quiz_maker.handle_message_event(message_event("approve")))

    slack_service.before_post_dm = duplicate_approve

    first_result = quiz_maker.handle_message_event(message_event("approve"))

    assert first_result["status"] == "sent_quiz"
    assert duplicate_result["status"] == "quiz_send_in_progress"
    assert len(slack_service.dms) == 6
    assert "Sending quiz..." in slack_service.messages[0]["text"]


def test_reaction_event_records_response_and_summary(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    draft = ai_service.generate_quiz_draft("EDA", [])
    storage.save_quiz_draft("UINSTRUCTOR", draft)
    quiz_maker.handle_message_event(message_event("approve"))

    active_quiz = next(iter(storage.get_active_quizzes().values()))
    sent_question = active_quiz["sent_questions"][0]
    reaction_result = quiz_maker.handle_reaction_event(
        {
            "type": "reaction_added",
            "reaction": "one",
            "user": "USTUDENT1",
            "item": {
                "channel": sent_question["channel"],
                "ts": sent_question["ts"],
            },
        }
    )
    summary_result = quiz_maker.handle_message_event(message_event("quiz summary"))

    assert reaction_result["status"] == "recorded_quiz_response"
    assert summary_result["status"] == "sent_quiz_summary"
    assert "Responses: 1/2" in slack_service.messages[-1]["text"]
    assert "q1: :one: 1" in slack_service.messages[-1]["text"]


def test_summary_refreshes_responses_from_slack_reactions(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    draft = ai_service.generate_quiz_draft("EDA", [])
    storage.save_quiz_draft("UINSTRUCTOR", draft)
    quiz_maker.handle_message_event(message_event("approve"))

    active_quiz = next(iter(storage.get_active_quizzes().values()))
    sent_question = active_quiz["sent_questions"][0]
    slack_service.reactions_by_message[(sent_question["channel"], sent_question["ts"])] = [
        {"name": "one", "users": ["USTUDENT1"]},
    ]

    summary_result = quiz_maker.handle_message_event(message_event("quiz summary"))

    assert summary_result["status"] == "sent_quiz_summary"
    assert "Responses: 1/2" in slack_service.messages[-1]["text"]
    current_quiz_id, current_quiz = storage.get_current_quiz_for_owner("UINSTRUCTOR")
    assert current_quiz["responses"]["USTUDENT1"]["q1"] == "one"


def test_summary_uses_current_quiz_for_owner(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    storage.save_active_quiz(
        "quiz-old",
        {
            "topic": "Old quiz",
            "owner": "UINSTRUCTOR",
            "questions": [],
            "recipients": [],
            "sent_questions": [],
            "responses": {},
        },
    )
    storage.save_active_quiz(
        "quiz-new",
        {
            "topic": "New quiz",
            "owner": "UINSTRUCTOR",
            "questions": [],
            "recipients": [],
            "sent_questions": [],
            "responses": {},
        },
    )

    result = quiz_maker.handle_message_event(message_event("quiz summary"))

    assert result["status"] == "sent_quiz_summary"
    assert "Quiz summary: New quiz" in slack_service.messages[-1]["text"]
    assert "Quiz ID: quiz-new" in slack_service.messages[-1]["text"]


def test_duplicate_quiz_summary_event_is_ignored(tmp_path):
    quiz_maker, storage, slack_service, ai_service = build_quiz_maker(tmp_path)
    draft = ai_service.generate_quiz_draft("EDA", [])
    storage.save_quiz_draft("UINSTRUCTOR", draft)
    quiz_maker.handle_message_event(message_event("approve"))

    summary_event = message_event("quiz summary", ts="111.222")
    first_result = quiz_maker.handle_message_event(summary_event)
    second_result = quiz_maker.handle_message_event(summary_event)

    assert first_result["status"] == "sent_quiz_summary"
    assert second_result["status"] == "duplicate_quiz_summary"
    summary_messages = [
        message
        for message in slack_service.messages
        if message["text"].startswith("Quiz summary:")
    ]
    assert len(summary_messages) == 1


def test_formatters_show_staff_and_student_versions():
    draft = FakeAIService().generate_quiz_draft("EDA", [])

    staff_text = format_quiz_draft(draft)
    intro_text = format_student_quiz_intro("EDA", 2)
    student_text = format_student_question(draft["questions"][0], 1, 2)

    assert "Correct answer" in staff_text
    assert "Correct answer" not in student_text
    assert "*QUIZ: EDA*" in intro_text
    assert "React to each question message" in intro_text
    assert "QUIZ: EDA" not in student_text
    assert "*_Question 1/2: What does EDA help analysts inspect?_*" in student_text
    assert "React with :one:" not in student_text
