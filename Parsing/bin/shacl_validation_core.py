import json
from pathlib import Path

from rdflib import Graph


def run_shacl_validation(
    data_graph_path: Path,
    shacl_shapes_path: Path,
    data_graph_format: str = "turtle",
    shacl_graph_format: str = "turtle",
):
    from pyshacl import validate

    data_graph = Graph()
    data_graph.parse(str(data_graph_path), format=data_graph_format)

    shacl_graph = Graph()
    shacl_graph.parse(str(shacl_shapes_path), format=shacl_graph_format)

    conforms, report_graph_ttl, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        inference="rdfs",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False,
        serialize_report_graph="ttl",
    )

    report_graph = Graph()
    report_graph.parse(data=report_graph_ttl, format="turtle")
    namespace_manager = report_graph.namespace_manager

    results = []
    for subject, predicate, obj in sorted(report_graph):
        results.append(
            {
                "subject": subject.n3(namespace_manager),
                "predicate": predicate.n3(namespace_manager),
                "object": obj.n3(namespace_manager),
            }
        )

    return {
        "conforms": bool(conforms),
        "report_text": str(report_text),
        "report_ttl": str(report_graph_ttl),
        "results": results,
    }


def write_report(report: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
