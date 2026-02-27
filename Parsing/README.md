knowledge graph integration of BAM creep dataset 
==================================================


This is the sub-project repository for the task for KG integration of BAM creep dataset. 
The project is a part of IUC02 of NFDI-Matwerk.

# Instructions

The project uses several tools developed in the past, 
and all the dependencies have been cloned into the `./dependencies` directory as subtrees. 

# 1. install the python environment.

```
conda create -f environment.yaml
conda activate DataManagement
```

or for a fresh pip-based environment:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

# 2. Install the dependencies.


All dependenies have been included in the `dependencies` directory as subtrees. However, for ease of use they should be installed manually.
For this, cd into the depnendency folder and insatll it in development mode.

```
cd dependencies/creep_shacl_maker
pip install -e .
```

# 3. Use case data

Application data is taken from the BAM creep dataset, which is available at https://doi.org/10.5281/zenodo.13937986 .
This data can be downloaded automatically.

```
bash bin/get_data_from_zenodo.sh
```

or, if you prefer (thanks  @teman67!)

```
python bin/get_data_from_zenodo.py
```

This will download and unzip the datafiles to the Data/BAMDataset directory.


# 4. Run the tests

Now the results from the mapping can be reproduced bu execuiting the tests. 
pytest will discover all of the tests in the `./tests` and execute them.

```
pytest
```

# 5. Analyze the results

The tests create some json files in ./Metadata/Mappings/ and in Data/BAMDataset.
For the moment we need to check consistency.


# 6. Project structure


.
├── bin                 #    script files to be executed directly
├── config              # config files (mostly yaml)
├── Data                # data files
├── dependencies        # cloned dependencies
├── Doc                 # documentation
├── Metadata
│     └── Mappings      # mapping files, ttl, rdf, json.
├── Notebooks
├── src                 # source codea(python files, any other application.
└── test                # test files


Any mapping, schema, in json, ttl or rdf formats should reside inside the Mappings directory, 
at least until we can find a better solution. 

TODO: this needs  to be adapted to the new project structue!


# 7. Achievements so far:

at the moment we are able to convert a LIS file into a schemka-complient json file. Please see (Vh5205_C-78.LIS)[Vh5205_C-78.LIS] and (Vh5205_C-78_tranlated.josn)[Vh5205_C-78_tranlated.josn] for an example.

## 7.1 LIS to JSON
```
python bin/translate_bam_data.py Data/BAMDataset/Vh5205_C-95.LIS  --output Data/BAMDataset_Json/Vh5205_C-95_translated.json
```


## 7.2 JSON to SHACL

```
python bin/json_to_shacl_2.py Data/BAMDataset_Json/Vh5205_C-95_translated.json --output  Data/BAMDataset_Graph/Vh5205_C-78_translated.ttl
```


## 7.3 LIS to SHACL

```
python bin/bam2shacl.py -i Data/BAMDataset/Vh5205_C-78.LIS  -o Data/BAMDataset_Graph/Vh5205_C-78_translated.ttl
```

## 7.4 Web visualization (browser)

Generate a standalone HTML graph visualization:

```
python bin/create_visualization.py
```

Optional input/output:

```
python bin/create_visualization.py --input shacl_validation/rdfGraph_smallExample.ttl --output Notebooks/rdf_graph_viewer.html
```

## 7.5 One-command checks (tests + visualization)

Run everything needed before handoff:

```
python bin/run_all_checks.py
```

Use a different micromamba env name (optional):

```
python bin/run_all_checks.py <env_name>
```

Platform wrappers:

```bash
bash bin/run_all_checks.sh
```

```bat
bin\run_all_checks.bat
```
