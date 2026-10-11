"""Print the OpenAPI schema as stable JSON. Needs no database or running server.

Usage: uv run python -m pnsi.cli.export_openapi > ../../packages/api-client/openapi.json
"""

from __future__ import annotations

import json
import logging
import sys


def schema_json() -> str:
    from pnsi.main import create_app
    from pnsi.settings import Settings

    # Fixed settings so the schema does not depend on the local .env.
    app = create_app(Settings(_env_file=None, app_env="dev", log_level="ERROR"))
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    logging.disable(logging.CRITICAL)
    sys.stdout.write(schema_json())


if __name__ == "__main__":
    main()
