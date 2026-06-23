This repo is a small Flask app that listens for Slack events and alerts an admin when a Slack user asks 3 or more questions.

Here is the step-by-step flow in [app.py](/Users/minhle/Documents/working-repo/ai-learning-coordinator/app.py:1).

1. Imports

```python
import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
```

The app uses:

- `Flask` to create a small web server
- `request` to read incoming Slack webhook data
- `jsonify` to send JSON responses back to Slack
- `WebClient` to call Slack APIs

`os` is imported but currently unused.

2. Create the Flask app

```python
app = Flask(__name__)
```

This creates the backend web application. Slack will send HTTP requests to this app.

3. Slack tokens and admin ID

```python
SLACK_BOT_TOKEN = "..."
SLACK_USER_TOKEN = "..."
ADMIN_SLACK_ID = "U0BC9D267DG"
```

These values authenticate with Slack.

- `SLACK_BOT_TOKEN`: lets the bot send messages
- `SLACK_USER_TOKEN`: lets the app search Slack messages
- `ADMIN_SLACK_ID`: the Slack user who receives private alerts

Important: these tokens should not be committed in code. They should usually come from environment variables like `os.environ["SLACK_BOT_TOKEN"]`.

4. Create Slack clients

```python
bot_client = WebClient(token=SLACK_BOT_TOKEN)
user_client = WebClient(token=SLACK_USER_TOKEN)
```

There are two Slack API clients:

- `bot_client`: used to send admin alert messages
- `user_client`: used to search Slack message history

5. In-memory question tracker

```python
question_database = {}
```

This dictionary tracks how many question messages each user has sent.

Example shape:

```python
{
    "U123": 1,
    "U456": 3
}
```

This data resets every time the Python app restarts.

6. Define the Slack webhook route

```python
@app.route("/slack/events", methods=["POST"])
def slack_events():
```

Slack sends event data to:

```text
/slack/events
```

Only `POST` requests are accepted.

7. Read Slack’s JSON payload

```python
data = request.json
```

This gets the JSON body sent by Slack.

8. Handle Slack verification challenge

```python
if data and "challenge" in data:
    return jsonify({"challenge": data["challenge"]})
```

When you first configure the Slack Request URL, Slack sends a `challenge`.

The app must send it back to prove the endpoint is real.

9. Handle normal Slack events

```python
if data and "event" in data:
    event = data["event"]
```

Slack wraps the actual message event inside the `event` field.

10. Ignore bot messages

```python
if event.get("type") == "message" and not event.get("bot_id"):
```

This means:

- only handle Slack messages
- skip messages sent by bots

That prevents the bot from reacting to itself.

11. Extract message info

```python
message_text = event.get("text", "").strip()
channel_id = event.get("channel")
user_id = event.get("user")
```

The app pulls out:

- the message text
- the channel ID
- the Slack user ID

`channel_id` is currently extracted but not used.

12. Count messages that end with `?`

```python
if message_text.endswith("?"):
```

Only messages ending exactly with `?` are counted.

So this counts:

```text
What is Python?
```

But this does not count:

```text
What is Python? thanks
```

13. Update the user’s question count

```python
question_database[user_id] = question_database.get(user_id, 0) + 1
current_count = question_database[user_id]
```

If the user is not in the dictionary yet, their count starts at `0`.

Then the app adds `1`.

14. Print a sorted tracker in the terminal

```python
sorted_database = sorted(question_database.items(), key=lambda item: item[1], reverse=True)
```

This sorts users by question count from highest to lowest.

Then it prints a small table in your terminal showing each user and their number of questions.

15. Trigger alert at 3 questions

```python
if current_count >= 3:
```

Once a user reaches 3 or more counted questions, the app sends an alert.

Because this says `>= 3`, it will alert again at 4, 5, 6, etc.

16. Send first admin message

```python
bot_client.chat_postMessage(
    channel=ADMIN_SLACK_ID,
    text=f"..."
)
```

This sends a private Slack message to the admin saying the user hit the threshold.

17. Search recent messages from that user

```python
rts_query = f"from:<@{user_id}>"
rts_response = user_client.search_messages(query=rts_query, count=5)
```

This tries to search Slack for the user’s last 5 messages.

The goal is to give the admin context about what the learner has been asking.

18. Build context summary

```python
context_summary = ""
if rts_response.get("ok"):
    matches = rts_response.get("messages", {}).get("matches", [])
    for idx, msg in enumerate(matches, 1):
        text = msg.get("text", "")
        context_summary += f"   {idx}. \"_{text}_\"\n"
```

If Slack search succeeds, the app loops through matching messages and builds a text summary.

If nothing is found, it uses:

```python
context_summary = "   _No prior searchable query history available._\n"
```

19. Send final detailed alert

```python
bot_client.chat_postMessage(channel=ADMIN_SLACK_ID, text=alert_payload)
```

This sends the full report to the admin, including:

- struggling learner ID
- total question count
- recent searched messages
- suggested next actions

20. Always respond to Slack

```python
return jsonify({"status": "ok"})
```

Slack expects your endpoint to respond quickly. This tells Slack the event was received.

21. Run the server

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

When you run:

```bash
python app.py
```

Flask starts a web server on port `8080`.

The app listens on all network interfaces because of:

```python
host="0.0.0.0"
```

In plain English: this app watches Slack messages, counts how many question-like messages each user sends, and privately alerts an admin when someone asks at least 3 questions.