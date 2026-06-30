class InMemoryStorage:
    def __init__(self):
        self.student_topic_database = {}
        self.student_question_history = {}
        self.active_study_groups = {}

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
