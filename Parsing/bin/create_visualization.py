import argparse
import os
from pathlib import Path

from visualization_core import build_graph_from_ttl, create_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an interactive RDF visualization HTML for browser use."
    )
    parser.add_argument(
        "--input",
        default=os.path.join("shacl_validation", "rdfGraph_smallExample.ttl"),
        help="Input Turtle file (default: shacl_validation/rdfGraph_smallExample.ttl)",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("Notebooks", "rdf_graph_viewer.html"),
        help="Output HTML file (default: Notebooks/rdf_graph_viewer.html)",
    )
    parser.add_argument(
        "--title",
        default="IUC02 RDF Web Visualization",
        help="Visualization title",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    graph = build_graph_from_ttl(input_path)
    create_html(graph, output_path, args.title)
    print(f"Visualization generated at: {output_path.resolve()}")


if __name__ == "__main__":
    main()
