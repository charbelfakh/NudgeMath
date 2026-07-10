from hint_engine.auth import (
    create_token,
    hash_password,
    verify_password,
    verify_token,
)

SECRET = "test-secret"


def test_password_hash_roundtrip():
    encoded = hash_password("hunter2")
    assert encoded.startswith("scrypt$")
    assert verify_password("hunter2", encoded) is True
    assert verify_password("wrong", encoded) is False


def test_password_hash_is_salted():
    # Same password hashes differently (random salt), both still verify.
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
    assert verify_password("same", a)
    assert verify_password("same", b)


def test_verify_password_rejects_garbage():
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "scrypt$bad") is False


def test_token_roundtrip():
    token = create_token("admin", secret=SECRET, now=1000.0)
    assert verify_token(token, secret=SECRET, now=1000.0) == "admin"


def test_token_expires():
    token = create_token("admin", ttl_seconds=100, secret=SECRET, now=1000.0)
    assert verify_token(token, secret=SECRET, now=1099.0) == "admin"
    assert verify_token(token, secret=SECRET, now=1100.0) is None
    assert verify_token(token, secret=SECRET, now=5000.0) is None


def test_token_rejects_tamper():
    token = create_token("admin", secret=SECRET, now=1000.0)
    payload, sig = token.split(".")
    tampered = payload + "." + ("A" if sig[0] != "A" else "B") + sig[1:]
    assert verify_token(tampered, secret=SECRET, now=1000.0) is None


def test_token_rejects_wrong_secret():
    token = create_token("admin", secret=SECRET, now=1000.0)
    assert verify_token(token, secret="other-secret", now=1000.0) is None


def test_verify_token_rejects_garbage():
    assert verify_token("garbage", secret=SECRET) is None
    assert verify_token("a.b.c", secret=SECRET) is None
