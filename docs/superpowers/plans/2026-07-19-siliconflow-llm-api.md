# SiliconFlow Large-Model API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the production course RAG endpoint to SiliconFlow's free `THUDM/GLM-Z1-9B-0414` model while preserving secure server-only credentials and local-answer fallback.

**Architecture:** Keep `POST /api/qa` as the only browser-facing interface. The FastAPI service retrieves five course chunks, calls SiliconFlow through the existing OpenAI-compatible client, validates the response shape, and returns either the model answer or the existing citation-backed local answer. Provider URL, key, and model remain in `/etc/foundation-smart-companion.env` so the provider can be changed without rebuilding.

**Tech Stack:** Python 3, FastAPI, urllib, pytest, React 19, systemd, Nginx, SiliconFlow OpenAI-compatible Chat Completions.

## Global Constraints

- The API key must exist only in `/etc/foundation-smart-companion.env` with mode `600` and must never be committed, returned to the browser, or printed in logs.
- The provider endpoint is `https://api.siliconflow.cn/v1/chat/completions`.
- The initial model is `THUDM/GLM-Z1-9B-0414`; it must remain environment-configurable because free-model availability can change.
- Retrieval remains mandatory before generation, and the external provider is not called when no source is found.
- Every provider error falls back to the existing local RAG answer and citations.
- Do not add a browser or administrator form for viewing or editing the API key.

## File Structure

- Create `server/tests/test_rag.py`: focused provider success and malformed-response regression tests.
- Modify `server/application/services/rag.py`: validate OpenAI-compatible response content before returning it.
- Modify `server/.env.example`: document the selected provider endpoint and model without a real key.
- Modify `README.md`: document SiliconFlow production values, key secrecy, and fallback behavior.

---

### Task 1: Harden The OpenAI-Compatible Provider Client

**Files:**
- Create: `server/tests/test_rag.py`
- Modify: `server/application/services/rag.py:91-117`

**Interfaces:**
- Consumes: `Settings`, `call_llm(settings, question, mode, sources)`.
- Produces: `_chat_content(payload: Any) -> str | None`; `call_llm` returns a stripped non-empty answer or `None` without raising on malformed provider data.

- [ ] **Step 1: Write the failing provider-response tests**

```python
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from server.application.config import Settings
from server.application.services.rag import call_llm


class FakeResponse:
    def __init__(self, payload: object):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        secret_key="test",
        data_dir=tmp_path,
        upload_dir=tmp_path / "uploads",
        session_ttl_seconds=3600,
        captcha_ttl_seconds=120,
        cookie_secure=False,
        cookie_path="/",
        llm_api_url="https://api.siliconflow.cn/v1/chat/completions",
        llm_api_key="test-key",
        llm_model="THUDM/GLM-Z1-9B-0414",
    )


SOURCES = [{"heading": "第3章 桩基础", "text": "桩侧阻力由桩土界面剪切作用发挥。"}]


@patch("server.application.services.rag.urllib.request.urlopen")
def test_call_llm_parses_siliconflow_chat_completion(urlopen, tmp_path: Path) -> None:
    urlopen.return_value = FakeResponse({"choices": [{"message": {"content": "  桩侧阻力由界面剪切发挥。[1]  "}}]})

    answer = call_llm(settings(tmp_path), "桩侧阻力如何发挥？", "教材问答", SOURCES)

    assert answer == "桩侧阻力由界面剪切发挥。[1]"
    request = urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://api.siliconflow.cn/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "THUDM/GLM-Z1-9B-0414"
    assert payload["stream"] is False


@patch("server.application.services.rag.urllib.request.urlopen")
def test_call_llm_returns_none_for_malformed_choices(urlopen, tmp_path: Path) -> None:
    urlopen.return_value = FakeResponse({"choices": []})

    assert call_llm(settings(tmp_path), "桩侧阻力如何发挥？", "教材问答", SOURCES) is None
```

- [ ] **Step 2: Run the tests to verify the malformed-response case fails**

Run:

```bash
server/.venv/bin/pytest server/tests/test_rag.py -q
```

Expected: the malformed-response test fails with `IndexError`, and the success test fails until `stream: false` and answer stripping are implemented.

- [ ] **Step 3: Implement strict response extraction and non-streaming requests**

Add above `call_llm`:

```python
def _chat_content(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()
```

Add `"stream": False` to the request payload and replace the direct nested `.get()` return with:

```python
        return _chat_content(data)
```

