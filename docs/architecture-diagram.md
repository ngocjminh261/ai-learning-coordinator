# CoursePilot Architecture

```mermaid
flowchart TD
    students[Students in Slack]
    staff[Instructors and TAs in Slack]
    slack[Slack workspace<br/>channels, DMs, reactions, canvases]

    students --> slack
    staff --> slack

    slack -->|message.channels, message.im, reaction_added| events[Flask backend<br/>/slack/events]
    staff -->|Google OAuth setup| oauth[Flask backend<br/>/google/oauth/start<br/>/google/oauth/callback]

    events --> router[Slack event router]
    events --> search[Background Slack search polling]

    router --> study[StudyGroupOrchestrator<br/>detect confusion and create lounges]
    router --> quiz[QuizMaker<br/>lecture notes, quiz drafts, approvals, summaries]
    router --> syllabus[SyllabusCompiler<br/>syllabus quick facts and FAQ canvas]

    search --> study

    study --> slack_service[SlackService]
    quiz --> slack_service
    syllabus --> slack_service

    quiz --> drive[Google Drive MCP service<br/>OAuth, recent files, content import]
    oauth --> drive

    quiz --> ai[AI service<br/>Gemini or Ollama]
    syllabus --> ai

    study --> storage[In-memory + JSON storage<br/>question counts, course state, notes, quizzes]
    quiz --> storage
    syllabus --> storage
    drive --> storage

    slack_service -->|DMs, channel messages, study lounges, reactions, canvases| slack
    drive -->|Drive API fallback| google[Google Drive]
    ai --> gemini[Gemini]
    ai --> ollama[Ollama]
```

## Data Flow

1. Students and staff interact with the app through Slack messages, DMs, reactions, and canvases.
2. Slack sends events to the Flask `/slack/events` endpoint.
3. The event router sends each event to the right feature module.
4. Study-group logic tracks repeated student confusion and creates Slack study lounges.
5. Quiz logic imports lecture notes, drafts quizzes with AI, sends approved quizzes by DM, and summarizes reactions.
6. Syllabus logic extracts course facts and publishes a Slack canvas.
7. Google Drive MCP brings instructor lecture notes into the quiz workflow.
8. Lightweight storage keeps demo state inspectable during the hackathon.
