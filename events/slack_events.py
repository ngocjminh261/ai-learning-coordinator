import time

from flask import jsonify, request

from features.study_groups import classify_topic


def handle_slack_event_payload(storage, study_group_orchestrator):
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
                current_topic_count = storage.record_question(user_id, assigned_topic, message_text)

                print(f"\n📊 --- REAL-TIME TOPIC LOGGING MATRIX ---")
                print(f"USER: <@{user_id}> | TOPIC: {assigned_topic.upper()} | COUNT: {current_topic_count}")
                print(f"-----------------------------------------\n")

                # If keyword is unknown, track it silently but bypass automated group triggers
                if assigned_topic == "unknown":
                    return jsonify({"status": "ok"})

                if current_topic_count == 3:
                    print(f"🚨 TOPIC THRESHOLD: User <@{user_id}> hit 3 questions for topic '{assigned_topic}'!")
                    _trigger_study_group(study_group_orchestrator, assigned_topic, user_id)

    return jsonify({"status": "ok"})


def active_search_polling_worker(storage, slack_service, study_group_orchestrator):
    """
    Background Worker: Uses Slack search to query the workspace for recent
    questions, syncing them with the live orchestration tracking matrix.
    """
    print("🚀 Real-Time Search API Polling Thread Started...")

    try:
        bot_user_id = slack_service.get_bot_user_id()
    except Exception:
        bot_user_id = None

    while True:
        try:
            response = slack_service.search_recent_questions()

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

                    current_topic_count = storage.get_topic_count(user_id, assigned_topic)

                    if current_topic_count < 3:
                        new_count = storage.record_question(user_id, assigned_topic, message_text)

                        print(f"\n🔍 --- SEARCH API REAL-TIME MATCH DETECTED ---")
                        print(f"USER: <@{user_id}> | TOPIC: {assigned_topic.upper()} | COUNT: {new_count}")
                        print(f"TEXT: \"{message_text}\"")
                        print(f"-----------------------------------------------\n")

                        if new_count == 3:
                            print(f"🚨 SEARCH API THRESHOLD: User <@{user_id}> hit 3 questions!")
                            _trigger_study_group(study_group_orchestrator, assigned_topic, user_id)

        except Exception as e:
            print(f"Search API Polling Error: {e}")

        time.sleep(10)


def _trigger_study_group(study_group_orchestrator, assigned_topic, user_id):
    try:
        study_group_orchestrator.auto_orchestrate_study_group(assigned_topic, user_id)
    except Exception as e:
        print(f"Study group orchestration error: {e}")
