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

    def is_bot_user(self, user_id):
        response = self.bot_client.users_info(user=user_id)
        return bool(response.get("user", {}).get("is_bot"))

    def list_channel_members(self, channel_id):
        members = []
        cursor = None
        while True:
            response = self.bot_client.conversations_members(
                channel=channel_id,
                cursor=cursor,
            )
            members.extend(response.get("members", []))
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                return members

    def open_dm(self, user_id):
        response = self.bot_client.conversations_open(users=user_id)
        return response["channel"]["id"]

    def post_dm(self, user_id, text):
        channel_id = self.open_dm(user_id)
        return self.post_message(channel_id, text)

    def get_message_reactions(self, channel_id, message_ts):
        response = self.bot_client.reactions_get(channel=channel_id, timestamp=message_ts)
        return response.get("message", {}).get("reactions", [])

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
        return self.user_client.search_messages(query="?", count=30, sort="timestamp")

    def create_public_channel(self, channel_name):
        return self.user_client.conversations_create(name=channel_name, is_private=False)

    def invite_user_to_channel(self, channel_id, user_id):
        return self.user_client.conversations_invite(channel=channel_id, users=user_id)
