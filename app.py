import threading

from flask import Flask

from config import get_required_config
from events.slack_events import active_search_polling_worker, handle_slack_event_payload
from features.study_groups import StudyGroupOrchestrator
from services.slack_service import SlackService
from services.storage_service import InMemoryStorage


app = Flask(__name__)

config = get_required_config()
storage = InMemoryStorage()
slack_service = SlackService(
    bot_token=config["SLACK_BOT_TOKEN"],
    user_token=config["SLACK_USER_TOKEN"],
    admin_slack_id=config["ADMIN_SLACK_ID"],
)
study_group_orchestrator = StudyGroupOrchestrator(storage, slack_service)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handle_slack_event_payload(storage, study_group_orchestrator)


if __name__ == "__main__":
    # Start the active Slack Search API engine in a concurrent background thread
    search_thread = threading.Thread(
        target=active_search_polling_worker,
        args=(storage, slack_service, study_group_orchestrator),
        daemon=True,
    )
    search_thread.start()

    app.run(host="0.0.0.0", port=config["PORT"])
