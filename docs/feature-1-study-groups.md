# Feature 1: Study Group Bot

## Purpose

Help the teacher spot lagging students and create a small focus group before they fall further behind.

The focus group is an instant, topic-specific help space. Students can ask more direct follow-up, admin, or ad hoc questions there without flooding the main channel.

The main channel should still be the default public learning space. The focus group is temporary support, not a replacement.

## MVP Behavior

1. Student messages arrive in Slack.
2. The app keeps only question-like messages.
3. The app tags each question with a topic from a small dictionary.
4. The app counts question volume by student and topic.
5. When students cross the threshold, the app creates or updates a study group.

## Bot Flow

```text
Slack message
  -> ignore bot messages
  -> keep message only if it ends with ?
  -> classify topic with topic dictionary
  -> increment student/topic question count
  -> check threshold
  -> create new group, add to existing group, or send individual alert
```

## First Trigger

Use the current app behavior:

- Count messages ending in `?`.
- Trigger when a student reaches `3` questions.
- Classify each question using the topic dictionary.
- Search recent Slack messages from that student for extra context.

This is simple, visible, and demo-friendly.

## When To Create A Group

Do not create a group just because one student asks questions.

| Situation | Action |
| --- | --- |
| 1 student hits the threshold | Send individual help alert |
| 2+ students hit the threshold for the same topic | Create a study group |
| Student matches an existing topic group | Add them to that group |
| No clear match | Keep tracking; do not suggest a group yet |

## Topic Dictionary

Start with a small hardcoded dictionary:

```python
TOPIC_KEYWORDS = {
    "docker": ["docker", "container", "compose", "image", "volume"],
    "slack api": ["slack", "bot", "token", "event", "scope"],
    "python env": ["python", "pip", "uv", "venv", "import"],
    "api basics": ["api", "endpoint", "request", "response", "json"],
}
```

If a question contains a keyword, assign the matching topic. If no topic matches, store it as `unknown` and do not use it for group creation yet.

## Grouping Logic

For the hackathon MVP, keep grouping rule-based and mostly non-AI:

- Same dictionary topic.
- Same channel when possible.
- Students who crossed the question threshold close together.

Content understanding with AI can come later. Without AI, the app uses `?`, channel, timestamp, and dictionary topics.

With AI, we could group by meaning instead of exact keywords. Example: "container won't start" and "Docker compose fails" could be treated as the same topic.

## Suggested Output

Create or update a Slack study group, then notify the coordinator:

```text
Study group created

Topic: Docker basics
Students: <@U123>, <@U456>, <@U789>
Reason: Each student asked multiple recent questions about Docker setup.
Purpose: Fast follow-up and ad hoc help for today's Docker confusion.
```

## Data Needed

- Student user ID
- Channel ID
- Message text
- Message timestamp
- Question count
- Recent matching messages
- Study group ID or channel ID after creation

In the MVP, this can stay in memory. Later, move it to SQLite or another small store.

## Group State

Track simple group records in memory:

```python
{
    "topic": "docker",
    "channel_id": "C123",
    "student_ids": ["U123", "U456"],
    "group_channel_id": "G123",
    "status": "active",
    "created_at": "...",
    "expires_at": "...",
}
```

Before creating a group, check whether a group with the same topic already exists. If it does, add the new student instead of creating a duplicate group.

For the MVP, a group is active for one day. Tomorrow's students should get a new topic group, even if yesterday had the same topic.

## AI Requirement

AI is not required for the first version.

- No AI: use question marks, counts, channels, timestamps, and simple keywords.
- With AI: classify question topics, detect similar confusion, and write better teacher summaries.

## Not In Scope Yet

- Calendar scheduling
- Mentor availability matching
- Long-term student performance history
- Perfect topic classification

## Done Means

- One student can trigger the threshold.
- The app only creates a group when there are at least two matching students.
- The coordinator receives a clear study-group update in Slack.
- If grouping fails, the original threshold alert still sends.
