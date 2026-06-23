from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[1]
SERVER_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("FOUNDATION_DATA_DIR", SERVER_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("FOUNDATION_DB_PATH", DATA_DIR / "app.db"))
SECRET_KEY = os.getenv("FOUNDATION_SECRET_KEY", "change-me-before-production")
TOKEN_TTL_SECONDS = int(os.getenv("FOUNDATION_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
LLM_API_URL = os.getenv("FOUNDATION_LLM_API_URL", "").strip()
LLM_API_KEY = os.getenv("FOUNDATION_LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("FOUNDATION_LLM_MODEL", "gpt-4o-mini").strip()

DEMO_USERS = [
    {
        "id": "student-zhang",
        "role": "student",
        "roleLabel": "学生",
        "name": "张同学",
        "username": "student",
        "password": "123456",
        "studentNo": "20220001",
        "college": "土木工程学院",
        "school": "某某大学",
        "mentor": "李老师",
    },
    {
        "id": "teacher-li",
        "role": "teacher",
        "roleLabel": "指导老师",
        "name": "李老师",
        "username": "teacher",
        "password": "123456",
        "studentNo": "T-001",
        "college": "土木工程学院",
        "school": "某某大学",
        "mentor": "课程负责人",
    },
    {
        "id": "admin-root",
        "role": "admin",
        "roleLabel": "管理员",
        "name": "管理员",
        "username": "admin",
        "password": "123456",
        "studentNo": "ADMIN",
        "college": "教务与资源中心",
        "school": "某某大学",
        "mentor": "平台运维",
    },
]

DEFAULT_QA_CONFIG = {
    "teacherInstruction": "回答时优先引用教材原文，涉及规范条文时提示学生以指导老师确认版本为准。",
    "answerStyle": "先给结论，再列关键依据，最后给复习建议。",
    "reviewRule": "低置信度答案和计算题高分答案建议教师复核。",
}


app = FastAPI(title="Foundation Smart Companion API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginBody(BaseModel):
    username: str
    password: str


class DocumentBody(BaseModel):
    title: str = Field(default="课堂补充资料")
    text: str
    sourceType: str = Field(default="teacher-paste")


class QaBody(BaseModel):
    question: str
    mode: str = Field(default="教材问答")
    useLlm: bool = Field(default=True)


class ExerciseImportBody(BaseModel):
    exercises: list[dict[str, Any]] | None = None
    items: list[dict[str, Any]] | None = None


class QaConfigBody(BaseModel):
    teacherInstruction: str
    answerStyle: str
    reviewRule: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return salt, base64.urlsafe_b64encode(digest).decode("ascii")


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    _, candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


def b64_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(user: dict[str, Any]) -> str:
    payload = b64_json({"sub": user["id"], "role": user["role"], "exp": int(time.time()) + TOKEN_TTL_SECONDS})
    return f"{payload}.{sign(payload)}"


def parse_token(token: str) -> dict[str, Any]:
    try:
        payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, sign(payload)):
            raise ValueError("bad signature")
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return data
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "role": row["role"],
        "roleLabel": row["role_label"],
        "name": row["name"],
        "username": row["username"],
        "studentNo": row["student_no"],
        "college": row["college"],
        "school": row["school"],
        "mentor": row["mentor"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token_data = parse_token(authorization.split(" ", 1)[1].strip())
    with db() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (token_data["sub"],)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return row_to_user(row)


def require_manager(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher or admin role required")
    return user


def clean_uploaded_text(text: str) -> str:
    return (
        text.replace("\r", "")
        .replace("\\n", "\n")
        .replace("\ufeff", "")
        .strip()
    )


def normalize_document_title(name: str) -> str:
    return re.sub(r"\.(md|markdown|txt|json)$", "", name, flags=re.I)[:42] or "补充资料"


def chunk_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    text = clean_uploaded_text(document.get("text") or "")
    if not text:
        return []
    chunks: list[dict[str, Any]] = []
    heading = document["title"]
    buffer: list[str] = []
    start_line = 1
    lines = text.split("\n")

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        chunk_text = clean_uploaded_text("\n".join(buffer))
        if len(chunk_text) >= 18:
            chunks.append(
                {
                    "id": f"upload:{document['id']}:{len(chunks) + 1}",
                    "kind": "teacher-upload",
                    "sourceType": document.get("sourceType", "teacher-upload"),
                    "documentTitle": document["title"],
                    "text": chunk_text,
                    "source_line": start_line,
                    "end_line": end_line,
                    "heading_path": f"{document['title']} > {heading}" if heading != document["title"] else document["title"],
                }
            )
        buffer = []
        start_line = end_line + 1

    for index, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if match:
            flush(index - 1)
            heading = match.group(2).strip()[:80]
            start_line = index + 1
            continue
        buffer.append(line)
        current = "\n".join(buffer)
        if len(current) >= 620 or (not line.strip() and len(current) >= 360):
            flush(index)
    flush(len(lines))
    return chunks


def keyword_terms(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text or "")
    stop = set("的是了和与及或在有为对中下上其要能可")
    terms: set[str] = set()
    for index in range(len(compact)):
        for size in range(2, 7):
            term = compact[index : index + size]
            if len(term) == size and not all(char in stop for char in term):
                terms.add(term)
    return sorted(terms, key=lambda item: (-len(item), item))


def compact_text(text: str, limit: int = 260) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:limit] + "..." if len(clean) > limit else clean


def load_base_chunks() -> list[dict[str, Any]]:
    path = ROOT_DIR / "public" / "knowledge" / "chunks.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


BASE_CHUNKS = load_base_chunks()


def uploaded_chunks() -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    documents = [
        {
            "id": row["id"],
            "title": row["title"],
            "text": row["text"],
            "sourceType": row["source_type"],
            "uploadedAt": row["uploaded_at"],
        }
        for row in rows
    ]
    return [chunk for document in documents for chunk in chunk_document(document)]


def search_chunks(query: str, chunks: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    terms = keyword_terms(query)
    if not terms:
        return []
    anchor_terms = [
        term
        for term in ["桩侧阻力", "桩端阻力", "摩阻力", "浅基础", "深基础", "地基", "基础", "沉降", "承载力", "基坑", "土压力", "负摩阻力"]
        if term in query
    ]
    scored: list[dict[str, Any]] = []
    for chunk in chunks:
        haystack = f"{chunk.get('heading_path', '')}\n{chunk.get('text', '')}"
        score = sum(len(term) for term in terms if term in haystack)
        anchor_hits = sum(1 for term in anchor_terms if term in haystack)
        anchor = anchor_hits * 26 if anchor_terms and anchor_hits else (-50 if anchor_terms else 0)
        length_bonus = 4 if len(chunk.get("text", "")) > 80 else 0
        total = score + anchor + length_bonus
        if total > 0:
            next_chunk = dict(chunk)
            next_chunk["score"] = total
            scored.append(next_chunk)
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def build_local_answer(question: str, mode: str, sources: list[dict[str, Any]], qa_config: dict[str, str]) -> str:
    if not sources:
        return "暂时没有检索到足够相关的教材或教师上传资料。可以换一个更具体的关键词继续提问。"
    top = sources[0]
    concepts = [term for term in keyword_terms(question) if term in top.get("text", "") or term in top.get("heading_path", "")][:5]
    mode_lead = {
        "规范问答": "按规范问答的口径，先定位相关教材和关联资料；正式条文编号以指导老师确认版本为准。",
        "学习辅导": "按学习辅导的口径，先抓教材关键说法，再用练习题验证掌握度。",
    }.get(mode, "按教材问答的口径，当前最相关的依据如下。")
    support = "\n".join(
        f"{index + 1}. {compact_text(item.get('text', ''), 150)}（{item.get('heading_path') or item.get('documentTitle') or '教材资料'}）"
        for index, item in enumerate(sources[:3])
    )
    concept_line = "、".join(concepts) if concepts else "建议结合检索片段中的术语继续追问"
    return "\n".join(
        [
            mode_lead,
            "",
            f"直接回答：{compact_text(top.get('text', ''), 260)}",
            f"关键概念：{concept_line}",
            f"复习提醒：{qa_config.get('answerStyle', DEFAULT_QA_CONFIG['answerStyle'])}",
            "",
            f"引用依据：\n{support}",
        ]
    )


def call_llm(question: str, mode: str, sources: list[dict[str, Any]], qa_config: dict[str, str]) -> str | None:
    if not LLM_API_URL or not LLM_API_KEY:
        return None
    context = "\n".join(
        f"{index + 1}. {item.get('heading_path', '')} L{item.get('source_line', '')}: {compact_text(item.get('text', ''), 420)}"
        for index, item in enumerate(sources)
    )
    prompt = "\n".join(
        [
            "你是《基础工程》课程的智慧学伴。请严格基于检索片段回答。",
            f"问答模式：{mode}",
            f"指导老师要求：{qa_config.get('teacherInstruction', '')}",
            f"学生问题：{question}",
            "检索片段：",
            context or "暂无检索片段。",
            "请用中文回答，包含：直接回答、关键依据、复习提醒。不要编造规范条文编号。",
        ]
    )
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是严谨的土木工程课程助教。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        LLM_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LLM_API_KEY}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=18) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
        return data.get("choices", [{}])[0].get("message", {}).get("content")
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def get_qa_config() -> dict[str, str]:
    with db() as connection:
        rows = connection.execute("SELECT key, value FROM settings WHERE key LIKE 'qa.%'").fetchall()
    config = dict(DEFAULT_QA_CONFIG)
    for row in rows:
        config[row["key"].replace("qa.", "", 1)] = row["value"]
    return config


def normalize_imported_exercise(item: dict[str, Any], index: int) -> dict[str, Any] | None:
    text = str(item.get("text") or item.get("title") or item.get("question") or "").strip()
    if not text:
        return None
    return {
        "id": item.get("id") or f"custom-exercise-{int(time.time())}-{index}",
        "number": item.get("number") or f"导入-{index + 1}",
        "chapter": item.get("chapter") or "第3章 桩基础",
        "chapterNo": item.get("chapterNo"),
        "type": item.get("type") or "思考题",
        "kind": item.get("kind") or "教师导入",
        "difficulty": item.get("difficulty") or "基础",
        "text": text,
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else ["教师导入"],
        "answer": item.get("answer"),
        "attachments": item.get("attachments") if isinstance(item.get("attachments"), list) else [],
        "sourceLine": item.get("sourceLine") or "teacher-import",
    }


def init_db() -> None:
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              password_salt TEXT NOT NULL,
              role TEXT NOT NULL,
              role_label TEXT NOT NULL,
              name TEXT NOT NULL,
              student_no TEXT NOT NULL,
              college TEXT NOT NULL,
              school TEXT NOT NULL,
              mentor TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              text TEXT NOT NULL,
              source_type TEXT NOT NULL,
              uploaded_by TEXT NOT NULL,
              uploaded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exercises (
              id TEXT PRIMARY KEY,
              payload TEXT NOT NULL,
              source TEXT NOT NULL,
              created_by TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        user_count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        if user_count == 0:
            for user in DEMO_USERS:
                salt, password_hash = hash_password(user["password"])
                connection.execute(
                    """
                    INSERT INTO users
                    (id, username, password_hash, password_salt, role, role_label, name, student_no, college, school, mentor, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        user["username"],
                        password_hash,
                        salt,
                        user["role"],
                        user["roleLabel"],
                        user["name"],
                        user["studentNo"],
                        user["college"],
                        user["school"],
                        user["mentor"],
                        now_iso(),
                    ),
                )
        exercise_count = connection.execute("SELECT COUNT(*) AS count FROM exercises").fetchone()["count"]
        if exercise_count == 0:
            path = ROOT_DIR / "public" / "knowledge" / "exercises.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                for item in data.get("exercises", []):
                    connection.execute(
                        "INSERT OR REPLACE INTO exercises (id, payload, source, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                        (item["id"], json.dumps(item, ensure_ascii=False), "textbook", "seed", now_iso()),
                    )
        for key, value in DEFAULT_QA_CONFIG.items():
            connection.execute(
                "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (f"qa.{key}", value, now_iso()),
            )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "time": now_iso(), "baseChunks": len(BASE_CHUNKS), "llmConfigured": bool(LLM_API_URL and LLM_API_KEY)}


@app.post("/api/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    with db() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (body.username.strip(),)).fetchone()
    if not row or not verify_password(body.password, row["password_salt"], row["password_hash"]):
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    user = row_to_user(row)
    return {"token": create_token(user), "user": user}


@app.get("/api/me")
def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": user}


@app.get("/api/documents")
def list_documents(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    documents = []
    for row in rows:
        document = {
            "id": row["id"],
            "title": row["title"],
            "text": row["text"],
            "sourceType": row["source_type"],
            "uploadedAt": row["uploaded_at"],
        }
        documents.append({**document, "chunkCount": len(chunk_document(document)), "textLength": len(document["text"])})
    return {"documents": documents, "chunks": sum(item["chunkCount"] for item in documents)}


@app.post("/api/documents")
def create_document(body: DocumentBody, user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    text = clean_uploaded_text(body.text)
    if len(text) < 8:
        raise HTTPException(status_code=400, detail="资料内容太短")
    document_id = f"doc-{int(time.time() * 1000)}-{secrets.token_hex(3)}"
    title = normalize_document_title(body.title)
    with db() as connection:
        connection.execute(
            "INSERT INTO documents (id, title, text, source_type, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, title, text[:180_000], body.sourceType, user["id"], now_iso()),
        )
    document = {"id": document_id, "title": title, "text": text[:180_000], "sourceType": body.sourceType, "uploadedAt": now_iso()}
    return {"document": document, "chunkCount": len(chunk_document(document))}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    raw = await file.read()
    text = clean_uploaded_text(raw.decode("utf-8", errors="ignore"))
    return create_document(DocumentBody(title=file.filename or "上传资料", text=text, sourceType="file-upload"), user)


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str, user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    with db() as connection:
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    return {"ok": True}


@app.get("/api/exercises")
def list_exercises(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM exercises ORDER BY source DESC, created_at DESC").fetchall()
    exercises = []
    for row in rows:
        payload = json.loads(row["payload"])
        payload["_source"] = row["source"]
        exercises.append(payload)
    chapters = sorted({item.get("chapter") for item in exercises if item.get("chapter")})
    return {
        "summary": {
            "total": len(exercises),
            "thinking": sum(1 for item in exercises if item.get("type") == "思考题"),
            "exercise": sum(1 for item in exercises if item.get("type") == "习题"),
            "chapters": chapters,
        },
        "exercises": exercises,
    }


@app.post("/api/exercises/import")
def import_exercises(body: ExerciseImportBody, user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    items = body.exercises if body.exercises is not None else body.items or []
    imported = [exercise for index, item in enumerate(items) if (exercise := normalize_imported_exercise(item, index))]
    with db() as connection:
        for exercise in imported:
            connection.execute(
                "INSERT OR REPLACE INTO exercises (id, payload, source, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                (exercise["id"], json.dumps(exercise, ensure_ascii=False), "teacher", user["id"], now_iso()),
            )
    return {"ok": True, "imported": len(imported), "exercises": imported}


@app.delete("/api/exercises/{exercise_id}")
def delete_exercise(exercise_id: str, user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    with db() as connection:
        connection.execute("DELETE FROM exercises WHERE id = ? AND source != 'textbook'", (exercise_id,))
    return {"ok": True}


@app.get("/api/qa-config")
def read_qa_config(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return get_qa_config()


@app.put("/api/qa-config")
def update_qa_config(body: QaConfigBody, user: dict[str, Any] = Depends(require_manager)) -> dict[str, Any]:
    values = body.model_dump()
    with db() as connection:
        for key, value in values.items():
            connection.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (f"qa.{key}", value, now_iso()),
            )
    return get_qa_config()


@app.post("/api/qa")
def ask_qa(body: QaBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    question = body.question.strip()
    if len(question) < 2:
        raise HTTPException(status_code=400, detail="问题太短")
    qa_config = get_qa_config()
    sources = search_chunks(question, uploaded_chunks() + BASE_CHUNKS, 4)
    llm_answer = call_llm(question, body.mode, sources, qa_config) if body.useLlm else None
    answer = llm_answer or build_local_answer(question, body.mode, sources, qa_config)
    return {"answer": answer, "sources": sources, "usedLlm": bool(llm_answer), "llmConfigured": bool(LLM_API_URL and LLM_API_KEY)}
