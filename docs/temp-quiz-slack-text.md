# Temporary Slack Text Review

This is a review sheet for the current user-facing Slack text. Edit or annotate this file with the wording you want.

## Quiz Feature: Instructor / Teaching Assistant

### Non-staff tries a quiz command

```text
🔒 Only users with the Instructor or Teaching Assistant title can use quiz commands.
```

### Instructor sends `lecture note`

```text
📝 Please send the lecture note using this format:

Topic: <topic>
Note:
<note text>
```

### Instructor sends invalid lecture-note format

```text
Please use this format:

Topic: <topic>
Note:
<note text>
```

### Lecture note is saved

```text
✅ Saved lecture note for *<topic>*. Please send `quiz` when you are ready.
```

### Instructor sends `quiz`, but no topics exist

```text
No lecture-note topics are saved yet. Please send `lecture note` first. 📝
```

### Instructor sends `quiz`, and topics exist

```text
✨ Pick a topic to generate a quiz:

1. <topic one>
2. <topic two>
```

### Instructor replies with invalid topic number

```text
Please reply with the topic number.
```

```text
Please reply with one of the listed topic numbers.
```

### Quiz draft is already generating

```text
⏳ Generating the quiz draft...
```

### No lecture notes found for selected topic

```text
No lecture notes are saved for *<topic>* yet.
```

### Quiz draft sent to instructor

```text
🧪 Draft quiz for *<topic>*

Q1. <question text>
:one: <choice one>
:two: <choice two>
:three: <choice three>

Correct answer: :one:

Q2. <question text>
:one: <choice one>
:two: <choice two>
:three: <choice three>

Correct answer: :two:

Reply `approve` to send this quiz, or `regenerate` to make a new draft.
```

### Instructor replies with other text while draft is waiting

```text
Please reply `approve` or `regenerate`.
```

### Instructor sends `regenerate`, but no draft exists

```text
No quiz draft is ready to regenerate. Please send `quiz` first.
```

### Instructor sends `approve`, but no draft exists

```text
No quiz draft is ready to approve. Please send `quiz` first.
```

### Quiz is already being sent

```text
📤 Sending quiz...
```

### Quiz sent successfully

```text
✅ Sent the *<topic>* quiz to <student count> student(s).
```

### Instructor sends `quiz summary`, but no active quiz exists

```text
No active quiz found yet.
```

### Quiz summary sent to instructor

```text
📊 Quiz summary: *<topic>*

✅ Overall accuracy: <accuracy percent>
👥 Responses: <responded count>/<student count> students
<teaching recommendation>

────────────────────
Question breakdown:

Q1. <question text>
Correct: :one: <choice text>
:one: 🟩🟩🟩 <count>
:two: 🟦 <count>
:three: ⬜ 0

Q2. <question text>
Correct: :two: <choice text>
:one: 🟩 <count>
:two: 🟦🟦🟦 <count>
:three: ⬜ 0

Quiz ID: <quiz id>
```

If there are no student responses yet, omit the divider and question breakdown.

## Quiz Feature: Student DMs

### Quiz intro DM

```text
🧠 *QUIZ: <topic>*

Please answer <question count> questions by reacting to each question message with :one:, :two:, or :three:.
```

### One DM per question

```text
*_Question 1/3: <question text>_*

:one: <choice one>
:two: <choice two>
:three: <choice three>

────────────────────
```

```text
*_Question 2/3: <question text>_*

:one: <choice one>
:two: <choice two>
:three: <choice three>

────────────────────
```

```text
*_Question 3/3: <question text>_*

:one: <choice one>
:two: <choice two>
:three: <choice three>

────────────────────
```

## Syllabus / Canvas Feature: Instructor / Teaching Assistant

These are not part of the quiz DM flow, but they are also current instructor-facing bot messages.

### Non-staff tries to upload syllabus

```text
Only users with the Instructor or Teaching Assistant title can upload a syllabus.
```

### Syllabus upload is not a PDF

```text
Please upload a PDF syllabus.
```

### Canvas already exists

```text
A course canvas already exists: `<canvas id>`.
Delete the canvas and clear `data/course_state.json` before uploading a new syllabus.
```

### Syllabus canvas creation fails

```text
Could not create the syllabus canvas: <error>
```

### Syllabus canvas created successfully

```text
Created syllabus canvas `<canvas id>` for *<course name>*.
Instructor: <instructor name>
```
