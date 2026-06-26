import os
import json
import random
import time
import threading
from flask import Flask, request, jsonify
from slack_sdk import WebClient

app = Flask(__name__)

def load_env_file(file_path=".env"):
    if not os.path.exists(file_path):
        return

    with open(file_path) as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_USER_TOKEN = os.environ.get("SLACK_USER_TOKEN")
ADMIN_SLACK_ID = os.environ.get("ADMIN_SLACK_ID")

missing_env_vars = [
    name
    for name, value in {
        "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
        "SLACK_USER_TOKEN": SLACK_USER_TOKEN,
        "ADMIN_SLACK_ID": ADMIN_SLACK_ID,
    }.items()
    if not value
]

if missing_env_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_env_vars)}")

bot_client = WebClient(token=SLACK_BOT_TOKEN)
user_client = WebClient(token=SLACK_USER_TOKEN)

TOPIC_KEYWORDS = {
    "docker": ["docker", "container", "compose", "image", "volume"],
    "slack api": ["slack", "bot", "token", "event", "scope"],
    "python env": ["python", "pip", "uv", "venv", "import"],
    "api basics": ["api", "endpoint", "request", "response", "json"],
}

student_topic_database = {}
student_question_history = {}  
active_study_groups = {}     


def classify_topic(message_text):
    """Scans the text for dictionary keywords and returns the assigned topic name."""
    text_lower = message_text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return "unknown"


