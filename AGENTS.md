# Repository Guidelines

## Project Structure & Module Organization

This is a small Python Flask app for Slack event handling.

- `app.py` is the app entrypoint and defines `/slack/events`.
- `README.md` contains setup, Slack scopes, ngrok, and run instructions.
- `app_flow.md` explains the current app flow step by step.
- `docs/scope.md` defines hackathon MVP scope and non-goals.
- `docs/system-design.md` maps the planned modular implementation.
- `.env.example` lists required local configuration keys; `.env` is local only.
- `pyproject.toml` and `uv.lock` define the Python project; runtime dependencies are currently documented in `README.md`.

No `tests/` directory exists yet. Add tests under `tests/` as behavior moves into helper functions.

## Active Product Features

The app is being developed around three Slack-based learning features:

- A bot that automatically creates study groups for lagging students.
- An automatic quiz maker that summarizes student knowledge for teachers or professors.
- A bot that combs through Slack channels to create an FAQ from repeated questions and useful answers.

Keep these features modular. Separate Slack event parsing, feature decisions, Slack API calls, AI/model calls, and storage so one feature can fail without breaking the others.

## Build, Test, and Development Commands

Install runtime dependencies:

```bash
pip3 install flask slack_sdk
```

Run the app locally:

```bash
python3 app.py
```

Expose the local Flask server for Slack:

```bash
ngrok http 8080
```

If using `uv`, prefer:

```bash
uv run python app.py
```

There is no build step or test command yet.

## Coding Style & Naming Conventions

Use standard Python style with 4-space indentation. Prefer clear function names such as `load_env_file`, `send_admin_alert`, or `handle_message_event`. Keep Slack API code separate from feature logic.

Avoid hardcoding tokens or workspace-specific IDs in Python files. Read configuration from environment variables loaded from `.env`.

## Testing Guidelines

No test framework is configured yet. When adding tests, use `pytest` and name files like:

```text
tests/test_question_tracker.py
```

Prioritize tests for message parsing, question counting, threshold behavior, and Slack alert formatting. Mock Slack clients in tests.

## Commit & Pull Request Guidelines

Recent commits use short imperative or descriptive messages, for example `updated README`. Keep commits small and focused.

Pull requests should include:

- A short summary of behavior changed
- Any new environment variables or Slack scopes
- Manual test steps, especially Slack/ngrok verification
- Screenshots or Slack message examples when user-facing alerts change

## Security & Configuration Tips

Never commit real `.env` values or Slack tokens. Keep `.env.example` safe to share. Reinstall the Slack app after changing scopes or event subscriptions.
