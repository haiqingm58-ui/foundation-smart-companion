# Intelligent QA Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-turn QA demo with a responsive multi-turn learning workbench whose answers remain grounded in per-message RAG citations.

**Architecture:** Add bounded conversation history to the existing `/api/qa` contract and LLM prompt, while keeping retrieval and local fallback server-owned. Extract the student QA UI from `App.jsx` into a focused `QAWorkbench` component with an independent transcript, composer, and evidence rail; `App.jsx` supplies existing local search and fallback helpers only for offline degradation.

**Tech Stack:** React 19, lucide-react, Vitest, Testing Library, FastAPI, Pydantic, pytest, Playwright, Vite.

## Global Constraints

- Conversations live only for the current page session; do not add persisted chat history.
- Send at most the last six completed user/assistant messages to the server.
- Use a single `useLlm: true` send flow and preserve the existing RAG fallback.
- Never expose the provider key or private knowledge corpus in the browser.
- Render only source metadata returned by the API or present in the local index.
- Keep all mode labels visible on mobile and provide accessible names for icon actions.

---

### Task 1: Add Bounded Multi-Turn Context To The QA API

**Files:**
- Modify: `server/application/api/qa.py`
- Modify: `server/application/services/rag.py`
- Modify: `server/tests/test_rag.py`
- Modify: `server/tests/test_student.py`

**Interfaces:**
- Consumes: existing `POST /api/qa`, `search(...)`, `call_llm(...)`, and `local_answer(...)`.
- Produces: `QaInput.history: list[QaHistoryMessage]`, `contextual_query(question, history) -> str`, and `call_llm(..., history=None) -> str | None`.

- [ ] **Step 1: Write failing service tests for contextual retrieval and prompt history**

Add tests that assert a short follow-up query includes the most recent user question, a complete standalone query remains unchanged, and the provider payload labels conversation history as context rather than evidence:

```python
def test_contextual_query_uses_recent_user_turn_for_short_follow_up():
    history = [{"role": "user", "content": "桩侧阻力如何产生？"}, {"role": "assistant", "content": "与桩土相对位移有关。"}]
    assert contextual_query("它受什么影响？", history) == "桩侧阻力如何产生？ 它受什么影响？"

def test_contextual_query_keeps_standalone_question_unchanged():
    assert contextual_query("地基承载力特征值的主要影响因素有哪些？", []) == "地基承载力特征值的主要影响因素有哪些？"
```

Extend the mocked `call_llm` test to pass a two-message history and assert the request contains `对话上下文（仅用于理解指代，不作为知识依据）`.

- [ ] **Step 2: Run the focused backend tests and confirm they fail**

Run:

```bash
server/.venv/bin/pytest server/tests/test_rag.py -q
```

Expected: failure because `contextual_query` and the `history` argument do not exist.

- [ ] **Step 3: Implement bounded API history and contextual retrieval**

Add a strict message schema and pass only validated history:

```python
class QaHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

class QaInput(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    mode: str = Field(default="教材问答", pattern="^(教材问答|规范问答|学习辅导)$")
    useLlm: bool = True
    history: list[QaHistoryMessage] = Field(default_factory=list, max_length=6)
```

Convert messages with `model_dump()`, build `retrieval_query = contextual_query(body.question, history)`, search with that query, and call `call_llm(..., history)`.

In `rag.py`, use the latest prior user message only when the new question is short or contains a contextual phrase such as `它`, `这个`, `上述`, `为什么`, `再解释`, `还有`, or `那`. Add bounded, whitespace-normalized history to the current user prompt under an explicit non-evidence heading.

- [ ] **Step 4: Add API validation coverage**

Extend `test_student.py` so a request with six history messages succeeds and seven messages returns `422`:

```python
history = [{"role": "user" if index % 2 == 0 else "assistant", "content": f"消息 {index}"} for index in range(6)]
assert client.post("/api/qa", json={"question": "它为什么变化？", "history": history}, headers=CSRF).status_code == 200
assert client.post("/api/qa", json={"question": "它为什么变化？", "history": history + [{"role": "user", "content": "第七条"}]}, headers=CSRF).status_code == 422
```

