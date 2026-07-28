import argparse
import json
import sys
from pathlib import Path

import shacl_validation_core


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate RDF data graph against SHACL shapes.")
    parser.add_argument("--data-graph", required=True, help="Path to RDF data graph (.ttl, .jsonld, etc.).")
    parser.add_argument("--shacl-shapes", required=True, help="Path to SHACL shapes graph (.ttl).")
    parser.add_argument("--data-format", default="turtle", help="rdflib format of data graph (default: turtle).")
    parser.add_argument("--shapes-format", default="turtle", help="rdflib format of SHACL graph (default: turtle).")
    parser.add_argument("--format", dest="fmt", choices=["text", "json"], default="text", help="Output format.")
    parser.add_argument("--output", default=None, help="Optional JSON report output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    data_graph = Path(args.data_graph)
    shacl_shapes = Path(args.shacl_shapes)

    if not data_graph.exists() or not data_graph.is_file():
        raise FileNotFoundError(f"Data graph not found: {data_graph}")
    if not shacl_shapes.exists() or not shacl_shapes.is_file():
        raise FileNotFoundError(f"SHACL graph not found: {shacl_shapes}")

    report = shacl_validation_core.run_shacl_validation(
        data_graph_path=data_graph,
        shacl_shapes_path=shacl_shapes,
        data_graph_format=args.data_format,
        shacl_graph_format=args.shapes_format,
    )

    summary = {
        "data_graph": str(data_graph),
        "shacl_shapes": str(shacl_shapes),
        **report,
    }

    if args.fmt == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Data graph : {data_graph}")
        print(f"SHACL graph: {shacl_shapes}")
        print(f"Conforms   : {summary['conforms']}")
        if not summary["conforms"]:
            print("--- Report text ---")
            print(summary["report_text"])

    if args.output:
        shacl_validation_core.write_report(summary, Path(args.output))

    return 0 if summary["conforms"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SHACL validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
