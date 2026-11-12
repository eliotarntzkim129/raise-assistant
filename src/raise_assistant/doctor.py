from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass

from .config import settings
from .providers import create_provider, provider_statuses


@dataclass
class Check:
    label: str
    ok: bool
    detail: str


def inspect() -> list[Check]:
    checks = [
        Check("Python", sys.version_info >= (3, 10), f"{sys.version.split()[0]} (3.10+ required)"),
        Check("Configuration", (settings.app_root / ".env").exists(), ".env exists" if (settings.app_root / ".env").exists() else "Run setup.sh or setup.ps1"),
    ]
    try:
        settings.prepare_directories()
        probe = settings.data_dir / ".doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(Check("Local storage", True, str(settings.data_dir)))
    except OSError as exc:
        checks.append(Check("Local storage", False, str(exc)))

    statuses = provider_statuses(settings)
    if any(item["configured"] for item in statuses):
        checks.append(Check("At least one provider", True, ", ".join(item["label"] for item in statuses if item["configured"])))
    else:
        checks.append(Check("At least one provider", False, "Run scripts/configure.py, or edit .env"))

    if settings.google_cloud_project:
        checks.append(Check("Google Cloud CLI", bool(shutil.which("gcloud")), "gcloud found" if shutil.which("gcloud") else "Install Google Cloud CLI for local login"))
        vertex = next(item for item in statuses if item["id"] == "vertex_gemini")
        checks.append(Check("Vertex credentials", bool(vertex["credentials_detected"]), vertex["detail"]))
        checks.append(Check("Vertex project", True, settings.google_cloud_project))
        checks.append(Check("Gemini region", bool(settings.vertex_location), settings.vertex_location or "Set VERTEX_LOCATION"))
        checks.append(Check("Claude region", bool(settings.vertex_claude_location), settings.vertex_claude_location or "Set VERTEX_CLAUDE_LOCATION"))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the local RAISE Assistant setup without printing secrets.")
    parser.add_argument("--test-provider", choices=[item["id"] for item in provider_statuses(settings)], help="Make one paid live model request to test this provider")
    parser.add_argument("--model", help="Override the configured model for the live test")
    args = parser.parse_args()

    checks = inspect()
    print("\nRAISE Assistant doctor\n")
    for item in checks:
        print(f"{'PASS' if item.ok else 'FAIL'}  {item.label}: {item.detail}")

    if args.test_provider:
        print(f"\nTesting {args.test_provider} with a small live request (provider charges may apply)…")
        try:
            response = create_provider(args.test_provider, args.model, settings).test()
            ok = "CONNECTION_OK" in response.upper()
            checks.append(Check("Live model response", ok, response[:200]))
            print(f"{'PASS' if ok else 'FAIL'}  Live model response: {response[:200]}")
        except Exception as exc:
            checks.append(Check("Live model response", False, str(exc)))
            print(f"FAIL  Live model response: {exc}")

    if not all(item.ok for item in checks):
        print("\nFix the FAIL items above, then rerun ./doctor.sh.")
        raise SystemExit(1)
    print("\nLocal configuration checks passed. Live model permissions require --test-provider.")


if __name__ == "__main__":
    main()