def auto_orchestrate_study_group(topic, new_student_id):
    """
    Automated Grouping Engine (Pattern A - Fully Briefed Private Channel):
    Creates or updates private focus lounges, making sure the professor can see
    the exact historical text backlog of every student who steps inside.
    """
    import random

    qualifying_students = [
        user_id for user_id, topics in student_topic_database.items()
        if topics.get(topic, 0) >= 3
    ]
    
    # CASE 1: Only 1 student has hit the threshold for this topic so far
    if len(qualifying_students) < 2:
        alert_text = (
            f"💡 *Individual Help Alert* 💡\n"
            f"👤 Student <@{new_student_id}> has hit the query threshold for *{topic.upper()}*.\n"
            f"📋 *Status:* Keeping student in the tracking queue. A study group will auto-provision once a second peer matches this topic."
        )
        bot_client.chat_postMessage(channel=ADMIN_SLACK_ID, text=alert_text)
        return

    # CASE 2: A private channel already exists for this topic -> Invite student and print their brief
    if topic in active_study_groups:
        group_data = active_study_groups[topic]
        group_channel_id = group_data["group_channel_id"]
        
        if new_student_id in group_data["student_ids"]:
            return
            
        try:
            user_client.conversations_invite(channel=group_channel_id, users=new_student_id)
            group_data["student_ids"].append(new_student_id)
            
            # Grab and print any new joining student's question history
            new_student_questions = student_question_history.get(new_student_id, {}).get(topic, ["Question text archived."])
            history_logs = f"👤 *<@{new_student_id}> asked:*\n"
            for q in new_student_questions:
                history_logs += f"  • _\"{q}\"_\n"

            bot_client.chat_postMessage(
                channel=group_channel_id,
                text=f"👋 Welcome <@{new_student_id}> to our ongoing *{topic.upper()}* focus session!\n\n"
                     f"📋 *Context Briefing for Course Staff:*\n{history_logs}"
            )
            
            admin_report = (
                f"📈 *Study Group Updated*\n\n"
                f"🏷️ *Topic:* {topic.title()} basics\n"
                f"👤 *Added Student:* <@{new_student_id}>\n"
                f"👥 *Current Roster:* " + ", ".join([f"<@{s}>" for s in group_data["student_ids"]]) + "\n"
                f"🎯 *Purpose:* Expanding active intervention workspace.\n\n"
                f"🔍 *New Backlog Material:*\n{history_logs}"
            )
            bot_client.chat_postMessage(channel=ADMIN_SLACK_ID, text=admin_report)
            
        except Exception as e:
            print(f"Error adding guest student via Admin token: {e}")

    # CASE 3: 2 students qualify and NO active group exists -> Create Admin-Owned Private Channel
    else:
        try:
            clean_topic = topic.replace(" ", "-")
            channel_name = f"lounge-{clean_topic}-{random.randint(100, 999)}"
            
            response = user_client.conversations_create(name=channel_name, is_private=True)
            
            if response.get("ok"):
                group_channel_id = response["channel"]["id"]
                
                try:
                    bot_user_id = bot_client.auth_test()["user_id"]
                    user_client.conversations_invite(channel=group_channel_id, users=bot_user_id)
                except Exception as bot_inv_err:
                    print(f"Note: Could not invite bot to private channel: {bot_inv_err}")

                for student in qualifying_students:
                    try:
                        user_client.conversations_invite(channel=group_channel_id, users=student)
                    except Exception as invite_err:
                        print(f"Admin token could not auto-invite {student}: {invite_err}")
                
                # Save state to memory
                active_study_groups[topic] = {
                    "topic": topic,
                    "group_channel_id": group_channel_id,
                    "student_ids": qualifying_students,
                    "status": "active"
                }
                
                history_logs = ""
                for student in qualifying_students:
                    student_questions = student_question_history.get(student, {}).get(topic, ["Question text archived."])
                    history_logs += f"👤 *<@{student}> asked:*\n"
                    for q in student_questions:
                        history_logs += f"  • _\"{q}\"_\n"
                
                bot_client.chat_postMessage(
                    channel=group_channel_id,
                    text=f"📚 *Welcome to the Proactive {topic.title()} Study Lounge!* 📚\n"
                         f"Hey team, I noticed some overlapping technical questions regarding *{topic.upper()}*. "
                         f"I've spun up this private channel with your course staff to clear up any bottlenecks together!\n\n"
                         f"📋 *Context Briefing for Course Staff:*\n{history_logs}"
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
                bot_client.chat_postMessage(channel=ADMIN_SLACK_ID, text=admin_report)
                
        except Exception as e:
            print(f"Error creating admin-authorized private channel: {e}")


def active_search_polling_worker():
    """
    Background Worker: Uses the native Slack Search API to query the workspace 
    for recent questions, syncing them with the live orchestration tracking matrix.
    """
    print("🚀 Real-Time Search API Polling Thread Started...")
    
    try:
        bot_user_id = bot_client.auth_test()["user_id"]
    except:
        bot_user_id = None

    while True:
        try:
            response = user_client.search_messages(query="?", count=10, sort="timestamp")
            
            if response.get("ok"):
                matches = response.get("messages", {}).get("matches", [])
                
                for match in matches:
                    user_id = match.get("user")
                    message_text = match.get("text", "").strip()
                    
                    if not user_id or user_id == bot_user_id or not message_text.endswith("?"):
                        continue
                    
                    assigned_topic = classify_topic(message_text)
                    if assigned_topic == "unknown":
                        continue
                        
                    if user_id not in student_topic_database:
                        student_topic_database[user_id] = {}
                    
                    current_topic_count = student_topic_database[user_id].get(assigned_topic, 0)
                    
                    if current_topic_count < 3:
                        if user_id not in student_question_history:
                            student_question_history[user_id] = {}
                        if assigned_topic not in student_question_history[user_id]:
                            student_question_history[user_id][assigned_topic] = []
                        student_question_history[user_id][assigned_topic].append(message_text)

                        student_topic_database[user_id][assigned_topic] = current_topic_count + 1
                        new_count = student_topic_database[user_id][assigned_topic]
                        
                        print(f"\n🔍 --- SEARCH API REAL-TIME MATCH DETECTED ---")
                        print(f"USER: <@{user_id}> | TOPIC: {assigned_topic.upper()} | COUNT: {new_count}")
                        print(f"TEXT: \"{message_text}\"")
                        print(f"-----------------------------------------------\n")
                        
                        if new_count == 3:
                            print(f"🚨 SEARCH API THRESHOLD: User <@{user_id}> hit 3 questions!")
                            auto_orchestrate_study_group(assigned_topic, user_id)
                            
        except Exception as e:
            print(f"Search API Polling Error: {e}")
            
        time.sleep(10)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    
    if data and "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
        
    if data and "event" in data:
        event = data["event"]
        
        if event.get("type") == "message" and not event.get("bot_id"):
            message_text = event.get("text", "").strip()
            user_id = event.get("user")
            
            if message_text.endswith("?"):
                assigned_topic = classify_topic(message_text)
                
                if user_id not in student_topic_database:
                    student_topic_database[user_id] = {}
                
                if user_id not in student_question_history:
                    student_question_history[user_id] = {}
                if assigned_topic not in student_question_history[user_id]:
                    student_question_history[user_id][assigned_topic] = []
                student_question_history[user_id][assigned_topic].append(message_text)

                student_topic_database[user_id][assigned_topic] = student_topic_database[user_id].get(assigned_topic, 0) + 1
                current_topic_count = student_topic_database[user_id][assigned_topic]
                
                print(f"\n📊 --- REAL-TIME TOPIC LOGGING MATRIX ---")
                print(f"USER: <@{user_id}> | TOPIC: {assigned_topic.upper()} | COUNT: {current_topic_count}")
                print(f"-----------------------------------------\n")
                
                # If keyword is unknown, track it silently but bypass automated group triggers
                if assigned_topic == "unknown":
                    return jsonify({"status": "ok"})
                
                if current_topic_count == 3:
                    print(f"🚨 TOPIC THRESHOLD: User <@{user_id}> hit 3 questions for topic '{assigned_topic}'!")
                    
                    auto_orchestrate_study_group(assigned_topic, user_id)
                        
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Start the active Slack Search API engine in a concurrent background thread
    search_thread = threading.Thread(target=active_search_polling_worker, daemon=True)
    search_thread.start()
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))