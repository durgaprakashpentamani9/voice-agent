"""Provision and operate the LAP voice agent through Retell's public API.

No API request is made by importing this module or running its tests. The
``call`` command requires an explicit confirmation because it places a real
outbound phone call.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
API_ROOT = "https://api.retellai.com"
PROMPT_PATH = ROOT / "system_prompt.md"
RESOURCE_PATH = ROOT / "retell-resources.json"
ARTIFACTS_PATH = ROOT / "artifacts"
REQUIRED_PROMPT_VARIABLES = (
    "company_name", "customer_name", "agent_name", "agent_gender", "current_date",
    "current_day", "current_time", "additional_context_from_rag", "language_to_speak",
    "conversation_history", "customer_utterance",
)


class RetellError(RuntimeError):
    pass


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Load simple KEY=VALUE lines without overriding the process environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RetellError(f"Required configuration is missing: {name}. Set it in .env or the process environment.")
    return value


def load_prompt() -> str:
    if not PROMPT_PATH.is_file():
        raise RetellError(f"System prompt not found: {PROMPT_PATH}")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_PROMPT_VARIABLES if f"{{{{{name}}}}}" not in prompt]
    if missing:
        raise RetellError("System prompt is missing variables: " + ", ".join(missing))
    sections = [int(value) for value in re.findall(r"(?m)^# (\d+)\.", prompt)]
    if sections != list(range(1, 15)):
        raise RetellError("System prompt must keep sections 1 through 14 in order.")
    if prompt.rstrip().splitlines()[-1] != "- Never hand off before all seven items are complete and passed.":
        raise RetellError("GOLDEN RULES must remain the final prompt content.")
    return prompt


def retell_request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    api_key = required_env("RETELL_API_KEY")
    encoded_body = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        API_ROOT + path,
        data=encoded_body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=40) as response:
            payload = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RetellError(f"Retell API returned HTTP {exc.code}: {detail[:2000]}") from None
    except URLError as exc:
        raise RetellError(f"Could not reach Retell API: {exc.reason}") from None
    if not payload:
        return {}
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        raise RetellError("Retell API returned a non-JSON response.") from None


def build_llm_payload(prompt: str) -> dict[str, Any]:
    return {
        "start_speaker": "agent",
        "general_prompt": prompt,
        "general_tools": [
            {"type": "end_call", "name": "end_call", "description": "End the call after a specified terminal branch."}
        ],
        # Empty values prevent unresolved brace placeholders. The prompt tells
        # the model to use Retell's actual live message context as the turn grows.
        "default_dynamic_variables": {"conversation_history": "", "customer_utterance": ""},
        "model_temperature": 0,
    }


def build_agent_payload(llm_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "response_engine": {"type": "retell-llm", "llm_id": llm_id, "version": 0},
        "agent_name": required_env("RETELL_AGENT_LABEL"),
        "voice_id": required_env("RETELL_VOICE_ID"),
        # The prompt limits replies to the configured call language. Retell
        # supports this locale array for the corresponding ASR/TTS language pair.
        "language": ["en-IN", "hi-IN"],
        "interruption_sensitivity": float(os.environ.get("RETELL_INTERRUPTION_SENSITIVITY", "0.85")),
        "enable_backchannel": False,
        "enable_dnc_detection": True,
        "data_storage_setting": os.environ.get("RETELL_DATA_STORAGE_SETTING", "everything"),
        "opt_in_signed_url": os.environ.get("RETELL_SIGNED_URLS", "true").lower() == "true",
    }
    webhook = os.environ.get("RETELL_WEBHOOK_URL", "").strip()
    if webhook:
        payload["webhook_url"] = webhook
        payload["webhook_events"] = ["call_ended", "call_analyzed"]
    return payload


def _resource_ids() -> dict[str, Any]:
    if not RESOURCE_PATH.exists():
        return {}
    try:
        return json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RetellError("retell-resources.json is unreadable; correct or remove that local resource record before provisioning.") from None


def _write_resource_ids(data: dict[str, Any]) -> None:
    RESOURCE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def provision_agent(publish: bool = True) -> dict[str, Any]:
    prompt = load_prompt()
    agent_label = required_env("RETELL_AGENT_LABEL")
    voice_id = required_env("RETELL_VOICE_ID")
    resources = _resource_ids()

    if resources.get("llm_id") and resources.get("agent_id"):
        llm_id = resources["llm_id"]
        llm_response = retell_request("PATCH", f"/update-retell-llm/{quote(llm_id, safe='')}", build_llm_payload(prompt))
        agent_body = build_agent_payload(llm_id)
        agent_body.pop("response_engine", None)  # Response-engine reassignment is not needed for an existing agent.
        agent_response = retell_request("PATCH", f"/update-agent/{quote(resources['agent_id'], safe='')}", agent_body)
        agent_id = resources["agent_id"]
    else:
        llm_response = retell_request("POST", "/create-retell-llm", build_llm_payload(prompt))
        llm_id = llm_response.get("llm_id")
        if not llm_id:
            raise RetellError("Retell did not return llm_id; no agent was created.")
        resources.update({"llm_id": llm_id, "published": False})
        _write_resource_ids(resources)
        agent_response = retell_request("POST", "/create-agent", build_agent_payload(llm_id))
        agent_id = agent_response.get("agent_id")
        if not agent_id:
            raise RetellError(f"Retell created LLM {llm_id}, but did not return agent_id. Check the Retell dashboard before retrying.")
        resources.update({"llm_id": llm_id, "agent_id": agent_id, "published": False})
        _write_resource_ids(resources)

    version = agent_response.get("version")
    if publish:
        if version is None:
            raise RetellError("Retell did not return the agent version; the draft was not published.")
        retell_request("POST", f"/publish-agent-version/{quote(agent_id, safe='')}", {
            "version": version,
            "version_title": "LAP qualification agent",
            "version_description": "Single-prompt LAP qualification agent configured from system_prompt.md",
        })

    result = {
        "llm_id": llm_id,
        "agent_id": agent_id,
        "agent_version": version,
        "published": publish,
        "agent_label": agent_label,
        "voice_id": voice_id,
        "languages": ["en-IN", "hi-IN"],
    }
    _write_resource_ids(result)
    return result


def _rag_context(args: argparse.Namespace) -> str:
    if args.rag_context_file:
        return Path(args.rag_context_file).read_text(encoding="utf-8")
    return os.environ.get("ADDITIONAL_CONTEXT_FROM_RAG", "")


def build_call_payload(args: argparse.Namespace, agent_id: str, from_number: str) -> dict[str, Any]:
    language = args.language
    if language not in {"English", "Hindi"}:
        raise RetellError("Language must be English or Hindi.")
    zone = ZoneInfo(os.environ.get("AGENT_TIMEZONE", "Asia/Kolkata"))
    now = datetime.now(zone)
    dynamic_variables = {
        "company_name": required_env("COMPANY_NAME"),
        "customer_name": args.customer_name,
        "agent_name": required_env("AGENT_NAME"),
        "agent_gender": args.agent_gender,
        "current_date": now.strftime("%Y-%m-%d"),
        "current_day": now.strftime("%A"),
        "current_time": now.strftime("%I:%M %p %Z"),
        "additional_context_from_rag": _rag_context(args),
        "language_to_speak": language,
        "conversation_history": "",
        "customer_utterance": "",
    }
    payload: dict[str, Any] = {
        "from_number": from_number,
        "to_number": args.to_number,
        "override_agent_id": agent_id,
        "retell_llm_dynamic_variables": dynamic_variables,
        "metadata": {"scenario": args.scenario or "manual-test"},
        "honor_internal_dnc": True,
        "idempotency_key": str(uuid4()),
    }
    return payload


def start_call(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_real_call:
        raise RetellError("No call placed. Rerun with --confirm-real-call to authorize this real outbound call.")
    customer_name = args.customer_name.strip()
    if not customer_name:
        raise RetellError("Customer name is required for verification.")
    agent_gender = args.agent_gender.strip()
    if not agent_gender:
        raise RetellError("Agent gender configuration is required.")
    resources = _resource_ids()
    agent_id = resources.get("agent_id") or os.environ.get("RETELL_AGENT_ID", "").strip()
    if not agent_id:
        raise RetellError("Provision the agent first or set RETELL_AGENT_ID.")
    from_number = required_env("RETELL_FROM_NUMBER")
    payload = build_call_payload(args, agent_id, from_number)
    return retell_request("POST", "/v2/create-phone-call", payload)


def list_voices() -> list[dict[str, Any]]:
    result = retell_request("GET", "/list-voices")
    if not isinstance(result, list):
        raise RetellError("Retell returned an unexpected voice-list response.")
    return result


def get_call(call_id: str) -> dict[str, Any]:
    return retell_request("GET", f"/v2/get-call/{quote(call_id, safe='')}")


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "LAP-Retell-Test-Exporter"})
    try:
        with urlopen(request, timeout=60) as response:
            destination.write_bytes(response.read())
    except (HTTPError, URLError) as exc:
        raise RetellError(f"Could not download a Retell call artifact: {exc}") from None


def export_call(call_id: str, scenario: str) -> dict[str, str]:
    record = get_call(call_id)
    transcript = record.get("transcript")
    recording_url = record.get("scrubbed_recording_url") or record.get("recording_url")
    if not transcript:
        raise RetellError("The call transcript is not available yet. Retry after the call ends and analysis completes.")
    if not recording_url:
        raise RetellError("Retell has no recording URL for this call. Check the agent data-storage settings.")

    safe_scenario = re.sub(r"[^A-Za-z0-9_-]+", "-", scenario.strip()).strip("-") or "call"
    destination = ARTIFACTS_PATH / f"{safe_scenario}-{call_id}"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "transcript.txt").write_text(transcript, encoding="utf-8")
    _download(recording_url, destination / "recording.wav")
    public_links = {
        key: record[key]
        for key in ("public_log_url", "recording_url", "scrubbed_recording_url")
        if record.get(key)
    }
    (destination / "public-links.json").write_text(json.dumps(public_links, indent=2) + "\n", encoding="utf-8")
    # Call responses include phone numbers and dynamic variables; keep this in
    # ignored local artifacts and do not print or commit it by default.
    (destination / "call-record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "artifact_directory": str(destination),
        "transcript_file": str(destination / "transcript.txt"),
        "recording_file": str(destination / "recording.wav"),
        "public_log_url": public_links.get("public_log_url", ""),
    }


def check_configuration() -> dict[str, Any]:
    prompt = load_prompt()
    return {
        "prompt_path": str(PROMPT_PATH),
        "prompt_characters": len(prompt),
        "required_variables": len(REQUIRED_PROMPT_VARIABLES),
        "section_order": list(range(1, 15)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retell provisioning and safe single-call test CLI for the LAP voice agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Validate the prompt and local setup without contacting Retell.")
    subparsers.add_parser("voices", help="List voices available to the configured Retell account.")
    provision_parser = subparsers.add_parser("provision", help="Create/update the Retell LLM and voice agent; publish the selected version.")
    provision_parser.add_argument("--draft-only", action="store_true", help="Do not publish the created/updated agent version.")
    call_parser = subparsers.add_parser("call", help="Place one real outbound test call (explicit confirmation required).")
    call_parser.add_argument("--to", dest="to_number", required=True, help="Customer/test actor phone number in E.164 format.")
    call_parser.add_argument("--customer-name", required=True)
    call_parser.add_argument("--agent-gender", default=os.environ.get("AGENT_GENDER", ""))
    call_parser.add_argument("--language", choices=("English", "Hindi"), default=os.environ.get("LANGUAGE_TO_SPEAK", "English"))
    call_parser.add_argument("--rag-context-file", help="Optional local text file injected as additional_context_from_rag.")
    call_parser.add_argument("--scenario", help="Scenario number/name for Retell call metadata.")
    call_parser.add_argument("--confirm-real-call", action="store_true", help="Required flag to place a real call.")
    export_parser = subparsers.add_parser("export-call", help="Export a completed call's transcript, recording, and log links.")
    export_parser.add_argument("--call-id", required=True)
    export_parser.add_argument("--scenario", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = check_configuration()
        elif args.command == "voices":
            result = [{key: voice.get(key) for key in ("voice_id", "voice_name", "provider", "gender", "accent", "age")}
                      for voice in list_voices()]
        elif args.command == "provision":
            result = provision_agent(publish=not args.draft_only)
        elif args.command == "call":
            result = start_call(args)
        elif args.command == "export-call":
            result = export_call(args.call_id, args.scenario)
        else:
            parser.error("Unknown command")
            return 2
    except (RetellError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
