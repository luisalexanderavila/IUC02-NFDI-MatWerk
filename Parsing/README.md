knowledge graph integration of BAM creep dataset 
==================================================


This is the sub-project repository for the task for KG integration of BAM creep dataset. 
The project is a part of IUC02 of NFDI-Matwerk.

# Instructions

The project uses several tools developed in the past, 
and all the dependencies have been cloned into the `./dependencies` directory as subtrees. 

# 1. install the python environment.

Recommended (cross-platform): use `pyenv` + local virtual environment.

Linux/macOS:

```
pyenv install -s 3.11.0
PYENV_VERSION=3.11.0 pyenv exec python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```
pyenv install -s 3.11.0
$env:PYENV_VERSION="3.11.0"
pyenv exec python -m venv .venv
.venv\Scripts\Activate.ps1
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
python bin/get_data_from_zenodo.py
```

Linux-only legacy wrapper (optional):

```
bash bin/get_data_from_zenodo.sh
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

Use a different Python version from pyenv (optional):

```
python bin/run_all_checks.py --python-version 3.11.9
```

Platform wrappers:

```bash
bash bin/run_all_checks.sh
```

```bat
bin\run_all_checks.bat
```
