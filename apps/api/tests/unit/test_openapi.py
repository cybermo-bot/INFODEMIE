from pathlib import Path

from pnsi.cli.export_openapi import schema_json

CLIENT_SCHEMA = Path(__file__).resolve().parents[4] / "packages" / "api-client" / "openapi.json"


def test_committed_client_schema_is_current():
    assert CLIENT_SCHEMA.read_text(encoding="utf-8") == schema_json(), (
        "packages/api-client/openapi.json is stale: run `make api-client`"
    )


def test_every_operation_has_an_id_and_documents_errors():
    import json

    schema = json.loads(schema_json())
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            assert op.get("operationId"), f"{method} {path} lacks operation_id"
            if not path.startswith("/api/v1/health"):
                assert "403" in op["responses"], f"{method} {path} must document 403"
