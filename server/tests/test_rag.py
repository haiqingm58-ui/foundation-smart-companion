from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from server.application.config import Settings
from server.application.services.rag import call_llm, contextual_query


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
    urlopen.return_value = FakeResponse(
        {"choices": [{"message": {"content": "  桩侧阻力由界面剪切发挥。[1]  "}}]}
    )

    history = [
        {"role": "user", "content": "桩侧阻力如何产生？"},
        {"role": "assistant", "content": "它由桩土界面剪切作用发挥。"},
    ]
    answer = call_llm(settings(tmp_path), "它受什么影响？", "教材问答", SOURCES, history)

    assert answer == "桩侧阻力由界面剪切发挥。[1]"
    request = urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://api.siliconflow.cn/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "THUDM/GLM-Z1-9B-0414"
    assert payload["stream"] is False
    prompt = payload["messages"][1]["content"]
    assert "对话上下文（仅用于理解指代，不作为知识依据）" in prompt
    assert "学生：桩侧阻力如何产生？" in prompt
    assert "助教：它由桩土界面剪切作用发挥。" in prompt


def test_contextual_query_uses_recent_user_turn_for_short_follow_up() -> None:
    history = [
        {"role": "user", "content": "桩侧阻力如何产生？"},
        {"role": "assistant", "content": "它由桩土界面剪切作用发挥。"},
    ]

    assert contextual_query("它受什么影响？", history) == "桩侧阻力如何产生？ 它受什么影响？"


def test_contextual_query_keeps_standalone_question_unchanged() -> None:
    question = "地基承载力特征值的主要影响因素有哪些？"

    assert contextual_query(question, []) == question


@patch("server.application.services.rag.urllib.request.urlopen")
def test_call_llm_returns_none_for_malformed_choices(urlopen, tmp_path: Path) -> None:
    urlopen.return_value = FakeResponse({"choices": []})

    assert call_llm(settings(tmp_path), "桩侧阻力如何发挥？", "教材问答", SOURCES) is None