- [ ] **Step 5: Run backend tests and commit**

Run:

```bash
server/.venv/bin/pytest server/tests/test_rag.py server/tests/test_student.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add server/application/api/qa.py server/application/services/rag.py server/tests/test_rag.py server/tests/test_student.py
git commit -m "feat: add contextual multi-turn QA"
```

### Task 2: Build The Multi-Turn QA Workbench Component

**Files:**
- Create: `src/pages/student/qa/QAWorkbench.jsx`
- Create: `src/pages/student/qa/QAWorkbench.test.jsx`
- Modify: `src/App.jsx`

**Interfaces:**
- Consumes: `askQa(payload) -> Promise<{answer, sources, usedLlm, llmConfigured}>`, `searchLocal(chunks, query, limit)`, and `buildFallbackAnswer(question, mode, sources, qaConfig)`.
- Produces: `<QAWorkbench ragChunks qaConfig backendStatus askQa searchLocal buildFallbackAnswer />`.

- [ ] **Step 1: Write failing component tests**

Cover the welcome state, one send flow, contextual second send, source selection, keyboard behavior, retry, and new conversation:

```jsx
const askQa = vi.fn()
  .mockResolvedValueOnce({ answer: "第一轮回答 [1]", sources: [sourceA], usedLlm: true, llmConfigured: true })
  .mockResolvedValueOnce({ answer: "第二轮回答 [1]", sources: [sourceB], usedLlm: true, llmConfigured: true });

render(<QAWorkbench askQa={askQa} ragChunks={[]} backendStatus="online" searchLocal={() => []} buildFallbackAnswer={() => "本地回答"} />);
fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "桩侧阻力如何产生？" } });
fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
expect(await screen.findByText("第一轮回答 [1]")).toBeInTheDocument();
fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "它受什么影响？" } });
fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
await waitFor(() => expect(askQa).toHaveBeenLastCalledWith(expect.objectContaining({ history: [
  { role: "user", content: "桩侧阻力如何产生？" },
  { role: "assistant", content: "第一轮回答 [1]" },
] })));
```

- [ ] **Step 2: Run the component test and confirm it fails**

Run:

```bash
npx vitest run src/pages/student/qa/QAWorkbench.test.jsx
```

Expected: failure because the component does not exist.

- [ ] **Step 3: Implement the workbench state and controls**

Create a component with:

```jsx
const [messages, setMessages] = useState([]);
const [draft, setDraft] = useState("");
const [mode, setMode] = useState("教材问答");
const [status, setStatus] = useState("idle");
const [activeMessageId, setActiveMessageId] = useState(null);
```

Store each assistant answer as `{ id, role: "assistant", content, sources, usedLlm, status }`. On send, append the user turn, pass the last six completed messages as history, call `askQa({ question, mode, useLlm: true, history })`, and append the assistant result. On failure, run the supplied local search and fallback function and label the result `本地教材索引`.

Render a compact header, welcome prompts, transcript toolbar, user/assistant messages, copy and retry icon buttons, suggested follow-up chips, a sticky textarea composer, and an evidence rail tied to `activeMessageId`. Use one send button and `Enter`/`Shift+Enter` behavior.

- [ ] **Step 4: Replace the legacy QAPage implementation**

Import `QAWorkbench` in `App.jsx`, keep a thin adapter, and remove `callFreeAi` use from the page:

```jsx
function QAPage({ ragChunks = [], qaConfig = defaultQaConfig, backendStatus = "offline" }) {
  return (
    <QAWorkbench
      ragChunks={ragChunks}
      qaConfig={qaConfig}
      backendStatus={backendStatus}
      askQa={(body) => apiRequest("/qa", { method: "POST", body })}
      searchLocal={searchChunks}
      buildFallbackAnswer={buildLocalRagAnswer}
    />
  );
}
```

- [ ] **Step 5: Run frontend tests and commit**

Run:

```bash
npx vitest run src/pages/student/qa/QAWorkbench.test.jsx
npm test
```

