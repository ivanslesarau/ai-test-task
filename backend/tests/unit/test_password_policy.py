from app.core.password_policy import validate_password


def test_rejects_password_shorter_than_minimum() -> None:
    assert validate_password("short1234567") is None  # exactly 12 chars, not breached
    error = validate_password("short12345")  # 10 chars
    assert error is not None
    assert "12 characters" in error


def test_rejects_password_longer_than_maximum() -> None:
    error = validate_password("a" * 129)
    assert error is not None
    assert "128 characters" in error


def test_accepts_a_password_within_bounds_and_not_breached() -> None:
    assert validate_password("Xk9#mQ2vLp$4wZ") is None


def test_rejects_a_password_on_the_breached_list() -> None:
    error = validate_password("password123456")
    assert error is not None
    assert "breached" in error.lower()


def test_breached_check_is_case_insensitive() -> None:
    error = validate_password("PASSWORD123456")
    assert error is not None


def test_boundary_lengths_are_accepted() -> None:
    assert validate_password("x" * 12) is None
    assert validate_password("x" * 128) is None
