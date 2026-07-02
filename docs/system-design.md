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
  syllabus_compiler.py
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
- `ai_service.py`: summarize syllabus material, generate quiz drafts, summarize quiz answers, draft FAQ entries.
- `storage_service.py`: store question counts, topic groups, course maps, quiz drafts, responses, and FAQ drafts.

## Data Model

Start with inspectable JSON files for course maps and drafts. Move to SQLite only if the data model gets harder to manage.

Core records:

- `StudentQuestion`: user, channel, text, topic, timestamp
- `CourseMap`: channel, syllabus source, topics, modules, learning objectives
- `StudyGroup`: topic, date, students, Slack group/channel ID, status
- `Quiz`: topic, questions, recipients, responses, summary
- `FAQDraft`: course map, source messages, question-answer pairs, review status

## Feature Boundaries

- Study groups can run without AI by using the topic dictionary.
- Quiz maker uses AI for draft questions and response summaries.
- Syllabus compiler uses AI to create reusable course context.
- FAQ maker uses AI for repeated-question clustering and syllabus-based grouping.
- All AI output must be reviewed before broad sharing.

## Build Order

1. Refactor current `app.py` into event parsing, services, and feature handlers.
2. Implement Feature 1 using question counts and topic dictionary.
3. Add syllabus compiler and lightweight course-map storage.
4. Add instructor UI shell for quiz and FAQ workflows.
5. Add AI service for syllabus summaries, quiz drafts, quiz summaries, and FAQ drafts.

## Failure Rule

Slack event handling should always return quickly. If one feature fails, log the error and let the other features continue.
