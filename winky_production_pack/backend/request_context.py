import secrets
from contextvars import ContextVar

request_id_var = ContextVar("winky_request_id", default="")


def new_request_id() -> str:
    return secrets.token_hex(8)


def set_request_id(value: str) -> None:
    request_id_var.set(value)


def get_request_id() -> str:
    return request_id_var.get("")
