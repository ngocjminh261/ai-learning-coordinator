import os


def parse_csv_env(value):
    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


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


def get_required_config():
    load_env_file()

    config = {
        "SLACK_BOT_TOKEN": os.environ.get("SLACK_BOT_TOKEN"),
        "SLACK_USER_TOKEN": os.environ.get("SLACK_USER_TOKEN"),
        "ADMIN_SLACK_ID": os.environ.get("ADMIN_SLACK_ID"),
        "ADMIN_SLACK_IDS": parse_csv_env(os.environ.get("ADMIN_SLACK_IDS")),
        "COURSE_CHANNEL_ID": os.environ.get("COURSE_CHANNEL_ID"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "GEMINI_MODEL": os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
        "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "llama3.1"),
        "COURSE_STATE_STORAGE_PATH": os.environ.get(
            "COURSE_STATE_STORAGE_PATH",
            "data/course_state.json",
        ),
        "PORT": int(os.environ.get("PORT", 8080)),
    }

    if config["ADMIN_SLACK_ID"] and config["ADMIN_SLACK_ID"] not in config["ADMIN_SLACK_IDS"]:
        config["ADMIN_SLACK_IDS"].append(config["ADMIN_SLACK_ID"])

    missing_env_vars = [
        name
        for name in ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN", "COURSE_CHANNEL_ID")
        if not config[name]
    ]

    if not config["ADMIN_SLACK_IDS"]:
        missing_env_vars.append("ADMIN_SLACK_IDS or ADMIN_SLACK_ID")

    if missing_env_vars:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_env_vars)}")

    return config
