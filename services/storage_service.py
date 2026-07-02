import json
import threading
from pathlib import Path


class InMemoryStorage:
    def __init__(self, course_state_path="data/course_state.json"):
        self.student_topic_database = {}
        self.student_question_history = {}
        self.active_study_groups = {}
        self.course_state_path = Path(course_state_path)
        self.upload_tracking_lock = threading.Lock()
        self.in_progress_uploads = set()
        self.completed_uploads = set()

    def record_question(self, user_id, topic, message_text):
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

        return self.student_topic_database[user_id][topic]

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

    def save_course_canvas_state(self, course_map, canvas_id, channel_id):
        state = {
            "course_map": course_map,
            "faq_canvas": {
                "canvas_id": canvas_id,
                "channel_id": channel_id,
                "title": course_map.get("canvas_title"),
                "updated_at": course_map.get("created_at"),
            },
        }
        self.save_course_state(state)
        return state

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
