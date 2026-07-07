# CoursePilot

CoursePilot is a Slack-based teaching assistant that helps instructors spot confusion, coordinate support, and create reusable course resources without leaving Slack.

For the hackathon MVP, it listens to Slack activity, counts question-like messages, alerts the coordinator when students may need help, and can turn a DM'd syllabus PDF into a quick fact sheet Slack canvas.

## What it does

- Receives Slack events at `/slack/events`
- Counts messages from each user that end with `?`
- Prints the live question count in the terminal
- Sends a private Slack alert to `ADMIN_SLACK_ID` when a user reaches the threshold
- Uses Slack search to include recent message context in the alert
- Supports study-group coordination when multiple students struggle with the same topic
- Supports lecture-note based quiz generation, private Slack quiz delivery, and quiz summaries
- Supports Google Drive lecture-note import for quiz context
- Lets an instructor or teaching assistant DM the bot a PDF labeled as a syllabus
- Extracts course name, instructor, schedule, location, contacts, and office hours with Gemini or Ollama
- Creates a `Course quick fact + FAQ` canvas in `COURSE_CHANNEL_ID`

Question counts are stored in memory, so they reset when the app restarts.
Course canvas, lecture-note, quiz, and OAuth state are stored under `data/` by default.

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
SLACK_TA_CHANNEL_ID=C0XXXXXXX
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
COURSE_STATE_STORAGE_PATH=data/course_state.json
GOOGLE_DRIVE_MCP_SERVER_URL=https://drivemcp.googleapis.com/mcp/v1
GOOGLE_OAUTH_CLIENT_ID=your-google-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8080/google/oauth/callback
GOOGLE_OAUTH_TOKEN_PATH=data/google_oauth_token.json
GOOGLE_DRIVE_LECTURE_FILE_ID=optional-google-drive-file-id-for-demo
PORT=8080
```

Only `SLACK_BOT_TOKEN`, `SLACK_USER_TOKEN`, `COURSE_CHANNEL_ID`, and either `ADMIN_SLACK_ID` or `ADMIN_SLACK_IDS` are required to start the app. Gemini, Ollama, and Google Drive values are needed for AI syllabus extraction, quiz generation, and Drive lecture-note import.

Add Slack scopes:

1. Go to your Slack app in the Slack API dashboard.
2. Open **OAuth & Permissions**.
3. Scroll to **Scopes**.
4. Under **Bot Token Scopes**, click **Add an OAuth Scope** and add:
	   - `chat:write`
	   - `channels:read`
	   - `channels:history`
	   - `files:read`
	   - `canvases:write`
	   - `users:read`
	   - `im:write`
	   - `reactions:read`
	   - `channels:write.invites`
5. Under **User Token Scopes**, click **Add an OAuth Scope** and add:
	   - `search:read`
	   - `channels:write`
	   - `channels:write.invites`
6. Click **Reinstall to Workspace** so Slack applies the new scopes.

If you want the app to listen in private channels, add `groups:history` under **Bot Token Scopes** too.
If you want the app to create or invite users into private study groups, add the matching private-channel write scopes as well.

To get the values for `.env`:

1. In **OAuth & Permissions**, copy **Bot User OAuth Token** into `SLACK_BOT_TOKEN`.
2. Copy **User OAuth Token** into `SLACK_USER_TOKEN`.
3. In Slack, open your profile, click the three-dot menu, then click **Copy member ID**. Use that value for `ADMIN_SLACK_ID`.

For Google Drive lecture-note import:

1. Create a Google OAuth client.
2. Add this redirect URI to the OAuth client:

```text
http://localhost:8080/google/oauth/callback
```

3. Fill in `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.
4. After starting the Flask app, open this route in your browser:

```text
http://localhost:8080/google/oauth/start
```

The callback saves the OAuth token to `GOOGLE_OAUTH_TOKEN_PATH`.

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
reaction_added
```

Reinstall the Slack app after changing scopes or event subscriptions.

## Test

Study-group / question-count flow:

1. Send question messages in a public Slack channel that each end with `?` and include a known topic keyword.
2. Watch the terminal for the question count log.
3. When one student reaches 3 matching questions, check the coordinator Slack DM for the individual help alert.
4. When 3 students reach the threshold for the same topic, confirm the app creates a public `lounge-...` study channel and invites the students.

Quiz flow:

1. From a Slack user whose profile title is `Instructor` or `Teaching Assistant`, DM the bot `lecture note`.
2. Reply `1` to paste notes manually, or `2` to import a recent Google Drive file.
3. For manual notes, use this format:

```text
Topic: Data preprocessing
Note:
Cleaning null values helps students prepare model-ready data.
```

4. Send `quiz`.
5. Pick a topic number.
6. Review the draft, then reply `approve`.
7. Have students answer by reacting with `:one:`, `:two:`, or `:three:`.
8. Send `quiz summary` to receive aggregate understanding.

Syllabus quick fact flow:

1. DM the bot a PDF named `syllabus.pdf`, or upload a PDF with `syllabus` in the DM text, from an Instructor or Teaching Assistant Slack account.
2. Confirm the bot replies with a canvas ID.
3. Confirm `Course quick fact + FAQ` appears in `COURSE_CHANNEL_ID`.
4. Check `data/course_state.json` for the latest active syllabus/canvas state.

Run unit tests:

```bash
uv run python -m pytest
```
