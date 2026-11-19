from src.api import exceptions


def test_unauthorized_exception_is_401_app_error_with_defaults():
    exc = exceptions.UnauthorizedException()
    assert isinstance(exc, exceptions.AppError)
    assert exc.status_code == 401
    assert exc.error == "unauthorized"
    assert exc.message


def test_unauthorized_exception_accepts_custom_message():
    exc = exceptions.UnauthorizedException("이메일 또는 비밀번호가 올바르지 않습니다.")
    assert exc.message == "이메일 또는 비밀번호가 올바르지 않습니다."
