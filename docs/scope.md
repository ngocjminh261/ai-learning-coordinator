# Hackathon Scope

## Goal

Build a Slack-based AI Learning Coordinator demo that helps teachers spot confusion and respond faster.

## Demo Flow

1. Students ask questions in Slack.
2. The app detects confusion signals.
3. The app sends a useful teacher/coordinator summary.
4. The teacher reviews an FAQ, quiz insight, or study-group suggestion.

## MVP Features

- **Study groups:** detect lagging students and suggest a small group. See `docs/feature-1-study-groups.md`.
- **Quiz maker:** create a private low-stakes quiz and summarize understanding. See `docs/feature-2-quiz-maker.md`.
- **FAQ bot:** draft syllabus-organized FAQ pairs from repeated Slack questions. See `docs/feature-3-faq-bot.md`.

## Architecture Boundary

Use one Flask app with modular pieces. See `docs/system-design.md`.

- Slack event receiver
- Event parser
- Feature handlers
- Slack service
- AI/model service
- Storage service

Do not split into microservices for the hackathon.

## Non-Goals

- Production deployment
- Multi-workspace Slack support
- Analytics dashboard
- Fully automated grading
- Perfect student knowledge modeling

## Done Means

- App runs locally.
- Slack reaches `/slack/events` through ngrok.
- One feature works end to end in Slack.
- Other features have placeholders or next steps.
- One feature failing does not stop event handling.

## Scope Rule

If a new idea does not improve the demo flow, move it to later.
