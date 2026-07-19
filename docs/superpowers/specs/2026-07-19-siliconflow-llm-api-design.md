# SiliconFlow Large-Model API Integration Design

## Goal

Connect the production RAG question-answering flow to SiliconFlow's OpenAI-compatible Chat Completions API. The platform must continue to answer from retrieved course material when the external model is unavailable.

## Selected Provider

- Provider: SiliconFlow domestic endpoint
- Endpoint: `https://api.siliconflow.cn/v1/chat/completions`
- Initial model: `THUDM/GLM-Z1-9B-0414`
- Authentication: provider API key stored only on the production server

The model is selected from SiliconFlow's currently free text-generation models. Model availability and pricing may change, so the model name remains an environment variable rather than a code constant.

## Architecture And Data Flow

1. An authenticated student submits a question to `POST /api/qa` with a question mode.
2. The server searches textbook, standard, and teacher-uploaded chunks according to that mode.
3. The five highest-scoring chunks are formatted as numbered context and sent to SiliconFlow.
4. The model is instructed to answer only from that context and cite the numbered sources.
5. The API response returns the generated answer, structured citations, `usedLlm`, and `llmConfigured`.
6. If retrieval finds no evidence, no external request is made. If the provider times out, rejects the request, or returns an invalid payload, the server returns the existing local RAG answer with citations.

## Production Configuration

The following values live in `/etc/foundation-smart-companion.env`, which remains mode `600` and is loaded by `foundation-smart-companion-api.service`:

```text
FOUNDATION_LLM_API_URL=https://api.siliconflow.cn/v1/chat/completions
FOUNDATION_LLM_API_KEY=<server-only secret>
FOUNDATION_LLM_MODEL=THUDM/GLM-Z1-9B-0414
```

The key must never be committed, rendered in the browser, returned by a health endpoint, or written to logs. The public health response may expose only the boolean `llmConfigured`.

## Reliability And Error Handling

- Keep a bounded provider timeout so a slow model cannot hold the student interface indefinitely.
- Treat HTTP failures, timeouts, malformed JSON, and missing answer content as provider failures.
- Preserve the local RAG fallback and source citations for every provider failure.
- Do not retry automatically inside a single student request; this avoids duplicate cost and long waits.
- Keep the provider URL and model configurable so a discontinued free model can be replaced without rebuilding the site.

## Verification

The production rollout is accepted only when all of the following pass:

1. The service is active and `/api/health` reports `llmConfigured: true` without exposing secrets.
2. A direct provider request from the JDCloud host returns a valid Chat Completions response.
3. An authenticated textbook question returns `usedLlm: true`, a non-empty answer, and at least one course citation.
4. A simulated invalid provider configuration returns `usedLlm: false` and a usable local RAG answer.
5. The browser question-answering page displays the generated answer and citations without console or API errors.

## Scope

This change connects the existing RAG pipeline to a model; it does not move secrets into an administrator form, add billing, or allow students and teachers to select arbitrary providers. Provider administration remains a server operation because the key is production infrastructure data.
