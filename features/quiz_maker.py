from features.syllabus_compiler import STAFF_TITLES, normalize_profile_title


REACTION_LABELS = {
    "one": ":one:",
    "two": ":two:",
    "three": ":three:",
}

BAR_BLOCKS = {
    "one": "🟩",
    "two": "🟦",
    "three": "🟨",
}

SUMMARY_BAR_MAX_BLOCKS = 8


class QuizMaker:
    def __init__(self, storage, slack_service, ai_service, course_channel_id, drive_service=None):
        self.storage = storage
        self.slack_service = slack_service
        self.ai_service = ai_service
        self.course_channel_id = course_channel_id
        self.drive_service = drive_service

    def handle_message_event(self, event):
        if event.get("type") != "message" or event.get("bot_id"):
            return {"handled": False}

        text = event.get("text", "").strip()
        user_id = event.get("user")
        channel_id = event.get("channel")
        if not text or not user_id:
            return {"handled": False}

        lowered = text.casefold()
        if lowered in {"lecture note", "quiz", "approve", "regenerate", "quiz summary"}:
            if not self.is_staff_user(user_id):
                self.slack_service.post_message(
                    channel_id,
                    "🔒 Only users with the Instructor or Teaching Assistant title can use quiz commands.",
                )
                return {"handled": True, "status": "rejected_non_staff"}

        if lowered == "lecture note":
            self.storage.set_pending_action(user_id, "lecture_note_source")
            self.slack_service.post_message(
                channel_id,
                format_lecture_note_source_prompt(),
            )
            return {"handled": True, "status": "waiting_for_lecture_note_source"}

        if lowered == "quiz":
            return self.start_quiz_topic_selection(user_id, channel_id)

        if lowered == "approve":
            return self.approve_quiz(user_id, channel_id)

        if lowered == "regenerate":
            return self.regenerate_quiz(user_id, channel_id)

        if lowered == "quiz summary":
            return self.send_quiz_summary(
                user_id,
                channel_id,
                event.get("ts") or event.get("event_ts"),
            )

        pending_action = self.storage.get_pending_action(user_id)
        if not pending_action:
            return {"handled": False}

        if pending_action.get("state") == "lecture_note":
            return self.save_lecture_note_from_message(user_id, channel_id, text)

        if pending_action.get("state") == "lecture_note_source":
            return self.handle_lecture_note_source_choice(user_id, channel_id, text)

        if pending_action.get("state") == "drive_lecture_note_file_number":
            return self.import_drive_lecture_note(
                user_id,
                channel_id,
                text,
                pending_action,
                event.get("ts") or event.get("event_ts"),
            )

        if pending_action.get("state") == "quiz_topic_number":
            return self.generate_quiz_from_topic_number(user_id, channel_id, text, pending_action)

        if pending_action.get("state") == "quiz_generating":
            return {"handled": True, "status": "quiz_generation_in_progress"}

        if pending_action.get("state") == "quiz_approval":
            self.slack_service.post_message(channel_id, "Please reply `approve` or `regenerate`.")
            return {"handled": True, "status": "unexpected_quiz_approval_reply"}

        return {"handled": False}

    def handle_lecture_note_source_choice(self, user_id, channel_id, text):
        choice = text.strip()
        if choice == "1":
            self.storage.set_pending_action(user_id, "lecture_note")
            self.slack_service.post_message(
                channel_id,
                "📝 Please send the lecture note using this format:\n\nTopic: <topic>\nNote:\n<note text>",
            )
            return {"handled": True, "status": "waiting_for_lecture_note"}

        if choice == "2":
            if not self.drive_service:
                self.slack_service.post_message(
                    channel_id,
                    "Google Drive import is not configured yet.",
                )
                return {"handled": True, "status": "drive_import_not_configured"}

            try:
                files = self.drive_service.list_recent_files(page_size=5)
            except Exception as exc:
                self.slack_service.post_message(
                    channel_id,
                    f"Could not list Google Drive files through MCP: {exc}",
                )
                return {"handled": True, "status": "drive_file_list_failed"}

            if not files:
                self.slack_service.post_message(channel_id, "No recent Google Drive files found.")
                return {"handled": True, "status": "no_drive_files"}

            self.storage.set_pending_action(
                user_id,
                "drive_lecture_note_file_number",
                drive_files=files,
            )
            self.slack_service.post_message(channel_id, format_drive_file_list(files))
            return {"handled": True, "status": "waiting_for_drive_file_number"}

        self.slack_service.post_message(channel_id, "Please reply `1` or `2`.")
        return {"handled": True, "status": "invalid_lecture_note_source"}

    def handle_reaction_event(self, event):
        if event.get("type") != "reaction_added":
            return {"handled": False}

        reaction = event.get("reaction")
        if reaction not in REACTION_LABELS:
            return {"handled": False}

        item = event.get("item", {})
        channel_id = item.get("channel")
        message_ts = item.get("ts")
        student_id = event.get("user")
        if not channel_id or not message_ts or not student_id:
            return {"handled": False}

        quiz_id, quiz, question = self.storage.find_quiz_question_by_message(
            channel_id,
            message_ts,
        )
        if not quiz:
            return {"handled": False}

        self.storage.record_quiz_response(
            quiz_id,
            question["id"],
            student_id,
            reaction,
        )
        return {"handled": True, "status": "recorded_quiz_response"}

    def start_quiz_topic_selection(self, user_id, channel_id):
        topics = self.storage.get_lecture_note_topics()
        if not topics:
            self.slack_service.post_message(
                channel_id,
                "No lecture-note topics are saved yet. Please send `lecture note` first. 📝",
            )
            return {"handled": True, "status": "no_topics"}

        self.storage.set_pending_action(user_id, "quiz_topic_number", topics=topics)
        self.slack_service.post_message(channel_id, format_topic_list(topics))
        return {"handled": True, "status": "waiting_for_quiz_topic_number"}

    def save_lecture_note_from_message(self, user_id, channel_id, text):
        parsed_note = parse_structured_lecture_note(text)
        if not parsed_note:
            self.slack_service.post_message(
                channel_id,
                "Please use this format:\n\nTopic: <topic>\nNote:\n<note text>",
            )
            return {"handled": True, "status": "invalid_lecture_note"}

        note = self.storage.save_lecture_note(
            topic=parsed_note["topic"],
            note_text=parsed_note["text"],
            sender=user_id,
            channel=channel_id,
        )
        self.storage.clear_pending_action(user_id)
        self.slack_service.post_message(
            channel_id,
            f"✅ Saved lecture note for *{note['topic']}*. Please send `quiz` when you are ready.",
        )
        return {"handled": True, "status": "saved_lecture_note"}

    def import_drive_lecture_note(self, user_id, channel_id, text, pending_action, event_ts=None):
        try:
            selected_index = int(text.strip()) - 1
        except ValueError:
            self.slack_service.post_message(channel_id, "Please reply with the Drive file number.")
            return {"handled": True, "status": "invalid_drive_file_number"}

        files = pending_action.get("drive_files", [])
        if selected_index < 0 or selected_index >= len(files):
            self.slack_service.post_message(channel_id, "Please reply with one of the listed file numbers.")
            return {"handled": True, "status": "invalid_drive_file_number"}

        selected_file = files[selected_index]
        event_key = build_drive_import_event_key(user_id, channel_id, selected_file, event_ts)
        if event_key and not self.storage.claim_processed_event(event_key):
            return {"handled": True, "status": "duplicate_drive_import"}

        try:
            imported_text = self.drive_service.read_file_content(selected_file["id"])
        except Exception as exc:
            self.slack_service.post_message(
                channel_id,
                f"Could not import that Google Drive file through MCP: {exc}",
            )
            return {"handled": True, "status": "drive_file_import_failed"}

        if not imported_text:
            self.slack_service.post_message(channel_id, "That Google Drive file did not include readable text.")
            return {"handled": True, "status": "empty_drive_file"}

        parsed_note = parse_structured_lecture_note(imported_text)
        if parsed_note:
            topic = parsed_note["topic"]
            note_text = parsed_note["text"]
        else:
            topic = derive_topic_from_drive_file(selected_file)
            note_text = imported_text

        note = self.storage.save_lecture_note(
            topic=topic,
            note_text=note_text,
            sender=user_id,
            channel=channel_id,
            source={
                "type": getattr(self.drive_service, "last_read_source", None) or "google_drive_mcp",
                "file_id": selected_file["id"],
                "file_name": selected_file["title"],
                "view_url": selected_file.get("viewUrl"),
            },
        )
        self.storage.clear_pending_action(user_id)
        self.slack_service.post_message(
            channel_id,
            f"✅ Imported Google Drive file *{selected_file['title']}* as lecture notes for *{note['topic']}*.",
        )
        return {"handled": True, "status": "imported_drive_lecture_note"}

    def generate_quiz_from_topic_number(self, user_id, channel_id, text, pending_action):
        try:
            selected_index = int(text.strip()) - 1
        except ValueError:
            self.slack_service.post_message(channel_id, "Please reply with the topic number.")
            return {"handled": True, "status": "invalid_topic_number"}

        topics = pending_action.get("topics", [])
        if selected_index < 0 or selected_index >= len(topics):
            self.slack_service.post_message(channel_id, "Please reply with one of the listed topic numbers.")
            return {"handled": True, "status": "invalid_topic_number"}

        topic = topics[selected_index]
        self.storage.set_pending_action(user_id, "quiz_generating", topic=topic)
        return self.generate_and_send_draft(user_id, channel_id, topic)

    def regenerate_quiz(self, user_id, channel_id):
        pending_action = self.storage.get_pending_action(user_id)
        draft = self.storage.get_quiz_draft(user_id)
        topic = None
        if pending_action and pending_action.get("state") == "quiz_approval":
            topic = pending_action.get("topic")
        if not topic and draft:
            topic = draft.get("topic")
        if not topic:
            self.slack_service.post_message(channel_id, "No quiz draft is ready to regenerate. Please send `quiz` first.")
            return {"handled": True, "status": "no_draft_to_regenerate"}

        return self.generate_and_send_draft(user_id, channel_id, topic)

    def generate_and_send_draft(self, user_id, channel_id, topic):
        notes = self.storage.get_notes_for_topic(topic)
        if not notes:
            self.slack_service.post_message(channel_id, f"No lecture notes are saved for *{topic}* yet.")
            return {"handled": True, "status": "no_notes_for_topic"}

        self.slack_service.post_message(channel_id, "⏳ Generating the quiz draft...")
        draft = self.ai_service.generate_quiz_draft(topic, notes)
        self.storage.save_quiz_draft(user_id, draft)
        self.storage.set_pending_action(user_id, "quiz_approval", topic=topic)
        self.slack_service.post_message(channel_id, format_quiz_draft(draft))
        return {"handled": True, "status": "sent_quiz_draft"}

    def approve_quiz(self, user_id, channel_id):
        draft = self.storage.pop_quiz_draft(user_id)
        if not draft:
            pending_action = self.storage.get_pending_action(user_id)
            if pending_action and pending_action.get("state") == "quiz_sending":
                return {"handled": True, "status": "quiz_send_in_progress"}

            self.slack_service.post_message(channel_id, "No quiz draft is ready to approve. Please send `quiz` first.")
            return {"handled": True, "status": "no_draft_to_approve"}

        self.storage.set_pending_action(user_id, "quiz_sending", topic=draft["topic"])
        self.slack_service.post_message(channel_id, "📤 Sending quiz...")
        recipients = self.get_student_recipients()
        sent_questions = []
        for recipient in recipients:
            self.slack_service.post_dm(
                recipient,
                format_student_quiz_intro(draft["topic"], len(draft["questions"])),
            )
            for question_index, question in enumerate(draft["questions"], start=1):
                response = self.slack_service.post_dm(
                    recipient,
                    format_student_question(question, question_index, len(draft["questions"])),
                )
                sent_questions.append(
                    {
                        "id": question["id"],
                        "recipient": recipient,
                        "channel": response.get("channel"),
                        "ts": response.get("ts"),
                    }
                )

        quiz_id = f"quiz-{user_id}-{len(self.storage.get_active_quizzes()) + 1}"
        self.storage.save_active_quiz(
            quiz_id,
            {
                "topic": draft["topic"],
                "questions": draft["questions"],
                "recipients": recipients,
                "sent_questions": sent_questions,
                "responses": {},
                "owner": user_id,
            },
        )
        self.storage.clear_pending_action(user_id)
        self.slack_service.post_message(
            channel_id,
            f"✅ Sent the *{draft['topic']}* quiz to {len(recipients)} student(s).",
        )
        return {"handled": True, "status": "sent_quiz", "quiz_id": quiz_id}

    def send_quiz_summary(self, user_id, channel_id, event_ts=None):
        if event_ts:
            event_key = f"quiz-summary:{user_id}:{event_ts}"
            if not self.storage.claim_processed_event(event_key):
                return {"handled": True, "status": "duplicate_quiz_summary"}

        quiz_id, quiz = self.storage.get_current_quiz_for_owner(user_id)
        if not quiz:
            self.slack_service.post_message(channel_id, "No active quiz found yet.")
            return {"handled": True, "status": "no_active_quiz"}

        self.refresh_quiz_responses_from_slack(quiz_id, quiz)
        _, quiz = self.storage.get_current_quiz_for_owner(user_id)
        self.slack_service.post_message(channel_id, format_quiz_summary(quiz_id, quiz))
        return {"handled": True, "status": "sent_quiz_summary"}

    def refresh_quiz_responses_from_slack(self, quiz_id, quiz):
        refreshed_responses = {
            student_id: dict(student_responses)
            for student_id, student_responses in quiz.get("responses", {}).items()
        }
        valid_reactions = set(REACTION_LABELS)
        for sent_question in quiz.get("sent_questions", []):
            channel_id = sent_question.get("channel")
            message_ts = sent_question.get("ts")
            question_id = sent_question.get("id")
            if not channel_id or not message_ts or not question_id:
                continue

            try:
                reactions = self.slack_service.get_message_reactions(channel_id, message_ts)
            except Exception as exc:
                print(f"Could not fetch quiz reactions for {channel_id}/{message_ts}: {exc}")
                continue

            for reaction in reactions:
                reaction_name = reaction.get("name")
                if reaction_name not in valid_reactions:
                    continue
                for reacting_user in reaction.get("users", []):
                    student_responses = refreshed_responses.setdefault(reacting_user, {})
                    student_responses[question_id] = reaction_name

        self.storage.replace_quiz_responses(quiz_id, refreshed_responses)

    def get_student_recipients(self):
        recipients = []
        for user_id in self.slack_service.list_channel_members(self.course_channel_id):
            if self.slack_service.is_bot_user(user_id):
                continue
            if self.is_staff_user(user_id):
                continue
            recipients.append(user_id)
        return recipients

    def is_staff_user(self, user_id):
        try:
            title = self.slack_service.get_user_profile_title(user_id)
        except Exception:
            return False
        return normalize_profile_title(title) in STAFF_TITLES


