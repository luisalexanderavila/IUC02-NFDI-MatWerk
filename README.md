knowledge graph integration of BAM creep dataset 
==================================================


This is the main project repository for the task for KG integration of BAM creep dataset. 
The project is a part of IUC02 of NFDI-Matwerk.

# Instructions

The project uses several tools developed in the past, 
and all the dependencies are in separate repositories.

# 1. clone this repository and cd to its root directory.

# 2. install the python environment.

```
conda create -f environment.yaml
conda activate DataManagement
```

3. Install the dependencies.

There is one dependency which was created from scratch for this project and is included in the main repository so you dont need to 
download it. For practicity, it was included as an independent package and you need to cd to its location and
install it in the python environment.

```
cd dependencies/creep_shacl_maker
pip install -e .
```

Other dependencies which were created before and are applied now were brought from the old repositories (mainly Aachen gitlab instance). 
as all the repositories are private for the moment and maybe to small as to put them in pipy, you need to install each of them separately.
There is a script that can help, with the aid of a configuration file in `config/dependencies_config.yaml`,
To execute the scirpt, simply do:

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

# 4. Use case data

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


# 7. Achievements so far:

at the moment we are able to convert a LIS file into a schema-complient json file. Please see (Vh5205_C-78.LIS)[Vh5205_C-78.LIS] and (Vh5205_C-78_tranlated.josn)[Vh5205_C-78_tranlated.josn] for an example.

## 7.1 LIS to JSON
```
python bin/translate_bam_data.py Data/BAMDataset/Vh5205_C-95.LIS  --output Data/BAMDataset_Json/Vh5205_C-95_translated.json
```


## 7.2 JSON to SHACL

```
python bin/json_to_shacl_2.py Data/BAMDataset_Json/Vh5205_C-95_translated.json --output  Data/BAMDataset_Graph/Vh5205_C-78_translated.ttl
```
