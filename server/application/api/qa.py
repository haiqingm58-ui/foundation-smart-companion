from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..errors import APIError
from ..services.rag import call_llm, local_answer, search
from .dependencies import AuthContext, current_auth


router = APIRouter(tags=["qa"])


class QaInput(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    mode: str = Field(default="教材问答", pattern="^(教材问答|规范问答|学习辅导)$")
    useLlm: bool = True


@router.post("/api/qa")
def ask(body: QaInput, request: Request, _auth: AuthContext = Depends(current_auth)):
    with request.app.state.database.session() as session:
        sources = search(session, body.question, body.mode, 5)
    llm_answer = call_llm(request.app.state.settings, body.question, body.mode, sources) if body.useLlm else None
    answer = llm_answer or local_answer(body.question, sources)
    citations = [{"id": item["id"], "sourceType": item["sourceType"], "heading": item["heading"], "chapter": item.get("chapter"), "page": item.get("page"), "line": item.get("line"), "excerpt": item["text"][:260], "score": round(item["score"], 2)} for item in sources]
    return request.app.state.success(request, {"answer": answer, "sources": citations, "usedLlm": bool(llm_answer), "llmConfigured": bool(request.app.state.settings.llm_api_url and request.app.state.settings.llm_api_key)})