def parse_structured_lecture_note(text):
    topic_marker = "Topic:"
    note_marker = "Note:"
    if topic_marker not in text or note_marker not in text:
        return None

    topic_start = text.find(topic_marker) + len(topic_marker)
    note_start = text.find(note_marker)
    topic = text[topic_start:note_start].strip()
    note_text = text[note_start + len(note_marker) :].strip()
    if not topic or not note_text:
        return None

    return {"topic": topic, "text": note_text}


def format_topic_list(topics):
    topic_lines = "\n".join(f"{index}. {topic}" for index, topic in enumerate(topics, start=1))
    return f"✨ Pick a topic to generate a quiz:\n\n{topic_lines}"


def format_lecture_note_source_prompt():
    return "\n".join(
        [
            "📝 How do you want to add lecture notes?",
            "",
            "1. Paste in Slack",
            "2. Import from Google Drive",
        ]
    )


def format_drive_file_list(files):
    file_lines = "\n".join(
        f"{index}. {file_data['title']}"
        for index, file_data in enumerate(files, start=1)
    )
    return f"Pick a Google Drive file to import:\n\n{file_lines}"


def derive_topic_from_drive_file(file_data):
    title = file_data.get("title", "Google Drive lecture note").strip()
    for suffix in (".gdoc", ".docx", ".pdf", ".md", ".txt"):
        if title.casefold().endswith(suffix):
            return title[: -len(suffix)].strip() or title
    return title


