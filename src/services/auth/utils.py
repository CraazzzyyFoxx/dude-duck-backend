from passlib import pwd
from passlib.context import CryptContext


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_and_update_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    return password_context.verify_and_update(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def generate_password() -> str:
    return pwd.genword()