Expected: the focused test and the complete frontend suite pass.

Commit:

```bash
git add src/pages/student/qa/QAWorkbench.jsx src/pages/student/qa/QAWorkbench.test.jsx src/App.jsx
git commit -m "feat: build multi-turn QA workbench"
```

### Task 3: Add Responsive Workbench Styling And Browser Coverage

**Files:**
- Create: `src/pages/student/qa/QAWorkbench.css`
- Modify: `src/styles.css`
- Create: `tests/e2e/qa-workbench.spec.mjs`

**Interfaces:**
- Consumes: semantic class names and accessible labels from `QAWorkbench.jsx`.
- Produces: two-column desktop layout, stacked tablet layout, inline mobile evidence, and overflow assertions.

- [ ] **Step 1: Add a failing Playwright journey**

Authenticate with the existing `e2e-student-token`, open `/student/qa`, submit `桩侧阻力如何产生？`, then submit `它受什么影响？`. Assert two assistant answers, visible evidence, a single primary send action, and no horizontal overflow at `1440x1000`, `1024x900`, and `390x844`.

```js
await page.goto(`${APP_PATH}/student/qa`);
await page.getByLabel("输入问题").fill("桩侧阻力如何产生？");
await page.getByRole("button", { name: "发送问题" }).click();
await expect(page.locator(".qaAssistantMessage")).toHaveCount(1);
await expect(page.getByRole("complementary", { name: "回答依据" })).toContainText("桩侧阻力");
```

- [ ] **Step 2: Implement stable responsive styling**

Create a full-width workbench using:

```css
.qaWorkbenchGrid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 350px);
  min-height: clamp(620px, calc(100vh - 190px), 820px);
  gap: 16px;
}
```

Give the transcript `min-height: 0; overflow: auto`, keep the composer at the bottom, clamp excerpts, and use the existing blue/green/red design tokens. At `1100px`, stack the evidence rail below the conversation. At `640px`, reduce outer padding, keep mode labels visible, make the composer full width, and render the active evidence in a collapsible mobile section. Remove the now-unused `.qaShell`, `.bubble`, `.ragFlow`, `.sourceItem`, and `.askBox` rules from `styles.css`.

- [ ] **Step 3: Run component and browser tests**

Run:

```bash
npm test
npm run test:e2e -- tests/e2e/qa-workbench.spec.mjs
```

Expected: all frontend tests pass, the two-turn browser journey passes, and all viewport overflow assertions pass.

- [ ] **Step 4: Inspect screenshots and commit**

Inspect the desktop and mobile screenshots under `output/playwright/`. Confirm the transcript, evidence rail, textarea, mode selector, and source cards do not overlap or clip.

Commit:

```bash
git add src/pages/student/qa/QAWorkbench.css src/styles.css tests/e2e/qa-workbench.spec.mjs
git commit -m "style: refine responsive QA workbench"
```

### Task 4: Verify, Deploy, And Publish

**Files:**
- Modify only if verification reveals a scoped defect in the files above.

**Interfaces:**
- Consumes: completed backend, frontend, and responsive workbench changes.
- Produces: verified production release and synchronized GitHub `main`.

- [ ] **Step 1: Run the full quality gate**

Run:

```bash
npm run check
npm run test:e2e
git diff --check
```

Expected: frontend, backend, deploy, build, prerender, and browser tests all pass.

- [ ] **Step 2: Deploy to JDCloud**

Run:

```bash
npm run deploy:jdcloud
```

Expected: release activation succeeds and both public health and login checks pass.

- [ ] **Step 3: Verify production QA**

Confirm `GET /foundation-smart-companion/api/health` returns `status: ok` and `llmConfigured: true`. Log in as a student, ask a textbook question followed by a contextual follow-up, verify both answers render with citations, and confirm desktop/mobile screenshots have no runtime or API errors.

- [ ] **Step 4: Merge, push, and verify GitHub CI**

Merge the feature branch to `main`, push `origin main`, wait for the matching Actions run to complete successfully, then remove the owned worktree and merged feature branch.
