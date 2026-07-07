from services.slack_service import SlackService


class FakeSlackClient:
    def __init__(self):
        self.created_channels = []
        self.invites = []

    def conversations_create(self, name, is_private):
        self.created_channels.append({"name": name, "is_private": is_private})
        return {"ok": True, "channel": {"id": "CLOUNGE", "name": name}}

    def conversations_invite(self, channel, users):
        self.invites.append({"channel": channel, "users": users})
        return {"ok": True}


def test_create_public_channel_uses_bot_client():
    service = SlackService(
        bot_token="xoxb-test",
        user_token="xoxp-test",
        admin_slack_id="UADMIN",
    )
    bot_client = FakeSlackClient()
    user_client = FakeSlackClient()
    service.bot_client = bot_client
    service.user_client = user_client

    response = service.create_public_channel("lounge-machine-learning-123")

    assert response["ok"] is True
    assert bot_client.created_channels == [
        {"name": "lounge-machine-learning-123", "is_private": False}
    ]
    assert user_client.created_channels == []


def test_invite_user_to_channel_uses_bot_client():
    service = SlackService(
        bot_token="xoxb-test",
        user_token="xoxp-test",
        admin_slack_id="UADMIN",
    )
    bot_client = FakeSlackClient()
    user_client = FakeSlackClient()
    service.bot_client = bot_client
    service.user_client = user_client

    response = service.invite_user_to_channel("CLOUNGE", "USTUDENT")

    assert response["ok"] is True
    assert bot_client.invites == [{"channel": "CLOUNGE", "users": "USTUDENT"}]
    assert user_client.invites == []
