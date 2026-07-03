from __future__ import annotations

import base64
import io
import random
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from ..models import CaptchaRecord
from ..security import keyed_digest


CAPTCHA_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def random_code() -> str:
    return "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(4))


def render_image(code: str) -> str:
    image = Image.new("RGB", (150, 52), (241, 247, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=28)
    for _ in range(4):
        y1, y2 = random.randint(5, 47), random.randint(5, 47)
        draw.line((0, y1, 150, y2), fill=(55, 105, 170), width=1)
    for _ in range(65):
        x, y = random.randrange(150), random.randrange(52)
        draw.point((x, y), fill=(random.randrange(90, 180), random.randrange(90, 170), random.randrange(110, 200)))
    for index, character in enumerate(code):
        draw.text((18 + index * 30, 9 + random.randint(-2, 2)), character, font=font, fill=(19, 66, 126))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def create_captcha(session: Session, secret: str, client_ip: str, ttl_seconds: int) -> tuple[CaptchaRecord, str]:
    code = random_code()
    record = CaptchaRecord(
        id=str(uuid4()),
        answer_hash=keyed_digest(code.upper(), secret),
        client_ip=client_ip,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    )
    session.add(record)
    session.commit()
    return record, render_image(code)
