import json
import threading
from pathlib import Path


class InMemoryStorage:
    def __init__(self, course_state_path="data/course_state.json"):
        self.student_topic_database = {}
        self.student_question_history = {}
        self.seen_question_message_keys = set()
        self.active_study_groups = {}
        self.course_state_path = Path(course_state_path)
        self.upload_tracking_lock = threading.Lock()
        self.course_state_lock = threading.RLock()
        self.in_progress_uploads = set()
        self.completed_uploads = set()

    def record_question(self, user_id, topic, message_text, message_key=None):
        if message_key in self.seen_question_message_keys:
            return self.get_topic_count(user_id, topic), False

        if user_id not in self.student_topic_database:
            self.student_topic_database[user_id] = {}

        if user_id not in self.student_question_history:
            self.student_question_history[user_id] = {}

        if topic not in self.student_question_history[user_id]:
            self.student_question_history[user_id][topic] = []

        self.student_question_history[user_id][topic].append(message_text)
        self.student_topic_database[user_id][topic] = (
            self.student_topic_database[user_id].get(topic, 0) + 1
        )

        if message_key:
            self.seen_question_message_keys.add(message_key)

        return self.student_topic_database[user_id][topic], True

    def get_topic_count(self, user_id, topic):
        if user_id not in self.student_topic_database:
            self.student_topic_database[user_id] = {}

        return self.student_topic_database[user_id].get(topic, 0)

    def get_qualifying_students(self, topic, threshold=3):
        return [
            user_id
            for user_id, topics in self.student_topic_database.items()
            if topics.get(topic, 0) >= threshold
        ]

    def get_question_history(self, user_id, topic):
        return self.student_question_history.get(user_id, {}).get(
            topic,
            ["Question text archived."],
        )

    def get_study_group(self, topic):
        return self.active_study_groups.get(topic)

    def save_study_group(self, topic, group_data):
        self.active_study_groups[topic] = group_data

    def load_course_state(self):
        if not self.course_state_path.exists():
            return {}

        with self.course_state_path.open() as state_file:
            return json.load(state_file)

    def save_course_state(self, state):
        self.course_state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.course_state_path.open("w") as state_file:
            json.dump(state, state_file, indent=2)
            state_file.write("\n")

    def update_course_state(self, updates):
        state = self.load_course_state()
        state.update(updates)
        self.save_course_state(state)
        return state

    def save_course_canvas_state(self, course_map, canvas_id, channel_id):
        updates = {
            "course_map": course_map,
            "faq_canvas": {
                "canvas_id": canvas_id,
                "channel_id": channel_id,
                "title": course_map.get("canvas_title"),
                "updated_at": course_map.get("created_at"),
            },
        }
        return self.update_course_state(updates)

    def get_active_canvas_id(self):
        state = self.load_course_state()
        return state.get("faq_canvas", {}).get("canvas_id")

    def begin_upload(self, upload_key):
        with self.upload_tracking_lock:
            if upload_key in self.in_progress_uploads:
                return "duplicate_in_progress"
            if upload_key in self.completed_uploads:
                return "duplicate_completed"

            self.in_progress_uploads.add(upload_key)
            return "started"

    def complete_upload(self, upload_key):
        with self.upload_tracking_lock:
            self.in_progress_uploads.discard(upload_key)
            self.completed_uploads.add(upload_key)

    def fail_upload(self, upload_key):
        with self.upload_tracking_lock:
            self.in_progress_uploads.discard(upload_key)

    def save_lecture_note(self, topic, note_text, sender, channel, source=None):
        note = {
            "topic": topic,
            "text": note_text,
            "sender": sender,
            "channel": channel,
        }
        if source:
            note["source"] = source

        state = self.load_course_state()
        lecture_notes = state.setdefault("lecture_notes", [])
        lecture_notes.append(note)
        self.save_course_state(state)
        return note

    def get_lecture_notes(self):
        return self.load_course_state().get("lecture_notes", [])

    def get_lecture_note_topics(self):
        topics = []
        seen = set()
        for note in self.get_lecture_notes():
            topic = note.get("topic")
            if topic and topic not in seen:
                topics.append(topic)
                seen.add(topic)
        return topics

    def get_notes_for_topic(self, topic):
        return [
            note
            for note in self.get_lecture_notes()
            if note.get("topic", "").casefold() == topic.casefold()
        ]

    def set_pending_action(self, user_id, state_name, **data):
        state = self.load_course_state()
        pending_actions = state.setdefault("pending_actions", {})
        pending_actions[user_id] = {"state": state_name, **data}
        self.save_course_state(state)
        return pending_actions[user_id]

    def get_pending_action(self, user_id):
        return self.load_course_state().get("pending_actions", {}).get(user_id)

    def clear_pending_action(self, user_id):
        state = self.load_course_state()
        pending_actions = state.setdefault("pending_actions", {})
        pending_actions.pop(user_id, None)
        self.save_course_state(state)

    def claim_processed_event(self, event_key):
        with self.course_state_lock:
            state = self.load_course_state()
            processed_events = state.setdefault("processed_events", {})
            if event_key in processed_events:
                return False

            processed_events[event_key] = True
            self.save_course_state(state)
            return True

    def save_quiz_draft(self, user_id, draft):
        state = self.load_course_state()
        quiz_drafts = state.setdefault("quiz_drafts", {})
        quiz_drafts[user_id] = draft
        self.save_course_state(state)
        return draft

    def get_quiz_draft(self, user_id):
        return self.load_course_state().get("quiz_drafts", {}).get(user_id)

    def clear_quiz_draft(self, user_id):
        state = self.load_course_state()
        quiz_drafts = state.setdefault("quiz_drafts", {})
        quiz_drafts.pop(user_id, None)
        self.save_course_state(state)

    def pop_quiz_draft(self, user_id):
        with self.course_state_lock:
            state = self.load_course_state()
            quiz_drafts = state.setdefault("quiz_drafts", {})
            draft = quiz_drafts.pop(user_id, None)
            self.save_course_state(state)
            return draft

    def save_active_quiz(self, quiz_id, quiz):
        state = self.load_course_state()
        active_quizzes = state.setdefault("active_quizzes", {})
        active_quizzes[quiz_id] = quiz
        owner = quiz.get("owner")
        if owner:
            current_quiz_by_owner = state.setdefault("current_quiz_by_owner", {})
            current_quiz_by_owner[owner] = quiz_id
        self.save_course_state(state)
        return quiz

    def get_active_quizzes(self):
        return self.load_course_state().get("active_quizzes", {})

    def get_current_quiz_for_owner(self, owner):
        state = self.load_course_state()
        quiz_id = state.get("current_quiz_by_owner", {}).get(owner)
        if not quiz_id:
            return None, None

        quiz = state.get("active_quizzes", {}).get(quiz_id)
        if not quiz:
            return None, None

        return quiz_id, quiz

    def find_quiz_question_by_message(self, channel_id, message_ts):
        for quiz_id, quiz in self.get_active_quizzes().items():
            for question in quiz.get("sent_questions", []):
                if question.get("channel") == channel_id and question.get("ts") == message_ts:
                    return quiz_id, quiz, question
        return None, None, None

    def record_quiz_response(self, quiz_id, question_id, student_id, reaction):
        state = self.load_course_state()
        active_quizzes = state.setdefault("active_quizzes", {})
        quiz = active_quizzes.get(quiz_id)
        if not quiz:
            return None

        responses = quiz.setdefault("responses", {})
        student_responses = responses.setdefault(student_id, {})
        student_responses[question_id] = reaction
        self.save_course_state(state)
        return student_responses

    def replace_quiz_responses(self, quiz_id, responses):
        state = self.load_course_state()
        active_quizzes = state.setdefault("active_quizzes", {})
        quiz = active_quizzes.get(quiz_id)
        if not quiz:
            return None

        quiz["responses"] = responses
        self.save_course_state(state)
        return responses
