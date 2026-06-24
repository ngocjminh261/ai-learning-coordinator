# AI Learning Coordinator

A small Flask app that listens for Slack message events, counts learner questions, and privately alerts a coordinator when someone asks 3 or more questions.

## What it does

- Receives Slack events at `/slack/events`
- Counts messages from each user that end with `?`
- Prints the live question count in the terminal
- Sends a private Slack alert to `ADMIN_SLACK_ID` when a user reaches the threshold
- Uses Slack search to include recent message context in the alert

Question counts are stored in memory, so they reset when the app restarts.

## Setup

Install dependencies:

```bash
pip3 install flask slack_sdk
```

Create your local env file:

```bash
cp .env.example .env
```

Then fill in `.env`:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_TOKEN=xoxp-your-user-token
ADMIN_SLACK_ID=UXXXXXXXXXX
PORT=8080
```

Add Slack scopes:

1. Go to your Slack app in the Slack API dashboard.
2. Open **OAuth & Permissions**.
3. Scroll to **Scopes**.
4. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add:
   - `chat:write`
   - `channels:history`
5. Under **User Token Scopes**, click **Add an OAuth Scope** and add:
   - `search:read`
6. Click **Reinstall to Workspace** so Slack applies the new scopes.

If you want the app to listen in private channels, add `groups:history` under **Bot Token Scopes** too.

To get the values for `.env`:

1. In **OAuth & Permissions**, copy **Bot User OAuth Token** into `SLACK_BOT_TOKEN`.
2. Copy **User OAuth Token** into `SLACK_USER_TOKEN`.
3. In Slack, open your profile, click the three-dot menu, then click **Copy member ID**. Use that value for `ADMIN_SLACK_ID`.

## Run locally

Start the Flask app:

```bash
python3 app.py
```

In another terminal, expose the local server:

```bash
ngrok http 8080
```

In Slack Event Subscriptions, set the Request URL to:

```text
https://your-ngrok-url.ngrok-free.dev/slack/events
```

Subscribe the bot to:

```text
message.channels
```

Reinstall the Slack app after changing scopes or event subscriptions.

## Test

1. Send 3 messages in a public Slack channel that each end with `?`.
2. Watch the terminal for the question count log.
3. Check the coordinator Slack DM for the alert.
