from __future__ import annotations

import argparse
import json

from src.discovery import append_discovery_items, build_discovery_index, collect_discovery_items
from src.pipeline import run_pipeline
from src.schemas import InputItem
from src.whitelist import build_whitelist_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OMS infodemic demo pipeline on one claim or one discovered item.")
    parser.add_argument("--claim", required=False, help="Manual claim or event text to analyze.")
    parser.add_argument("--title", default="", help="Optional title.")
    parser.add_argument("--source", default="manual_cli", help="Source name.")
    parser.add_argument("--url", default="", help="Optional source URL.")
    parser.add_argument("--language", default="fr", help="Output language code for the final draft.")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild the whitelist index before running.")
    parser.add_argument("--discover-query", help="Run web/social discovery for a query and analyze the first discovered item.")
    parser.add_argument("--max-items", type=int, default=6, help="Max items per discovery source.")
    parser.add_argument("--no-news", action="store_true", help="Disable news search discovery.")
    parser.add_argument("--no-bluesky", action="store_true", help="Disable Bluesky discovery.")
    args = parser.parse_args()

    if args.rebuild_index:
        build_whitelist_index(force_rebuild=True)

    if args.discover_query:
        discovered = collect_discovery_items(
            query=args.discover_query,
            include_news=not args.no_news,
            include_bluesky=not args.no_bluesky,
            max_items_per_source=args.max_items,
        )
        summary = append_discovery_items(discovered)
        build_discovery_index(force_rebuild=True)
        if not discovered:
            raise SystemExit("Discovery returned no items.")
        result = run_pipeline(discovered[0], output_language=args.language)
        print(
            json.dumps(
                {
                    "discovery_query": args.discover_query,
                    "discovery_store": summary,
                    "analyzed_item": discovered[0].model_dump(),
                    "result": result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if not args.claim:
        raise SystemExit("You must provide --claim or --discover-query")

    item = InputItem(
        title=args.title,
        text=args.claim,
        source=args.source,
        url=args.url,
        source_type="manual",
    )
    result = run_pipeline(item, output_language=args.language)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
