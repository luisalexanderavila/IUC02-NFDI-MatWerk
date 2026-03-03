import argparse
import os
from pathlib import Path

from pyvis.network import Network
from rdflib import Graph


def build_graph_from_ttl(ttl_path: Path) -> Graph:
    graph = Graph()
    graph.parse(str(ttl_path), format="ttl")
    return graph


def create_html(graph: Graph, output_path: Path, title: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    network = Network(height="750px", width="100%", directed=True, notebook=False)
    network.barnes_hut()
    network.set_options(
        """
        {
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "direction": "LR",
                    "sortMethod": "directed"
                }
            },
            "physics": {
                "hierarchicalRepulsion": {
                    "nodeDistance": 150
                },
                "solver": "hierarchicalRepulsion"
            },
            "edges": {
                "smooth": {
                    "enabled": true,
                    "type": "cubicBezier"
                }
            }
        }
        """
    )

    nodes = set()
    for subject, predicate, obj in graph:
        source = str(subject)
        target = str(obj)
        edge_label = str(predicate).split("/")[-1].split("#")[-1]

        if source not in nodes:
            network.add_node(source, label=source.split("/")[-1].split("#")[-1], title=source)
            nodes.add(source)

        if target not in nodes:
            network.add_node(target, label=target.split("/")[-1].split("#")[-1], title=target)
            nodes.add(target)

        network.add_edge(source, target, label=edge_label, title=str(predicate), arrows="to")

    html = network.generate_html(notebook=False)
    html = html.replace("<title>" + network.heading + "</title>", f"<title>{title}</title>")
    output_path.write_text(html, encoding="utf-8")


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