def build_drive_import_event_key(user_id, channel_id, selected_file, event_ts=None):
    file_id = selected_file.get("id")
    if not event_ts or not file_id:
        return None

    return f"drive-import:{user_id}:{channel_id}:{event_ts}:{file_id}"


def format_quiz_draft(draft):
    question_blocks = []
    for index, question in enumerate(draft["questions"], start=1):
        choices = question["choices"]
        question_blocks.append(
            "\n".join(
                [
                    f"Q{index}. {question['text']}",
                    f":one: {choices['one']}",
                    f":two: {choices['two']}",
                    f":three: {choices['three']}",
                    "",
                    f"Correct answer: {REACTION_LABELS[question['correct_reaction']]}",
                ]
            )
        )

    return (
        f"🧪 Draft quiz for *{draft['topic']}*\n\n"
        + "\n\n".join(question_blocks)
        + "\n\nReply `approve` to send this quiz, or `regenerate` to make a new draft."
    )


def format_student_quiz_intro(topic, question_count):
    return "\n".join(
        [
            f"🧠 *QUIZ: {topic}*",
            "",
            f"Please answer {question_count} questions by reacting to each question message with :one:, :two:, or :three:.",
        ]
    )


def format_student_question(question, question_index, question_count):
    choices = question["choices"]
    return "\n".join(
        [
            f"*_Question {question_index}/{question_count}: {question['text']}_*",
            "",
            f":one: {choices['one']}",
            f":two: {choices['two']}",
            f":three: {choices['three']}",
            "",
            "────────────────────",
        ]
    )


