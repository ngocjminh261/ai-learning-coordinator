import os


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
        "PORT": int(os.environ.get("PORT", 8080)),
    }

    missing_env_vars = [
        name
        for name in ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN", "ADMIN_SLACK_ID")
        if not config[name]
    ]

    if missing_env_vars:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_env_vars)}")

    return config
