from pathlib import Path

from pyvis.network import Network
from rdflib import Graph


def build_graph_from_ttl(ttl_path: Path) -> Graph:
    graph = Graph()
    graph.parse(str(ttl_path), format="ttl")
    return graph


def create_html(graph: Graph, output_path: Path, title: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    network = Network(
        height="750px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="local",
    )
    network.cdn_resources = "local"
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

    network.write_html(str(output_path), notebook=False, open_browser=False, local=True)
    html = output_path.read_text(encoding="utf-8")
    html = html.replace("<title>" + network.heading + "</title>", f"<title>{title}</title>")
    output_path.write_text(html, encoding="utf-8")
