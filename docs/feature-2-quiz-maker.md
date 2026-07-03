# Feature 2: Quiz Maker

## Purpose

Give the Instructor or Teaching Assistant a fast, low-stakes way to understand current student knowledge from lecture material.

This is not a formal test. It is a private comprehension check so students can answer honestly.

## MVP Behavior

1. Instructor or Teaching Assistant chats with the app and sends `quiz`.
2. App shows available lecture-note topics as a numbered list.
3. Instructor or Teaching Assistant picks a topic number.
4. App generates a quiz from saved lecture notes for that topic.
5. App shows the quiz draft to the Instructor or Teaching Assistant.
6. Instructor or Teaching Assistant approves the draft.
7. App sends the quiz by DM to all non-staff members at the same time.
8. Students answer by reacting to the quiz message.
9. Instructor or Teaching Assistant sends `quiz summary`.
10. App summarizes the reaction responses for the Instructor or Teaching Assistant in staff chat or DM.

## Slack Flow

```text
Instructor/Teaching Assistant sends "quiz"
  -> app lists saved lecture-note topics
  -> Instructor/Teaching Assistant picks a topic number
  -> app reads saved topic-note context
  -> app drafts quiz
  -> Instructor/Teaching Assistant approves
  -> app DMs all non-staff members
  -> students answer with reactions
  -> Instructor/Teaching Assistant sends "quiz summary"
  -> app summarizes responses for Instructor/Teaching Assistant
```

## Lecture Note Context

For the demo, use 2 topics from lecture notes already fed to the app through Feature 2A. See `docs/feature-2a-lecture-notes.md`.

The first version only needs notes around the topic the Instructor or Teaching Assistant has in mind. Do not try to model the whole course yet.

AI should draft, not auto-send. The Instructor or Teaching Assistant approves before students receive anything.

## Staff Recognition

For the demo, treat a Slack member as staff when their profile title is exactly `Instructor` or `Teaching Assistant`.

Staff can run `lecture note`, `quiz`, `approve`, and `regenerate`. Students are course-channel members whose title is not `Instructor` or `Teaching Assistant`.

## Conversation State

For the demo, the app only needs three pending states:

- `lecture_note`: waiting for structured `Topic:` and `Note:` input
- `quiz_topic_number`: waiting for the Instructor or Teaching Assistant to pick a topic number
- `quiz_approval`: waiting for `approve` or `regenerate`

Keep the state keyed by staff user ID. The demo controls the happy path, so invalid input only needs a short reminder of the expected reply.

## Topic Selection

When the Instructor or Teaching Assistant sends `quiz`, the app should first show the saved topics:

```text
Pick a topic for the quiz:

1. Docker basics
2. Python functions
```

The Instructor or Teaching Assistant replies with a number, such as `1`. After that, the app calls AI to generate the quiz from the saved notes for that topic.

## Draft Preview

After AI generates the quiz, the app sends the Instructor or Teaching Assistant a draft preview before students see anything:

```text
Quiz draft: Docker basics

Q1. What is the main purpose of a Docker image?
:one: To define a reusable app environment
:two: To store live container logs
:three: To replace all databases

Correct answer: :one:

Q2. What happens when you run a Docker container?
:one: Docker creates a running instance from an image
:two: Docker deletes the image
:three: Docker converts Python to JavaScript

Correct answer: :one:

Reply `approve` to send, or `regenerate` to make a new draft.
```

For the MVP, the draft should include:

- quiz topic
- 2-3 short multiple-choice questions
- reaction choices using `:one:`, `:two:`, and `:three:`
- correct answer for Instructor/Teaching Assistant review only
- `approve` and `regenerate` commands

Only the approved student version should be sent to students. The student version should not show the correct answers.

## Quiz Shape

Keep the first version small:

- 2 demo topics
- 2-3 short multiple-choice questions
- Reaction-based answers in Slack
- Private Slack DM delivery
- Send to all non-staff members at the same time
- No public scores
- Aggregate Instructor/Teaching Assistant summary

## Summary Output

When the Instructor or Teaching Assistant sends `quiz summary`, send a short summary:

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
- Full quiz builder UI

## Done Means

- Instructor or Teaching Assistant can ask the app for a quiz with `quiz`.
- App can list saved lecture-note topics.
- Instructor or Teaching Assistant can pick a topic by number.
- App can draft a quiz from saved lecture notes for the topic.
- Instructor or Teaching Assistant can approve before sending.
- Non-staff students receive the quiz privately in Slack.
- Students can answer with reactions.
- Instructor or Teaching Assistant can ask for results with `quiz summary`.
- Instructor or Teaching Assistant receives an aggregate understanding summary.