Retain the current bounded 25-second timeout and exception fallback.

- [ ] **Step 4: Run focused and API fallback tests**

Run:

```bash
server/.venv/bin/pytest server/tests/test_rag.py server/tests/test_student.py::test_rag_returns_ranked_citation_without_llm -q
```

Expected: all tests pass; the existing no-key path still returns a citation-backed local answer.

- [ ] **Step 5: Commit the provider client**

```bash
git add server/application/services/rag.py server/tests/test_rag.py
git commit -m "fix: harden SiliconFlow response handling"
```

---

### Task 2: Document The Production Provider Configuration

**Files:**
- Modify: `server/.env.example:10-14`
- Modify: `README.md:56-64`

**Interfaces:**
- Consumes: `FOUNDATION_LLM_API_URL`, `FOUNDATION_LLM_API_KEY`, and `FOUNDATION_LLM_MODEL` from `load_settings()`.
- Produces: a copy-safe configuration example containing no secret and matching the selected provider.

- [ ] **Step 1: Update the environment example**

Use these exact non-secret values:

```text
# Optional: SiliconFlow OpenAI-compatible chat completions endpoint.
# Keep the real key only in /etc/foundation-smart-companion.env with mode 600.
# If these are not set, /api/qa still returns a server-side RAG answer with citations.
FOUNDATION_LLM_API_URL=https://api.siliconflow.cn/v1/chat/completions
FOUNDATION_LLM_API_KEY=
FOUNDATION_LLM_MODEL=THUDM/GLM-Z1-9B-0414
```

- [ ] **Step 2: Update the README configuration block**

Replace the generic endpoint and model with:

```bash
FOUNDATION_LLM_API_URL=https://api.siliconflow.cn/v1/chat/completions
FOUNDATION_LLM_API_KEY=your-server-only-api-key
FOUNDATION_LLM_MODEL=THUDM/GLM-Z1-9B-0414
```

Add one sentence stating that free models and rate limits can change, so production operators should verify SiliconFlow pricing before changing the model.

- [ ] **Step 3: Verify documentation consistency and secret hygiene**

Run:

```bash
rg -n "api.siliconflow.cn/v1/chat/completions|THUDM/GLM-Z1-9B-0414" README.md server/.env.example
git grep -nE "sk-[A-Za-z0-9_-]{16,}|FOUNDATION_LLM_API_KEY=[^<y[:space:]]" -- . ':!docs/superpowers/plans/*'
```

Expected: both files contain the endpoint and model; the secret scan returns no real key.

- [ ] **Step 4: Commit the configuration documentation**

```bash
git add README.md server/.env.example
git commit -m "docs: configure SiliconFlow model endpoint"
```

---

### Task 3: Provision The Server-Only API Key

**Files:**
- Modify on server: `/etc/foundation-smart-companion.env`

**Interfaces:**
- Consumes: a newly created SiliconFlow API key supplied through a private interactive flow.
- Produces: three non-empty `FOUNDATION_LLM_*` values loaded by `foundation-smart-companion-api.service`.

- [ ] **Step 1: Create the key in the official SiliconFlow console**

Open `https://cloud.siliconflow.cn/account/ak`, sign in, create a dedicated key named `foundation-smart-companion-production`, and keep the key out of the repository and chat transcript.

- [ ] **Step 2: Back up and update the production environment file**

Install a temporary root-owned helper, then run it in an interactive SSH session so the key is entered with terminal echo disabled. The helper backs up the file, replaces only the three LLM values, preserves every unrelated variable, and restores root-only permissions:

```bash
ssh jdcloud 'sudo tee /tmp/configure-foundation-llm >/dev/null && sudo chmod 700 /tmp/configure-foundation-llm' <<'REMOTE'
#!/usr/bin/env bash
set -Eeuo pipefail
env_file=/etc/foundation-smart-companion.env
cp -a "$env_file" "${env_file}.before-llm-$(date +%Y%m%d%H%M%S)"
read -rsp 'SiliconFlow API key: ' FOUNDATION_NEW_LLM_KEY
printf '\n'
export FOUNDATION_NEW_LLM_KEY
python3 - <<'PY'
import os
from pathlib import Path

path = Path("/etc/foundation-smart-companion.env")
updates = {
    "FOUNDATION_LLM_API_URL": "https://api.siliconflow.cn/v1/chat/completions",
    "FOUNDATION_LLM_API_KEY": os.environ.pop("FOUNDATION_NEW_LLM_KEY"),
    "FOUNDATION_LLM_MODEL": "THUDM/GLM-Z1-9B-0414",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
result = []
for line in lines:
    name = line.split("=", 1)[0] if "=" in line else ""
    if name in updates:
        result.append(f"{name}={updates[name]}")
        seen.add(name)
    else:
        result.append(line)
for name, value in updates.items():
    if name not in seen:
        result.append(f"{name}={value}")
path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
unset FOUNDATION_NEW_LLM_KEY
chmod 600 "$env_file"
chown root:root "$env_file"
REMOTE
ssh -tt jdcloud 'sudo /tmp/configure-foundation-llm; status=$?; sudo rm -f /tmp/configure-foundation-llm; exit $status'
```

