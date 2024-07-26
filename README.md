**NFDI-MatWerk/IUC02 Data schema for creep data of Ni-based superalloys including a comprehensive documentation of test results and metadata
Version 1.0 (07/2024)**

Creep testing of metallic materials for high temperature applications, e.g., in turbines and power plants, yields valuable datasets. High experimental efforts are necessary to ensure stable high temperature and constant loading conditions in these long-running tests. Proper, comprehensive documentation of these experiments is a key element to enable the assessment of the quality of respective creep datasets and their targeted use (and future re-use) for specific applications.
The provided data schema for creep tests was developed within the German NFDI-MatWerk initiative (https://nfdi-matwerk.de/). It is intended to define a structured approach for collecting all required information on a creep experiment using the established terminology of the respective test standard ISO 204:2022. The development goals encompass the following primary aspects:

- To ensure a comprehensive description with a hierarchical data structure that can be implemented to data management platforms,
- To define a scope of documentation that allows the assessment of a dataset’s quality by different end users who retrieve datasets from multiple data providers,
- To foster the exchange of high-quality creep datasets according to the FAIR principles [1], by providing easy interoperability and full reusability.

Although originally developed for datasets of Ni-based high temperature alloys, the data schema is largely agnostic to the type of material and may be similarly used for creep tests of different metallic (and other) materials.
A very detailed approach was chosen to ensure the collection of all related pieces of information, e.g. including a complete description of the material’s manufacturing history and a comprehensive description of the laboratory equipment. In this way, the developed data schema serves to describe or identify high quality datasets, which can be considered as reference data for verification purposes based on their precision and documentation. It is acknowledged that certain datasets, depending on their origin and intended use, may not require this full depth of documentation. Still, the suggested data schema can help to decide which parts of information are relevant for the respective purpose. The authors intend to further optimize the data structure in future versions, defining quality classes for creep datasets based on the extent of available (meta-) information.
This version of the data schema covers creep tests with the following features:

- It considers single- and polycrystalline specimen material
- Terminology is aligned with ISO 204:2022
- Creep test under tension and constant force
- Temperature measurement with thermocouples
- Contacting extensometer system

The data schema is provided in the following formats: .pdf, .xlsx, .csv and JSON, and it is also available in this git repository ([https://git.rwth-aachen.de/nfdi-matwerk/iuc02]).
The .xlsx/.pdf/.csv version of the data schema contains 12 columns. Columns B to E are categories that define the overarching structure of the schema (Please refer to file "Schema Structure Overview"). This structure mimics the way a domain expert would structure the data. Columns F to H refer to the single entries with the respective symbol and unit, if applicable. The units are community-common units. Column I is the data type. It should give a first hint on how to answer each entry field. Column J provides exemplary answers for most of the entries and the options of the corresponding drop-down list, if applicable. Column K is the requirement profile, while column L includes further explanations on the requirement and on the applicability of some entries.
The Requirement Profile (column K) refers to the highest quality class of reference creep data, taken from calibrated instruments, and which shall enable the following usages:
- Checking own creep test results on nominally similar material
- Verification of own testing set-up (e.g. by testing same/similar material)
- Using the data as input data for simulations of creep behavior for design and alloy development

Other quality classes or typical research datasets require less documentation.
The JSON schema yields the same categorization as the .xlsx/.pdf/.csv files and includes those concepts present in the data schema. The requirement profile and data type are essential features to be provided for each entry. The JSON schema is structured with column B as the first level of categorization and the mapping further builds upon it.
Our current definition for reference data of materials is available here: [https://zenodo.org/records/11667674].


Acknowledgment: 

This work was carried out in the framework of NFDI-MatWerk and funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) under the National Research Data Infrastructure – NFDI 38/1 – project number 460247524. Mariano Forti and Thomas Hammerschmidt acknowledge financial support by the DFG through project C1 of the collaborative research centre SFB/TR 103 (project number 190389738). Rossella Aversa acknowledges financial support by the EU’s H2020 framework program for research and innovation under grant agreement n. 101007417, NFFA-Europe Pilot Project. All authors acknowledge: (i) Klaus Neuking and Gunther Eggeler from Institute for Materials, Ruhr-Universität Bochum, Germany, for fruitful discussions on the detailed description of creep test setups and creep data of single-crystal superalloys, (ii) Irina Roslyakova from Institute for Materials, Ruhr-Universität Bochum, Germany, and Steffen Brinckmann from Forschungszentrum Jülich, Germany for fruitful discussions on data processing, and (iii) Erik Bitzek from Friedrich-Alexander-Universität Erlangen-Nürnberg for fruitful discussions on general requirements on contents and data formats in relation to creep data of Ni-based superalloys.

References:
[1] Wilkinson, M., Dumontier, M., Aalbersberg, I. et al. The FAIR Guiding Principles for scientific data management and stewardship. Sci Data 3, 160018 (2016). https://doi.org/10.1038/sdata.2016.18