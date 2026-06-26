# Feature 3: FAQ Bot

## Purpose

Turn repeated Slack questions into a draft FAQ that the instructor can review and share.

The FAQ should help students find answers without asking the same question again.

## MVP Behavior

1. Instructor provides syllabus topics or lesson notes.
2. Instructor chooses a Slack channel and time window.
3. Bot fetches recent channel messages.
4. AI finds repeated questions and useful answers.
5. AI drafts FAQ entries grouped by syllabus topic.
6. Instructor reviews before publishing.

## Flow

```text
Syllabus/topics
  + Slack channel messages
  -> extract repeated questions
  -> group by topic
  -> draft FAQ
  -> instructor review
  -> publish to Slack or save as Markdown
```

## Why Use Syllabus

The syllabus gives the FAQ structure.

Example topics:

- Docker basics
- Slack API
- Python environment
- Deployment

The bot should use these topics to organize FAQ sections instead of inventing unrelated categories.

## Output Shape

```markdown
## Docker basics

**Q: Why does Docker Compose fail to start my app?**
A: Check that `.env` exists, ports are free, and rebuild with `docker compose up --build`.

Source: 4 similar Slack questions
```

## AI Role

AI is useful here because the feature is mostly summarization.

AI should:

- detect repeated questions
- merge similar wording
- draft concise answers
- map questions to syllabus topics

AI should not auto-publish without instructor review.

## Not In Scope Yet

- Perfect answer verification
- Full knowledge base search
- Auto-publishing without review
- Long-form documentation generation
- Cross-course FAQ management

## Done Means

- Instructor can provide syllabus/topics.
- Bot can scan a selected Slack channel window.
- Bot drafts FAQ entries grouped by topic.
- Instructor can review before sharing.
