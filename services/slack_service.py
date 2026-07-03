from urllib.request import Request, urlopen

from slack_sdk import WebClient


class SlackService:
    def __init__(self, bot_token, user_token, admin_slack_id):
        self.admin_slack_id = admin_slack_id
        self.bot_token = bot_token
        self.bot_client = WebClient(token=bot_token)
        self.user_client = WebClient(token=user_token)

    def get_bot_user_id(self):
        return self.bot_client.auth_test()["user_id"]

    def post_admin_message(self, text):
        return self.bot_client.chat_postMessage(channel=self.admin_slack_id, text=text)

    def post_channel_message(self, channel_id, text):
        return self.bot_client.chat_postMessage(channel=channel_id, text=text)

    def post_message(self, channel_id, text):
        return self.bot_client.chat_postMessage(channel=channel_id, text=text)

    def get_user_profile_title(self, user_id):
        response = self.bot_client.users_info(user=user_id)
        profile = response.get("user", {}).get("profile", {})
        return profile.get("title", "")

    def download_file(self, url):
        request = Request(url, headers={"Authorization": f"Bearer {self.bot_token}"})
        with urlopen(request) as response:
            return response.read()

    def create_canvas(self, channel_id, title, markdown):
        return self.bot_client.api_call(
            "canvases.create",
            json={
                "channel_id": channel_id,
                "title": title,
                "document_content": {
                    "type": "markdown",
                    "markdown": markdown,
                },
            },
        )

    def search_recent_questions(self):
        return self.user_client.search_messages(query="?", count=20, sort="timestamp")

    def create_public_channel(self, channel_name):
        return self.user_client.conversations_create(name=channel_name, is_private=False)

    def invite_user_to_channel(self, channel_id, user_id):
        return self.user_client.conversations_invite(channel=channel_id, users=user_id)
