# Fix parsing of dropdown values in schema. 


some schema values are determined as dropdown. in the web app parsed values, this is being shown as:

calibrationStandard: {"calibrationStandardOptions": "DIN EN ISO 7500-2"}

Howver, the expected rendered visualization should be:

calibrationStandard: "DIN EN ISO 7500-2"

- check if the problem comes from the visualization or the json parsing. 
- check similar problems for other dropdown fields. 
