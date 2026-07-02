# Feature 3: Course Context and FAQ Maker

## Purpose

Turn syllabus material into reusable course context, then use that context plus repeated Slack questions to draft a reviewed FAQ.

The FAQ should help students find answers without asking the same question again. The syllabus summary should also give the app a shared course map for other features.

## Split

### 3A: Student Course Fact Sheet

Turns a syllabus PDF into a quick reference sheet for students.

Output:

- course name
- instructor
- course schedule and location
- TA and instructor contact
- TA and instructor office hours
- `Course quick fact + FAQ` canvas

This should be saved so the FAQ maker can reuse the active canvas later.

Testing MVP:

1. Admin/professor DMs the bot a syllabus PDF.
2. Bot extracts the essential student reference info.
3. Bot creates a quick fact sheet canvas in the course channel.
4. Bot saves the active canvas state for the next test upload.

Current testing issue:

- The app currently uses `data/course_state.json` to know whether an active course canvas already exists.
- Slack does not currently give this app a simple implemented path to find an existing canvas by the title `Course quick fact + FAQ`.
- If `data/course_state.json` is deleted during testing, the app can lose track of the existing canvas and may create a duplicate canvas on the next syllabus upload.
- For now, reset testing by deleting the Slack canvas manually and clearing `data/course_state.json` together.

### 3B: FAQ Maker

Uses the saved course map and Slack channel questions to draft a student-facing FAQ.

Output:

- repeated question clusters
- concise answers
- syllabus/topic grouping
- draft Slack canvas or Markdown FAQ

The instructor reviews the draft before it is shared.

## MVP Behavior

1. Instructor sends or uploads a syllabus.
2. Bot extracts a quick fact sheet for students.
3. Instructor chooses a Slack channel and time window.
4. Bot fetches recent channel messages.
5. AI finds repeated questions and useful answers.
6. AI drafts FAQ entries grouped by syllabus topic.
7. Instructor reviews before publishing to a Slack canvas or Markdown.

## Flow

```text
Syllabus PDF
  -> extract course facts
  -> save active canvas state
  + selected Slack channel messages
  -> extract repeated questions
  -> group by topic
  -> draft FAQ
  -> instructor review
  -> create Slack canvas or save as Markdown
```

## Why Split It

The syllabus compiler is shared course context.

The FAQ maker is one use of that context.

Example topics:

- Docker basics
- Slack API
- Python environment
- Deployment

The bot should use these topics to organize FAQ sections instead of inventing unrelated categories.

## Quick Fact Sheet Shape

```markdown
# Course quick fact + FAQ

## Course

Intro to Data Engineering

## Instructor

Dr. Ada Lovelace

## Schedule

- Mondays and Wednesdays 10:00-11:30 AM

## Location

Room 204

## Instructor Contact

ada@example.edu

## Instructor Office Hours

Tuesdays 2:00-3:00 PM

## TA Contact

- Grace Hopper: grace@example.edu

## TA Office Hours

- Grace Hopper: Fridays 1:00-2:00 PM
```

## FAQ Output Shape

```markdown
# Course FAQ

## Docker basics

**Q: Why does Docker Compose fail to start my app?**
A: Check that `.env` exists, ports are free, and rebuild with `docker compose up --build`.

Source: 4 similar Slack questions
```

## AI Role

AI is useful here because the feature is mostly summarization.

AI should:

- extract essential syllabus facts
- detect repeated questions
- merge similar wording
- draft concise answers
- map questions to syllabus topics

AI may create the starter syllabus canvas for testing. AI should not auto-publish the final repeated-question FAQ without instructor review.

## Not In Scope Yet

- Perfect answer verification
- Full knowledge base search
- Auto-publishing without review
- Long-form documentation generation
- Cross-course FAQ management
- Replacing the course LMS

## Done Means

- Instructor can provide a syllabus or lesson notes.
- Bot can create a quick fact sheet canvas from the syllabus.
- Bot can scan a selected Slack channel window.
- Bot drafts FAQ entries grouped by topic.
- Instructor can review before sharing the final repeated-question FAQ.