def format_quiz_summary(quiz_id, quiz):
    responses = quiz.get("responses", {})
    recipients = quiz.get("recipients", [])
    questions = quiz.get("questions", [])
    topic = quiz.get("topic", "Unknown topic")
    metrics = calculate_quiz_summary_metrics(quiz)
    lines = [
        f"📊 Quiz summary: *{topic}*",
        "",
        f"✅ Overall accuracy: {format_accuracy(metrics['accuracy'])}",
        f"👥 Responses: {len(responses)}/{len(recipients)} students",
        format_quiz_interpretation(topic, metrics),
    ]

    if metrics["submitted_answers"] > 0:
        lines.extend(
            [
                "",
                "────────────────────",
                "Question breakdown:",
            ]
        )

        for index, question in enumerate(questions, start=1):
            counts = count_question_reactions(question, responses)
            correct = question.get("correct_reaction")
            choices = question.get("choices", {})
            question_lines = [
                "",
                f"Q{index}. {question.get('text', 'Question text unavailable')}",
                f"Correct: {REACTION_LABELS.get(correct, correct)} {choices.get(correct, '')}".rstrip(),
            ]
            for reaction_name in REACTION_LABELS:
                question_lines.append(format_reaction_bar(reaction_name, counts[reaction_name]))
            lines.extend(question_lines)

    lines.extend(
        [
            "",
            f"Quiz ID: {quiz_id}",
        ]
    )
    return "\n".join(lines)


