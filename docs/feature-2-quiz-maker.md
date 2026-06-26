# Feature 2: Quick Quiz Maker

## Purpose

Give the instructor a fast, low-stakes way to understand current student knowledge.

This is not a formal test. It is a private comprehension check so students can answer honestly.

## MVP Behavior

1. Instructor opens a small quiz builder UI.
2. Instructor pastes a syllabus, lesson notes, or topic list.
3. Instructor chooses AI-suggested quiz or manual quiz creation.
4. Instructor reviews and edits the quiz.
5. Bot sends the quiz privately to students in Slack.
6. Bot summarizes responses for the instructor.

## UI Flow

```text
Syllabus/topic input
  -> topic selection
  -> AI-generate or manual create
  -> editable quiz draft
  -> choose recipients
  -> send private Slack quiz
  -> instructor summary
```

## Quiz Modes

- **AI-suggested:** AI drafts questions from syllabus/topics.
- **Manual:** instructor writes questions from scratch.

AI should draft, not auto-send. The instructor approves before students receive anything.

## Quiz Shape

Keep the first version small:

- 3-5 questions
- Multiple choice or short answer
- Private Slack DM delivery
- No public scores
- Aggregate instructor summary

## Summary Output

Send the instructor a short summary:

```text
Quiz summary: Docker basics

Responses: 12/18
Strong: image vs container basics
Needs review: volumes and compose ports
Suggested next step: review volume mounts for 5 minutes
```

## Not In Scope Yet

- Formal grading
- Public leaderboards
- Full LMS integration
- Long quizzes
- Complex student profiles

## Done Means

- Instructor can draft or generate a quiz.
- Instructor can review before sending.
- Students receive the quiz privately in Slack.
- Instructor receives an aggregate understanding summary.
