import json
import logging

from pnsi.log import MASK, SecretRedactor, configure_logging, get_logger


def test_sensitive_field_names_are_masked():
    redactor = SecretRedactor()
    out = redactor(None, "info", {"event": "x", "password": "hunter2", "api_key": "k", "n": 3})
    assert out["password"] == MASK
    assert out["api_key"] == MASK
    assert out["n"] == 3


def test_known_secret_values_are_masked_anywhere():
    redactor = SecretRedactor(["sk-live-123456"])
    out = redactor(
        None,
        "info",
        {"event": "calling with sk-live-123456", "detail": {"url": "https://x?k=sk-live-123456"}},
    )
    assert "sk-live-123456" not in json.dumps(out)


def test_nested_structures_are_scrubbed():
    redactor = SecretRedactor(["topsecret"])
    event = {"event": "e", "items": [{"Authorization": "Bearer x"}, "topsecret"]}
    out = redactor(None, "info", event)
    assert out["items"][0]["Authorization"] == MASK
    assert out["items"][1] == MASK


def test_end_to_end_log_line_has_no_secret(capsys):
    configure_logging("INFO", ["groq-key-abcdef"])
    get_logger("t").info("request failed", error="401 for key groq-key-abcdef", token="t0k3n")
    logging.getLogger("stdlib").warning("raw groq-key-abcdef")
    out = capsys.readouterr().out
    assert "groq-key-abcdef" not in out
    assert "t0k3n" not in out
    assert out.count(MASK) >= 3
