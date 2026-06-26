# System Design

## Implementation Goal

Build one Flask app that handles Slack events, instructor UI pages, AI calls, and lightweight storage.

Keep it a modular monolith for the hackathon. Do not split into microservices.

## Proposed Structure

```text
app.py
config.py

events/
  slack_events.py
  app_events.py

features/
  study_groups.py
  quiz_maker.py
  faq_bot.py

services/
  slack_service.py
  ai_service.py
  storage_service.py

templates/
  quiz_builder.html
  faq_builder.html
```

## Runtime Flows

### Slack Event Flow

```text
Slack event
  -> app.py /slack/events
  -> events/slack_events.py parses payload
  -> feature handlers receive clean app event
  -> services send Slack messages or store state
```

### Instructor UI Flow

```text
Instructor page
  -> Flask route
  -> feature handler
  -> AI service if needed
  -> instructor reviews draft
  -> Slack service sends quiz/FAQ/group update
```

## Shared Services

- `slack_service.py`: post messages, open DMs, create groups, invite students, fetch channel messages.
- `ai_service.py`: generate quiz drafts, summarize quiz answers, draft FAQ entries.
- `storage_service.py`: store question counts, topic groups, quiz drafts, responses, syllabus topics, and FAQ drafts.

## Data Model

Start in memory or SQLite.

Core records:

- `StudentQuestion`: user, channel, text, topic, timestamp
- `StudyGroup`: topic, date, students, Slack group/channel ID, status
- `Quiz`: topic, questions, recipients, responses, summary
- `FAQDraft`: topics, source messages, question-answer pairs

## Feature Boundaries

- Study groups can run without AI by using the topic dictionary.
- Quiz maker uses AI for draft questions and response summaries.
- FAQ bot uses AI for summarization and syllabus-based grouping.
- All AI output must be reviewed before broad sharing.

## Build Order

1. Refactor current `app.py` into event parsing, services, and feature handlers.
2. Implement Feature 1 using question counts and topic dictionary.
3. Add instructor UI shell for quiz and FAQ workflows.
4. Add AI service for quiz drafts, quiz summaries, and FAQ drafts.
5. Add lightweight persistence if in-memory state becomes too limiting.

## Failure Rule

Slack event handling should always return quickly. If one feature fails, log the error and let the other features continue.
