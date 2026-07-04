# Feature 2A: Lecture Note Prep

## Purpose

Give the app lecture-note context so Feature 2 can generate a quiz around a topic the Instructor or Teaching Assistant has in mind.

This is prep for quiz generation, not a full course-content system.

## MVP Behavior

1. Instructor or Teaching Assistant DMs the bot with `lecture note`.
2. Bot asks for the topic and lecture note text.
3. Instructor or Teaching Assistant sends or pastes the topic and note.
4. Bot saves the note with the topic.
5. Bot confirms the note is ready for quiz generation.
6. Feature 2 uses the saved topic notes when someone sends `quiz`.

## Slack Flow

```text
Instructor/Teaching Assistant sends "lecture note"
  -> bot asks for topic and note text
  -> Instructor/Teaching Assistant sends topic and note
  -> app saves topic note
  -> bot confirms note is stored
  -> quiz maker can use topic notes
```

## Lecture Note Input

Use a structured message for the demo:

```text
Topic: Docker basics
Note:
Containers package an app with its dependencies.
Images are reusable templates.
Containers are running instances of images.
```

The bot should save the text after `Topic:` as the topic and the text after `Note:` as the lecture note.

## Stored Note Shape

Keep the first version inspectable:

- note text
- topic
- sender user ID
- Slack DM or channel ID
- optional topic labels from AI

Store notes in the same lightweight JSON style as the rest of the hackathon data.

## Not In Scope Yet

- File upload parsing
- PDF or slide extraction
- Full course search
- Multi-course note libraries
- Automatic note cleanup

## Done Means

- Instructor or Teaching Assistant can DM `lecture note`.
- Bot can collect and store pasted lecture-note text.
- Stored notes include a topic.
- Quiz maker can read topic notes as input context.
