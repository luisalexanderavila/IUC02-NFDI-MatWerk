# Changes to the schema 
Work on the 2.1.8 version
## loadSensorCalibration 
[ ] the loadSensorCalibration field, is currently a string. it should be a dropdown with 'Yes' and 'No' options. Under loadSensorCalibration a new field called loadSensorCalibrationDescription whith a string value and a description 'Add any available details concerning the calibration'
[ ] in the lis file this corresponds to 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration' field. this field has an extra new line after the value. 
A new filed should be added right below, 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration Description' containing the description in that new line.
[ ] the 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration Description' from the lis file should map to loadSensorCalibrationDescription in the json. 

# temperatureMeasuringSystem.dataAcquisition.calibrationStandard
[ ] in the schema this is now a stirng, we want to add a description: 'Add description: E.g., EURAMET/cg-11/v.01'

# Metadata --> Measuring and test equipment --> Temperature-measuring system --> Temperature sensor	Thermocouple location	Location with respect to gauge section 
[ ] In the lis file, this line has value 'Inside the gauge length' which should be just 'Inside' 

