import typing
from datetime import datetime, timedelta, UTC

import jwt
from src.core import config


def generate_jwt(
    data: dict,
    secret: str,
    lifetime_seconds: int | None = None,
) -> str:
    payload = data.copy()
    if lifetime_seconds:
        expire = datetime.now(UTC) + timedelta(seconds=lifetime_seconds)
        payload["exp"] = expire
    return jwt.encode(payload, secret, algorithm=config.app.algorithm)


def decode_jwt(
    encoded_jwt: str,
    secret: str,
    audience: list[str],
) -> dict[str, typing.Any]:
    return jwt.decode(
        encoded_jwt,
        secret,
        audience=audience,
        algorithms=[config.app.algorithm],
    )
