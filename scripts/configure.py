#!/usr/bin/env python3
"""Interactive, local-only provider configuration."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

from dotenv import set_key


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"


def ask(label: str, current: str = "", *, secret: bool = False) -> str:
    suffix = " [already set]" if secret and current else f" [{current}]" if current else ""
    prompt = f"{label}{suffix}: "
    try:
        answer = getpass.getpass(prompt) if secret else input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nConfiguration ended. Your previous settings were preserved.")
        sys.exit(0)
    return answer.strip() or current


def read_current() -> dict[str, str]:
    from dotenv import dotenv_values

    return {key: value or "" for key, value in dotenv_values(ENV_FILE).items() if key}


def save(key: str, value: str) -> None:
    set_key(ENV_FILE, key, value, quote_mode="always")


def configure_choice(choice: str, current: dict[str, str]) -> None:
    if choice == "1":
        key = ask("Paste OpenAI API key", current.get("OPENAI_API_KEY", ""), secret=True)
        if key:
            save("OPENAI_API_KEY", key)
        save("OPENAI_MODEL", ask("OpenAI model ID", current.get("OPENAI_MODEL", "gpt-5.5")))
    elif choice == "2":
        key = ask("Paste Anthropic API key", current.get("ANTHROPIC_API_KEY", ""), secret=True)
        if key:
            save("ANTHROPIC_API_KEY", key)
        save("ANTHROPIC_MODEL", ask("Claude model ID", current.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")))
    elif choice == "3":
        key = ask("Paste Gemini API key", current.get("GEMINI_API_KEY", ""), secret=True)
        if key:
            save("GEMINI_API_KEY", key)
        save("GEMINI_MODEL", ask("Gemini model ID", current.get("GEMINI_MODEL", "gemini-3.8-flash")))
    elif choice == "4":
        project = ask("Google Cloud project ID", current.get("GOOGLE_CLOUD_PROJECT", ""))
        if project:
            save("GOOGLE_CLOUD_PROJECT", project)
        save("VERTEX_LOCATION", ask("Gemini region", current.get("VERTEX_LOCATION", "global")))
        save("VERTEX_GEMINI_MODEL", ask("Gemini on Vertex model ID", current.get("VERTEX_GEMINI_MODEL", "gemini-3.8-flash")))
        save("VERTEX_CLAUDE_LOCATION", ask("Claude on Vertex region", current.get("VERTEX_CLAUDE_LOCATION", "global")))
        save("VERTEX_CLAUDE_MODEL", ask("Claude Model Garden model ID", current.get("VERTEX_CLAUDE_MODEL", "claude-opus-4-8")))
        print("\nNext on this computer: bash scripts/gcp_local_auth.sh --project YOUR_PROJECT_ID")
        print("Your Google Cloud administrator may first need to run scripts/gcp_bootstrap.sh in Cloud Shell.")


def main() -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_bytes(EXAMPLE.read_bytes())
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass

    print("\nRAISE Assistant setup")
    print("Configure one or several model routes. Press Enter to keep an existing setting.")
    print("Keys are saved only in this computer's .env file.")
    while True:
        print("\n1. OpenAI API key")
        print("2. Claude API key")
        print("3. Gemini API key")
        print("4. Vertex AI (Google sign-in; Gemini and enabled Claude models)")
        print("5. Done for now")
        choice = ask("Select 1–5", "5")
        if choice == "5":
            break
        if choice not in {"1", "2", "3", "4"}:
            print("Choose a number from 1 to 5.")
            continue
        configure_choice(choice, read_current())

    print("\nConfiguration saved. You can rerun this wizard any time.")


if __name__ == "__main__":
    main()