def calculate_quiz_summary_metrics(quiz):
    responses = quiz.get("responses", {})
    questions = quiz.get("questions", [])
    correct_by_question = {
        question.get("id"): question.get("correct_reaction")
        for question in questions
    }
    submitted_answers = 0
    correct_answers = 0

    for student_responses in responses.values():
        for question_id, reaction in student_responses.items():
            if question_id not in correct_by_question:
                continue

            submitted_answers += 1
            if reaction == correct_by_question[question_id]:
                correct_answers += 1

    accuracy = None
    if submitted_answers:
        accuracy = correct_answers / submitted_answers

    return {
        "submitted_answers": submitted_answers,
        "correct_answers": correct_answers,
        "accuracy": accuracy,
    }


def format_accuracy(accuracy):
    if accuracy is None:
        return "No responses yet"

    return f"{round(accuracy * 100)}%"


def format_quiz_interpretation(topic, metrics):
    accuracy = metrics["accuracy"]
    if accuracy is None:
        return "No student responses yet. Try again after students react to the quiz messages."

    if accuracy < 0.6:
        return f"⚠️ Many students struggled with *{topic}*. This topic may need a revisit."

    if accuracy < 0.8:
        return f"🟡 Students have a developing grasp of *{topic}*. A short review may help."

    return f"✅ Students generally have a good grasp of *{topic}*."


def count_question_reactions(question, responses):
    counts = {"one": 0, "two": 0, "three": 0}
    question_id = question.get("id")
    for student_responses in responses.values():
        reaction = student_responses.get(question_id)
        if reaction in counts:
            counts[reaction] += 1

    return counts


def format_reaction_bar(reaction_name, count):
    return f"{REACTION_LABELS[reaction_name]} {build_emoji_bar(reaction_name, count)} {count}"


def build_emoji_bar(reaction_name, count):
    if count <= 0:
        return "⬜"

    block_count = min(count, SUMMARY_BAR_MAX_BLOCKS)
    return BAR_BLOCKS[reaction_name] * block_count
