import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD

# Load the JSON document
with open('/home/storage/fortimtb/CuadernoTrabajo/2025_IUC02_KGintegration.git/Data/BAMDataset/Vh5205_C-78_translated.json', 'r') as file:
    data = json.load(file)

# Define namespaces
SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.org/")
S = Namespace("http://example.org/shapes#")

# Create a graph
g = Graph()
g.bind("sh", SH)
g.bind("ex", EX)
g.bind("s", S)

# Function to create SHACL shapes from JSON
def create_shape(g, node, path, json_data):
    shape = URIRef(S[node])
    g.add((shape, RDF.type, SH.NodeShape))
    g.add((shape, SH.targetClass, EX[node]))

    for key, value in json_data.items():
        property_shape = URIRef(S[f"{node}_{key}_PropertyShape"])
        g.add((property_shape, RDF.type, SH.PropertyShape))
        g.add((property_shape, SH.path, URIRef(EX[key])))

        if isinstance(value, dict):
            nested_shape = create_shape(g, f"{node}_{key}", path + [key], value)
            g.add((property_shape, SH.node, nested_shape))
        else:
            g.add((property_shape, SH.datatype, XSD.string))
            g.add((property_shape, SH.minCount, Literal(1, datatype=XSD.integer)))
            g.add((property_shape, SH.maxCount, Literal(1, datatype=XSD.integer)))

        g.add((shape, SH.property, property_shape))

    return shape

# Create the SHACL shape
root_shape = create_shape(g, "MeasurementData", [], data["mappedMeasurementData"]["MeasurementData"])

# Serialize the graph to a file
g.serialize(destination='/home/storage/fortimtb/CuadernoTrabajo/2025_IUC02_KGintegration.git/Data/BAMDataset/Vh5205_C-78_translated.ttl', format='turtle')

print("SHACL shape created and saved to Vh5205_C-78_translated.ttl")