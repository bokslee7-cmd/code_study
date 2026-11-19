from passlib.context import CryptContext

BCRYPT_ROUNDS = 12  # cost factor from research.md
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt ignores everything after 72 bytes

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)


def _too_long(password: str) -> bool:
    return len(password.encode("utf-8")) > MAX_PASSWORD_BYTES


def validate_password(password: str) -> None:
    """Raise ValueError if the password does not meet the length policy."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if _too_long(password):
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    if _too_long(password):
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if _too_long(password):
        return False
    try:
        return bool(_pwd_context.verify(password, password_hash))
    except ValueError:  # malformed or unknown hash format
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with a weaker cost factor and should be upgraded on login."""
    return bool(_pwd_context.needs_update(password_hash))
