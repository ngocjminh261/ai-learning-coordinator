import threading

from flask import Flask, redirect, request

from config import get_required_config
from events.slack_events import active_search_polling_worker, handle_slack_event_payload
from features.quiz_maker import QuizMaker
from features.syllabus_compiler import SyllabusCompiler
from features.study_groups import StudyGroupOrchestrator
from services.ai_service import SyllabusAIService
from services.google_drive_mcp_service import (
    GoogleDriveMCPService,
    GoogleDriveOAuthError,
    GoogleDriveOAuthService,
)
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
google_drive_oauth_service = GoogleDriveOAuthService(
    client_id=config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=config["GOOGLE_OAUTH_CLIENT_SECRET"],
    redirect_uri=config["GOOGLE_OAUTH_REDIRECT_URI"],
    token_path=config["GOOGLE_OAUTH_TOKEN_PATH"],
)
google_drive_mcp_service = GoogleDriveMCPService(
    oauth_service=google_drive_oauth_service,
    server_url=config["GOOGLE_DRIVE_MCP_SERVER_URL"],
    lecture_file_id=config["GOOGLE_DRIVE_LECTURE_FILE_ID"],
)
study_group_orchestrator = StudyGroupOrchestrator(
    storage, 
    slack_service, 
    ta_channel_id=config.get("SLACK_TA_CHANNEL_ID")
)
syllabus_compiler = SyllabusCompiler(
    storage=storage,
    slack_service=slack_service,
    ai_service=ai_service,
    admin_slack_ids=config["ADMIN_SLACK_IDS"],
    course_channel_id=config["COURSE_CHANNEL_ID"],
)
quiz_maker = QuizMaker(
    storage=storage,
    slack_service=slack_service,
    ai_service=ai_service,
    course_channel_id=config["COURSE_CHANNEL_ID"],
    drive_service=google_drive_mcp_service,
)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handle_slack_event_payload(
        storage,
        study_group_orchestrator,
        syllabus_compiler,
        quiz_maker,
    )


@app.route("/google/oauth/start", methods=["GET"])
def google_oauth_start():
    try:
        return redirect(google_drive_oauth_service.build_authorization_url())
    except GoogleDriveOAuthError as exc:
        return str(exc), 500


@app.route("/google/oauth/callback", methods=["GET"])
def google_oauth_callback():
    if request.args.get("error"):
        return f"Google OAuth failed: {request.args['error']}", 400

    try:
        google_drive_oauth_service.exchange_code_for_token(request.args.get("code"))
    except GoogleDriveOAuthError as exc:
        return f"Could not save Google OAuth token: {exc}", 500

    return "Google Drive OAuth connected. You can close this tab."


if __name__ == "__main__":
    # Start the active Slack Search API engine in a concurrent background thread
    search_thread = threading.Thread(
        target=active_search_polling_worker,
        args=(storage, slack_service, study_group_orchestrator),
        daemon=True,
    )
    search_thread.start()

    app.run(host="0.0.0.0", port=config["PORT"])
