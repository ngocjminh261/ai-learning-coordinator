from features.study_groups import StudyGroupOrchestrator
from services.storage_service import InMemoryStorage


class FakeBotClient:
    def conversations_list(self, types, exclude_archived):
        return {"ok": True, "channels": []}


class FakeSlackService:
    def __init__(self):
        self.bot_client = FakeBotClient()
        self.invites = []
        self.admin_messages = []
        self.channel_messages = []

    def create_public_channel(self, channel_name):
        return {"ok": True, "channel": {"id": "CLOUNGE", "name": channel_name}}

    def get_bot_user_id(self):
        return "UBOT"

    def invite_user_to_channel(self, group_channel_id, user_id):
        self.invites.append({"channel": group_channel_id, "user": user_id})
        return {"ok": True}

    def post_admin_message(self, text):
        self.admin_messages.append(text)
        return {"ok": True}

    def post_channel_message(self, channel_id, text):
        self.channel_messages.append({"channel": channel_id, "text": text})
        return {"ok": True}


def test_create_study_group_invites_students_not_bot(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    slack_service = FakeSlackService()
    orchestrator = StudyGroupOrchestrator(storage, slack_service)

    students = ["USTUDENT1", "USTUDENT2", "USTUDENT3"]
    for student in students:
        for index in range(3):
            storage.record_question(
                student,
                "machine learning",
                f"Question {index} about regression?",
                f"CQUESTIONS:{student}:{index}",
            )

    orchestrator.auto_orchestrate_study_group("machine learning", "USTUDENT3")

    invited_users = [invite["user"] for invite in slack_service.invites]
    assert invited_users == students
    assert "UBOT" not in invited_users
    assert storage.get_study_group("machine learning")["group_channel_id"] == "CLOUNGE"


def test_create_study_group_announces_to_origin_channel(tmp_path):
    storage = InMemoryStorage(course_state_path=tmp_path / "course_state.json")
    slack_service = FakeSlackService()
    orchestrator = StudyGroupOrchestrator(storage, slack_service)

    students = ["USTUDENT1", "USTUDENT2", "USTUDENT3"]
    for student in students:
        for index in range(3):
            storage.record_question(
                student,
                "machine learning",
                f"Question {index} about regression?",
                f"CQUESTIONS:{student}:{index}",
            )

    orchestrator.auto_orchestrate_study_group(
        "machine learning",
        "USTUDENT3",
        origin_channel_id="CQUESTIONS",
    )

    announcements = [
        message for message in slack_service.channel_messages
        if message["channel"] == "CQUESTIONS"
    ]
    assert len(announcements) == 1
    assert "New Study Lounge Alert" in announcements[0]["text"]
    assert "<#CLOUNGE>" in announcements[0]["text"]
