import random


TOPIC_KEYWORDS = {
    "docker": ["docker", "container", "compose", "image", "volume"],
    "slack api": ["slack", "bot", "token", "event", "scope"],
    "python env": ["python", "pip", "uv", "venv", "import"],
    "api basics": ["api", "endpoint", "request", "response", "json"],
}


def classify_topic(message_text):
    """Scans the text for dictionary keywords and returns the assigned topic name."""
    text_lower = message_text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return "unknown"


class StudyGroupOrchestrator:
    def __init__(self, storage, slack_service):
        self.storage = storage
        self.slack_service = slack_service

    def auto_orchestrate_study_group(self, topic, new_student_id):
        """
        Automated Grouping Engine (Pattern A - Fully Briefed Private Channel):
        Creates or updates private focus lounges, making sure the professor can see
        the exact historical text backlog of every student who steps inside.
        """
        qualifying_students = self.storage.get_qualifying_students(topic)

        # CASE 1: Only 1 student has hit the threshold for this topic so far
        if len(qualifying_students) < 2:
            alert_text = (
                f"💡 *Individual Help Alert* 💡\n"
                f"👤 Student <@{new_student_id}> has hit the query threshold for *{topic.upper()}*.\n"
                f"📋 *Status:* Keeping student in the tracking queue. A study group will auto-provision once a second peer matches this topic."
            )
            self.slack_service.post_admin_message(alert_text)
            return

        # CASE 2: A private channel already exists for this topic -> Invite student and print their brief
        group_data = self.storage.get_study_group(topic)
        if group_data:
            group_channel_id = group_data["group_channel_id"]

            if new_student_id in group_data["student_ids"]:
                return

            try:
                self.slack_service.invite_user_to_channel(group_channel_id, new_student_id)
                group_data["student_ids"].append(new_student_id)

                new_student_questions = self.storage.get_question_history(new_student_id, topic)
                history_logs = self._format_student_history(new_student_id, new_student_questions)

                self.slack_service.post_channel_message(
                    group_channel_id,
                    text=f"👋 Welcome <@{new_student_id}> to our ongoing *{topic.upper()}* focus session!\n\n"
                    f"📋 *Context Briefing for Course Staff:*\n{history_logs}",
                )

                admin_report = (
                    f"📈 *Study Group Updated*\n\n"
                    f"🏷️ *Topic:* {topic.title()} basics\n"
                    f"👤 *Added Student:* <@{new_student_id}>\n"
                    f"👥 *Current Roster:* " + ", ".join([f"<@{s}>" for s in group_data["student_ids"]]) + "\n"
                    f"🎯 *Purpose:* Expanding active intervention workspace.\n\n"
                    f"🔍 *New Backlog Material:*\n{history_logs}"
                )
                self.slack_service.post_admin_message(admin_report)

            except Exception as e:
                print(f"Error adding guest student via Admin token: {e}")

        # CASE 3: 2 students qualify and NO active group exists -> Create Admin-Owned Private Channel
        else:
            try:
                clean_topic = topic.replace(" ", "-")
                channel_name = f"lounge-{clean_topic}-{random.randint(100, 999)}"

                response = self.slack_service.create_private_channel(channel_name)

                if response.get("ok"):
                    group_channel_id = response["channel"]["id"]

                    try:
                        bot_user_id = self.slack_service.get_bot_user_id()
                        self.slack_service.invite_user_to_channel(group_channel_id, bot_user_id)
                    except Exception as bot_inv_err:
                        print(f"Note: Could not invite bot to private channel: {bot_inv_err}")

                    for student in qualifying_students:
                        try:
                            self.slack_service.invite_user_to_channel(group_channel_id, student)
                        except Exception as invite_err:
                            print(f"Admin token could not auto-invite {student}: {invite_err}")

                    self.storage.save_study_group(
                        topic,
                        {
                            "topic": topic,
                            "group_channel_id": group_channel_id,
                            "student_ids": qualifying_students,
                            "status": "active",
                        },
                    )

                    history_logs = ""
                    for student in qualifying_students:
                        student_questions = self.storage.get_question_history(student, topic)
                        history_logs += self._format_student_history(student, student_questions)

                    self.slack_service.post_channel_message(
                        group_channel_id,
                        text=f"📚 *Welcome to the Proactive {topic.title()} Study Lounge!* 📚\n"
                        f"Hey team, I noticed some overlapping technical questions regarding *{topic.upper()}*. "
                        f"I've spun up this private channel with your course staff to clear up any bottlenecks together!\n\n"
                        f"📋 *Context Briefing for Course Staff:*\n{history_logs}",
                    )

                    students_formatted = ", ".join([f"<@{s}>" for s in qualifying_students])
                    admin_report = (
                        f"✨ *Study group created*\n\n"
                        f"🏷️ *Topic:* {topic.title()} basics\n"
                        f"👥 *Students:* {students_formatted}\n"
                        f"📊 *Reason:* Each student asked multiple recent questions about {topic.title()} setup.\n"
                        f"🎯 *Purpose:* Fast follow-up and ad hoc help for today's {topic.title()} confusion.\n\n"
                        f"🔍 *Aggregated Backlog Material:*\n{history_logs}"
                    )
                    self.slack_service.post_admin_message(admin_report)

            except Exception as e:
                print(f"Error creating admin-authorized private channel: {e}")

    def _format_student_history(self, student_id, questions):
        history_logs = f"👤 *<@{student_id}> asked:*\n"
        for question in questions:
            history_logs += f"  • _\"{question}\"_\n"
        return history_logs
