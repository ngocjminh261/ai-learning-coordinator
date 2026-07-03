import threading

from flask import Flask

from config import get_required_config
from events.slack_events import active_search_polling_worker, handle_slack_event_payload
from features.syllabus_compiler import SyllabusCompiler
from features.study_groups import StudyGroupOrchestrator
from services.ai_service import SyllabusAIService
from services.slack_service import SlackService
from services.storage_service import InMemoryStorage

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


app = Flask(__name__)

config = get_required_config()
storage = InMemoryStorage(course_state_path=config["COURSE_STATE_STORAGE_PATH"])
slack_service = SlackService(
    bot_token=config["SLACK_BOT_TOKEN"],
    user_token=config["SLACK_USER_TOKEN"],
    admin_slack_id=config["ADMIN_SLACK_ID"] or config["ADMIN_SLACK_IDS"][0],
)
ai_service = SyllabusAIService(
    gemini_api_key=config["GEMINI_API_KEY"],
    gemini_model=config["GEMINI_MODEL"],
    ollama_base_url=config["OLLAMA_BASE_URL"],
    ollama_model=config["OLLAMA_MODEL"],
)
study_group_orchestrator = StudyGroupOrchestrator(storage, slack_service)
syllabus_compiler = SyllabusCompiler(
    storage=storage,
    slack_service=slack_service,
    ai_service=ai_service,
    admin_slack_ids=config["ADMIN_SLACK_IDS"],
    course_channel_id=config["COURSE_CHANNEL_ID"],
)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handle_slack_event_payload(storage, study_group_orchestrator, syllabus_compiler)


if __name__ == "__main__":
    # Start the active Slack Search API engine in a concurrent background thread
    search_thread = threading.Thread(
        target=active_search_polling_worker,
        args=(storage, slack_service, study_group_orchestrator),
        daemon=True,
    )
    search_thread.start()

    app.run(host="0.0.0.0", port=config["PORT"])