- [ ] **Step 3: Verify configuration presence without printing values**

Run:

```bash
ssh jdcloud 'sudo awk -F= '\''/^FOUNDATION_LLM_/ {value=substr($0,index($0,"=")+1); print $1 "=" (length(value) ? "<set>" : "<empty>")} '\'' /etc/foundation-smart-companion.env; sudo stat -c "%a %U:%G" /etc/foundation-smart-companion.env'
```

Expected: URL, key, and model each show `<set>`; permissions show `600 root:root`.

- [ ] **Step 4: Run a provider smoke test from JDCloud**

Load the environment root-side and send one short Chat Completions request. The script prints only the HTTP status, returned model, and whether answer content is non-empty:

```bash
ssh jdcloud "sudo bash -lc 'set -a; source /etc/foundation-smart-companion.env; set +a; python3 -'" <<'PY'
import json
import os
import urllib.request

payload = json.dumps({
    "model": os.environ["FOUNDATION_LLM_MODEL"],
    "messages": [{"role": "user", "content": "只回答：接口连接成功"}],
    "stream": False,
    "max_tokens": 32,
}, ensure_ascii=False).encode("utf-8")
request = urllib.request.Request(
    os.environ["FOUNDATION_LLM_API_URL"],
    data=payload,
    headers={
        "Authorization": f"Bearer {os.environ['FOUNDATION_LLM_API_KEY']}",
        "Content-Type": "application/json",
    },
    method="POST",
)
with urllib.request.urlopen(request, timeout=25) as response:
    data = json.loads(response.read().decode("utf-8"))
content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
print(json.dumps({
    "status": 200,
    "model": data.get("model"),
    "hasContent": bool(content.strip()),
}, ensure_ascii=False))
PY
```

Expected: HTTP 200 and non-empty answer content.

---

### Task 4: Deploy And Verify End To End

**Files:**
- Verify: production service, health endpoint, student question-answering page

**Interfaces:**
- Consumes: Tasks 1-3 and the existing zero-downtime JDCloud deployment script.
- Produces: production `/api/qa` responses with `usedLlm: true` and preserved citations.

- [ ] **Step 1: Run the full local quality gate**

Run:

```bash
npm run check
```

Expected: Vitest, backend pytest, deployment tests, Vite build, and prerender all pass.

- [ ] **Step 2: Deploy the committed release**

Run:

```bash
npm run deploy:jdcloud
```

Expected: a new atomic source/web release is activated, migrations and imports complete, the API service restarts, and the public health and login checks pass.

- [ ] **Step 3: Confirm the model is configured publicly without exposing it**

Run:

```bash
curl -fsS http://111.228.5.243/foundation-smart-companion/api/health
```

Expected: `status` is `ok`, `llmConfigured` is `true`, and the response contains no API key.

- [ ] **Step 4: Verify authenticated RAG generation in the browser**

Log in as an existing student, open `智能问答`, select `教材问答`, ask `桩侧阻力是如何发挥的？`, and submit with large-model generation enabled.

Expected: the page identifies the answer as server-side model generation, the answer contains course-specific content, at least one citation is visible, and the network response has `usedLlm: true`.

- [ ] **Step 5: Verify fallback with an invalid key in an isolated test process**

Run the focused unit and API fallback tests rather than changing the production key:

```bash
server/.venv/bin/pytest server/tests/test_rag.py server/tests/test_student.py::test_rag_returns_ranked_citation_without_llm -q
```

Expected: malformed-provider and no-key cases return `None` from `call_llm`, while `/api/qa` returns the local answer and citations.

- [ ] **Step 6: Push the verified commits**

```bash
git push origin main
```

Expected: `origin/main` advances to the verified production commit and GitHub Actions succeeds.
