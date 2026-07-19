# Intelligent QA Workbench Design

## Goal

Turn the current single-question RAG demo into a calm, professional learning workbench. Students should be able to ask follow-up questions, understand whether the large model is available, and inspect the textbook evidence without the page becoming crowded.

## Selected Direction

The page uses a conversation-first, two-column workbench:

- The main column contains the multi-turn transcript and a persistent composer.
- The right rail contains the evidence for the currently selected assistant answer.
- The existing course navigation remains unchanged; no additional history sidebar is added.
- Conversations live for the current page session. Server-side saved history is outside this change.

This keeps the interface focused while preserving the academic traceability that distinguishes the platform from a general chatbot.

## Information Architecture

### Compact Page Header

The header keeps the title `智能问答` and a short description. A restrained connection badge reports one of three states: large model connected, RAG-only fallback, or server offline. The long blue notice is removed.

### Conversation Panel

The transcript is the visual center of the page. It contains:

- A welcome state with three short example questions when no conversation exists.
- User messages aligned to the right.
- Assistant messages aligned to the left with an assistant identity, generation state, answer text, source count, copy action, and retry action.
- Suggested follow-up questions derived from the active mode and latest question.
- A visible loading message while the server is answering.
- A clear, inline failure state that preserves the student's draft.

The transcript scrolls independently on desktop so the composer remains reachable. Messages use restrained surfaces instead of oversized chat bubbles.

### Composer

The composer is fixed to the bottom of the conversation panel and contains:

- A compact segmented control for `教材问答`, `规范问答`, and `学习辅导`.
- An auto-growing textarea that supports multi-line questions.
- One primary send button with a familiar send icon.
- `Enter` sends and `Shift+Enter` inserts a new line.
- A `新对话` command in the panel toolbar clears the current session after a lightweight confirmation when messages exist.

The former separate `检索` and `AI生成` buttons are replaced by one request using `useLlm: true`. The server remains responsible for falling back to RAG when the provider is unavailable.

### Evidence Rail

The right rail is titled `回答依据` and always reflects the latest assistant message. It contains:

- A small summary showing the current mode and number of retrieved sources.
- Source cards with document title, chapter path, excerpt, source type, and source location.
- An expand/collapse control for longer excerpts.
- A compact retrieval status section instead of the current four-step RAG banner.
- A useful empty state before the first answer.

No fake knowledge points or page numbers are invented. The interface renders only metadata returned by the API or present in the local index.

## Multi-Turn Data Flow

1. The frontend stores an ordered array of user and assistant messages for the active page session.
2. A new question is sent to `POST /api/qa` with the active mode, `useLlm: true`, and up to the last six completed messages as optional history.
3. The server validates and bounds the history. It uses recent context to resolve follow-up wording while retrieving evidence primarily for the newest question.
4. The server adds the bounded conversation context to the model prompt, while continuing to require answers grounded in retrieved course sources.
5. The response is stored with its own source snapshot so selecting an earlier assistant answer restores the evidence that supported it.
6. If the large model fails, the existing server RAG answer and citations remain visible in the same message shape.

History is never sent to the provider without passing through the server. No API key or private textbook corpus is exposed to the browser.

## Responsive Behavior

- At wide desktop widths, the workbench uses a flexible main column and a 320-360px evidence rail.
- At tablet widths, the evidence rail moves below the conversation while retaining clear separation.
- On phones, sources open as an inline collapsible section under each assistant answer, the composer spans the viewport width, and mode labels remain visible.
- Stable minimum heights and grid constraints prevent loading text, long citations, or controls from shifting the layout.

## Accessibility

- The transcript uses an `aria-live="polite"` region for generated answers and errors.
- Icon-only actions have explicit accessible names and tooltips.
- All mode, source, copy, retry, and send controls are keyboard accessible.
- Focus-visible styling remains clear.
- Loading and connection states are communicated with text, not color alone.

## Error Handling

- Empty questions do not send.
- Duplicate sends are blocked while a request is active.
- A failed request leaves the question and draft recoverable and offers retry.
- Malformed or missing sources render as an answer without an evidence count rather than breaking the page.
- Local RAG fallback is labeled accurately and never presented as a large-model response.

## Testing And Acceptance

The change is complete when:

1. A student can send a question and a contextual follow-up in the same session.
2. Each assistant message preserves and reopens its own source list.
3. The single send flow displays large-model, RAG fallback, loading, and error states correctly.
4. New conversation clears the transcript and returns to the welcome state.
5. Enter and Shift+Enter behave as documented.
6. Desktop, tablet, and mobile layouts have no overlap or clipped text.
7. Existing RAG fallback behavior and API authentication remain intact.
8. Frontend tests, backend tests, production build, and browser journeys pass.

## Scope

This change redesigns the student QA page and adds bounded session-based multi-turn context. It does not add server-persisted chat history, teacher review queues, voice input, file attachments, arbitrary model selection, or a new navigation module.
