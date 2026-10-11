import uuid

from pnsi.audit import service as audit
from pnsi.auth.principal import Principal
from pnsi.enums import Locale, Role
from pnsi.errors import request_id_var


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def test_record_builds_event_with_actor_scope_and_request_id():
    p = Principal.build(uuid.uuid4(), uuid.uuid4(), frozenset({Role.ANALYSTE}))
    db = FakeSession()
    token = request_id_var.set("req-abc12345")
    try:
        event = audit.record(
            db, "user.locale_changed", actor=p, object_type="user", object_id=p.user_id,
            changes=audit.diff({"locale": Locale.FR}, {"locale": Locale.AR}),
        )  # fmt: skip
    finally:
        request_id_var.reset(token)
    assert db.added == [event]
    assert event.actor_id == p.user_id
    assert event.institution_id == p.institution_id
    assert event.actor_roles == ["analyste"]
    assert event.request_id == "req-abc12345"
    assert event.changes == {"locale": {"from": "fr", "to": "ar"}}


def test_sensitive_values_never_enter_the_trail():
    db = FakeSession()
    event = audit.record(
        db, "user.created",
        changes={"password_hash": {"from": None, "to": "$argon2id$x"}, "token": "abc"},
        context={"nested": {"api_key": "k"}},
    )  # fmt: skip
    assert event.changes["password_hash"] == "***"
    assert event.changes["token"] == "***"
    assert event.context["nested"]["api_key"] == "***"


def test_diff_lists_only_changed_fields():
    assert audit.diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4}) == {
        "b": {"from": 2, "to": 3},
        "c": {"from": None, "to": 4},
    }
