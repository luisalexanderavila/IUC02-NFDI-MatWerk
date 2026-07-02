import pyshacl
from pyshacl import validate
from rdflib import Graph
import sys

if __name__ == "__main__":
    # Check ttl syntax
    rdf_Graph = Graph()

    try:
        rdf_Graph.parse("rdfGraph_smallExample.ttl", format="turtle")
        print("TTL file is valid!")

        for i, (subj, pred, obj) in enumerate(rdf_Graph):
            if i >= 10:
                break
            print(subj, pred, obj)

    except Exception as e:
        print("Error in TTL file:", e)

    # translate ttl to json-ld
    jsonld_Graph = rdf_Graph.serialize(format="json-ld", indent=4)
    with open("dataGraph.jsonld", "w", encoding="utf-8") as f:
        f.write(jsonld_Graph)

    print("JSON-LD saved as dataGraph.jsonld.")

    # read graph as ttl
    rdf_Graph = Graph()
    rdf_Graph.parse("rdfGraph_smallExample.ttl", format="turtle")

    # read graph as json-ld
    jsonld_Graph = Graph()
    jsonld_Graph.parse("dataGraph.jsonld", format="json-ld")

    # read shacl shapes
    shacl_shape = Graph()
    shacl_shape.parse("shaclShape_smallExample.ttl", format="turtle")

    # validate data_graph against shacl_shapes
    results = validate(
        data_graph=rdf_Graph,
        shacl_graph=shacl_shape,
        inference='rdfs',
        data_graph_format="ttl",
        shacl_graph_format="ttl",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=True,
        serialize_report_graph="ttl",
    )
    conforms, report_graph, report_text = results
    print("conforms", conforms)
    print(report_text)

    report_g = Graph()
    report_g.parse(data=report_graph, format="ttl", encoding="utf-8")
    nm = report_g.namespace_manager

    for s, p, o in sorted(report_g):
        print(s.n3(nm), p.n3(nm), o.n3(nm))