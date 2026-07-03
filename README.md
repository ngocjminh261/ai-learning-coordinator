# AI Learning Coordinator

A small Flask app that listens for Slack message events, counts learner questions, and can turn an admin-uploaded syllabus PDF into a quick fact sheet Slack canvas.

## What it does

- Receives Slack events at `/slack/events`
- Counts messages from each user that end with `?`
- Prints the live question count in the terminal
- Sends a private Slack alert to `ADMIN_SLACK_ID` when a user reaches the threshold
- Uses Slack search to include recent message context in the alert
- Lets an admin DM the bot a syllabus PDF
- Extracts course name, instructor, schedule, location, contacts, and office hours with Gemini or Ollama
- Creates a `Course quick fact + FAQ` canvas in `COURSE_CHANNEL_ID`

Question counts are stored in memory, so they reset when the app restarts.
Course canvas state is stored in `data/course_state.json` by default.

## Setup

Install dependencies:

```bash
pip3 install flask slack_sdk pypdf pytest
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
ADMIN_SLACK_IDS=UXXXXXXXXXX
COURSE_CHANNEL_ID=CXXXXXXXXXX
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
COURSE_STATE_STORAGE_PATH=data/course_state.json
PORT=8080
```

Add Slack scopes:

1. Go to your Slack app in the Slack API dashboard.
2. Open **OAuth & Permissions**.
3. Scroll to **Scopes**.
4. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add:
	   - `chat:write`
	   - `channels:history`
	   - `files:read`
	   - `canvases:write`
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
message.im
```

Reinstall the Slack app after changing scopes or event subscriptions.

## Test

Question-count flow:

1. Send 3 messages in a public Slack channel that each end with `?`.
2. Watch the terminal for the question count log.
3. Check the coordinator Slack DM for the alert.

Syllabus quick fact flow:

1. DM the bot a syllabus PDF from an admin Slack account.
2. Confirm the bot replies with a canvas ID.
3. Confirm `Course quick fact + FAQ` appears in `COURSE_CHANNEL_ID`.
4. Check `data/course_state.json` for the latest active syllabus/canvas state.

Run unit tests:

```bash
uv run python -m pytest
```
