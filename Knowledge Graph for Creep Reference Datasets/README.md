**Knowledge Graph for Creep Reference Datasets (NFDI MatWerk IUC02)**

The pipeline is planned to map **[BAM Reference Data: Creep of Single-Crystal Ni-Based Superalloy CMSX-6](https://zenodo.org/records/20132712)** into MSE-KG. The RDF-converted sources semantically descrble creep testing process, test pieces, materials & chemical composition, test machines & extensometers, input specifications (stress, temperature), and primary/secondary test results (rupture time, gauge lengths, durations, elongation/extension percentages).

**Links:**
- [Source JSON datasets](https://zenodo.org/records/20132712)
- [Reused Creep Testing Ontology (CTO)](https://github.com/HosseinBeygiNasrabadi/creep-testing-ontology)
- RDF in MaterialDigital Data Portal, **[Knowledge Graph for Creep Reference Datasets (NFDI MatWerk IUC02)](https://dataportal.material-digital.de/dataset/knowledge-graph-for-creep-reference-datasets-nfdi-matwerk-iuc02)**: 
- [SPARQL endpoint](https://dataportal.material-digital.de/dataset/knowledge-graph-for-creep-reference-datasets-nfdi-matwerk-iuc02/fuseki)
- [Guided query UI (Sparklis)](https://dataportal.material-digital.de/sparklis/?title=knowledge-graph-for-creep-reference-datasets-nfdi-matwerk-iuc02&endpoint=https%3A//dataportal.material-digital.de/dataset/bb5b86d3-ade4-4b63-9e84-783de85a4abd/fuseki/%24/sparql&entity_lexicon_select=http%3A//www.w3.org/2000/01/rdf-schema%23label&concept_lexicons_select=http%3A//www.w3.org/2000/01/rdf-schema%23label)

**Running it yourself:** If you have a new dataset;

1. Clone the repository,
2. Put your dataset in the `JSON datasets/` folder,
3. Run `bash creep_reference_dataset_map.sh`,
4. Copy the updated `creep_reference_dataset_rdf.ttl` and push it to Zenodo / the PMD data portal.

**Example SPARQL queries** (see [`queries/`](./Creep%20reference%20dataset%20(IUC02)/queries)):

1. List all creep datasets together with their test piece IDs and material identifiers.
2. Retrieve the initial stress and temperature used for each creep test.
3. Rank datasets by creep rupture time, longest to shortest.
4. Find all datasets tested within a given temperature range.
5. Retrieve the full chemical composition (all elements, wt.% and ppm) for a given test piece.
6. Compare percentage elongation after creep fracture across all datasets.
7. Retrieve test duration, soak time, and heating time together for each creep testing process.
8. List all creep testing machines and extensometers together with the datasets that used them.



## Contact

Dr. Hossein Beygi Nasrabadi
FIZ Karlsruhe – Leibniz Institute for Information Infrastructure GmbH
Email: Hossein.Beygi_Nasrabadi@fiz-karlsruhe.de
