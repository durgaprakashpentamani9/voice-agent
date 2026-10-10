# Home Credit LAP voice agent

This project contains the system prompt, a local policy mirror with unit tests, and a small Python CLI for provisioning and operating the agent through Retell's API. The prompt is the runtime instruction for the agent. `lap_agent/qualification.py` is a deterministic local test model; it does not parse speech and is not connected to Retell's live conversation runtime.

## Local validation

Use Python 3.10 or newer. No third-party Python package is required.

On Windows, use the Python launcher (`py`) so the Microsoft Store `python`
execution alias does not intercept the command:

```powershell
py -3 retell_app.py check
py -3 -m unittest discover -s tests -v
```

If `py -3` is also unavailable, install Python 3.10 or newer from
python.org and enable the Python Launcher during installation. Alternatively,
turn off the `python.exe` and `python3.exe` App Execution Aliases in Windows
Settings, then open a new terminal and use `python`.

These checks do not contact Retell, place calls, or generate recordings.

## Retell account setup

1. In the Retell dashboard, create an API key from the API Keys area. Copy `.env.example` to `.env` and set `RETELL_API_KEY` there. Keep `.env` private; it is ignored by Git.
2. In Retell's voice library/dashboard, select a professional voice that supports both English (India) and Hindi (India). Set its exact voice ID as `RETELL_VOICE_ID`. Voice compatibility and availability depend on the Retell account and selected provider; the script does not guess a voice ID.
3. Configure `RETELL_AGENT_LABEL`, `COMPANY_NAME`, `AGENT_NAME`, and `AGENT_GENDER`. The gender value must match the voice/persona used by the prompt. Set `RETELL_FROM_NUMBER` to an outbound-enabled Retell number in E.164 format. Retell account access, a usable number, permissions, and calling credits may be needed.
4. Optionally set `ADDITIONAL_CONTEXT_FROM_RAG` only to approved retrieved product content. Do not add rates, fees, thresholds, or other product claims without an authorized source.
5. Run `py -3 retell_app.py voices` to inspect voices available to the connected account. Run `py -3 retell_app.py provision` to create or update the Retell LLM and voice agent and publish the returned version. The created IDs are saved to the ignored `retell-resources.json`. Use `--draft-only` to omit publishing.

The provision command uses `system_prompt.md` as the Retell LLM prompt, configures the English India and Hindi India locales, enables Retell DNC detection, and uses the configured voice ID. Review the draft and account settings in Retell before calling customers. This repository does not contain a configured account, voice selection, or API credential.

## Test calls and saved artifacts

Use only a number you are authorized to call (for example, a test actor). Start one explicitly authorized real outbound call:

```powershell
py -3 retell_app.py call --to +91XXXXXXXXXX --customer-name "Test Customer" --agent-gender "<configured gender>" --language English --scenario "01-perfect" --confirm-real-call
```

Use `--language Hindi` for a Hindi test. Configure both prompt identity fields in `.env`. The CLI will not place a call unless `--confirm-real-call` is present. To run the 24 audio scenarios, make a separate call for each scenario using the customer lines in `test_scenarios.md`; these calls and their recording/transcript capture require the Retell account and a reachable test phone.

After a completed call has a transcript and recording available, export them with:

```powershell
py -3 retell_app.py export-call --call-id CALL_ID_FROM_RETELL --scenario 01-perfect
```

The CLI saves the transcript, recording, call JSON, and any Retell public log/recording links under `artifacts/`, which is ignored by Git because call records can contain personal data. Signed public links are enabled by default and may expire according to Retell's link policy. No call recordings, transcripts, or public links have been created by local setup or unit tests.

## Limits

The local automated tests exercise qualification and branch decisions on normalized facts. They do not test speech recognition, Hindi gendered inflection, voice quality, model behavior, actual handoffs, callbacks, or the Retell API. Real platform validation requires configured Retell credentials and voice/phone resources, plus separate human-reviewed test calls. The CLI provisions a prompt-driven agent; the deterministic local model is not deployed as a custom Retell tool.
