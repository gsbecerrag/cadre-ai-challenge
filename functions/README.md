# Firebase Functions — the Triage Agent

Python gen2. One function: `triage_on_feedback_written` fires on every write to
`feedback/{feedback_id}` and, when the rating is `down`, writes a Triage Report to
`triage_reports/{feedback_id}` and posts the summary to the Trace (ADR-0005).

`main.py` is the trigger and nothing else. The agent is `core/triage.py`, which takes the
`ConversationStore`, the `ModelProvider`, the `Tracer` and the Knowledge Base as arguments and
is tested at seam S3 in `core/tests/test_triage.py` with a fake event, the in-memory store and
the stub provider. Nothing here is tested, because there is nothing here to test.

## Deploy

```
make deploy-functions
```

It rsyncs `core/` and `knowledge/` into this directory (both are gitignored here — the copy is
the repository's own source, not a fork of it) and runs
`firebase deploy --only functions --project cadre-ai-challenge`. The copy is why the triage
call's cached prompt prefix is byte-identical to the chat's, and therefore why it lands on the
cache a conversation just paid to write.

Prerequisites, once per project:

- `make deploy-secrets` — the function declares `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`
  and `LANGFUSE_SECRET_KEY` in `SECRETS`; `firebase-functions` reads those as Secret Manager
  secret **ids** and binds each to an environment variable of the same name, so the id has to
  be spelled the way an environment variable is. Cloud Run's own bindings use hyphenated ids
  (`openrouter-api-key`, …), which a function cannot name — so `deploy-secrets` copies each
  one into a second secret under the function-shaped id when that id does not exist yet, and
  grants the runtime service account read access to all of them. It never prints a value.

  The copy is a copy, not a link: **rotating `openrouter-api-key` does not update
  `OPENROUTER_API_KEY`.** Add a version to both, or delete the function-shaped secret and run
  `make deploy-secrets` again.
- The Firestore database and the function must share a region: both are `us-central1`
  (a `nam5` multi-region database serves `us-central1` triggers).
- `firebase experiments:enable pythonfunctions` on Firebase CLI versions where Python
  functions are still behind the flag.

Model and everything else non-secret come from `core/config.py`'s defaults —
`TRIAGE_MODEL` falls back to `CHAT_MODEL`, which is Claude Sonnet 5. To override either
without a code change, put it in `functions/.env` (the Firebase CLI loads it; it is
gitignored, like every other dotenv in this repository).

## Locally, against the emulator

```
make deploy-functions COPY_ONLY=1          # rsync core/ and knowledge/ in, deploy nothing
cd functions && python3 -m venv venv && venv/bin/pip install -r requirements.txt
firebase emulators:start --only functions,firestore --project cadre-ai-challenge
```

Then, in another shell, write a Feedback document into the emulated Firestore — the trigger
fires on the write:

```
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 \
  uv run python scripts/write-feedback.py --rating down
```

With `MODEL_PROVIDER` unset the function still calls OpenRouter (the emulator emulates
Firestore, not the model), so either export a real `OPENROUTER_API_KEY` or expect the report
to be the provider's failure line in the emulator log. The report lands in the emulated
`triage_reports` collection, which the emulator UI shows at <http://127.0.0.1:4000/firestore>.
