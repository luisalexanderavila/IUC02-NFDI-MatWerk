knowledge graph integration of BAM creep dataset 
==================================================


This is the main project repository for the task for KG integration of BAM creep dataset. 
The project is a part of IUC02 of NFDI-Matwerk.

# Instructions

The project uses several tools developed in the past, 
and all the dependencies are in separate repositories.

1. clone this repository and cd to its root directory.

2. install the python environment.

```
conda create -f environment.yaml
conda activate DataManagement
```

3. Install the dependencies.

Dependencies are configured in config/dependencies_config.yaml and can be cloned automátically.

```
python bin/setup_dependencies.py
```
which will clone a couple repositories into the ./dependencies directory.
For the moment all dependencies must be installed manually. 
You can cd into ./dependencies and install all of them as editable packages to allow development (at the moment its only
two small packages).

For instance
```
cd dependencies/LISParser 
pip install -e .
```

Application data is taken from the BAM creep dataset, which is available at https://doi.org/10.5281/zenodo.13937986 .
This data can be downloaded automatically.

```
python bin/get_data_from_zenodo.sh
```

This will download and unzip the datafiles to the Data/BAMDataset directory.


4. Run the tests

Now the results from the mapping can be reproduced bu execuiting the tests. 
pytest will discover all of the tests in the `./tests` and execute them.

```
pytest
```

5. Analyze the results

The tests create some json files in ./Metadata/Mappings/ and in Data/BAMDataset.
For the moment we need to check consistency.


6. Project structure


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


7. Achievements so far:

at the moment we are able to convert a LIS file into a schema-complient json file. Please see (Vh5205_C-78.LIS)[Vh5205_C-78.LIS] and (Vh5205_C-78_tranlated.josn)[Vh5205_C-78_tranlated.josn] for an example.

