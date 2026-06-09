# Changes to the schema 
Work on the 2.1.8 version
## loadSensorCalibration 
[ ] the loadSensorCalibration field, is currently a string. it should be a dropdown with 'Yes' and 'No' options. Under loadSensorCalibration a new field called loadSensorCalibrationDescription whith a string value and a description 'Add any available details concerning the calibration'
[ ] in the lis file this corresponds to 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration' field. this field has an extra new line after the value. 
A new filed should be added right below, 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration Description' containing the description in that new line.
[ ] the 'Metadata --> Measuring and test equipment --> Load-measuring system --> Load sensor	Load sensor calibration Description' from the lis file should map to loadSensorCalibrationDescription in the json. 

# temperatureMeasuringSystem.dataAcquisition.calibrationStandard
[ ] in the schema this is now a string, we want to add a description: 'Add description: E.g., EURAMET/cg-11/v.01'

# Metadata --> Measuring and test equipment --> Temperature-measuring system --> Temperature sensor	Thermocouple location	Location with respect to gauge section 
[ ] In the lis file, this line has value 'Inside the gauge length' which should be just 'Inside' 

# Metadata --> Measuring and test equipment --> Temperature-measuring system --> Temperature sensor	Temperature deviation
[ ] in lis file, value should be one line. As an example for Vh5205_C-78-MD-TR.lis, instead of 
- 0.1 K (52-PM102-0400)
- 0.1 K (52-PM102-0401)
- 0.1 K (52-PM102-0402)
T-values were corrected accordingly	
it should be
- 0.1 K (52-PM102-0400); - 0.1 K (52-PM102-0401); - 0.1 K (52-PM102-0402); T-values were corrected accordingly	

# Metadata --> Measuring and test equipment --> Temperature-measuring system --> Data acquisition	Temperature deviation
[ ] in lis file, value should be one line. As an example for Vh5205_C-78-MD-TR.lis, instead of 
0 K (Channel #1)
+ 0.1 K (Channel #2)
- 0.2 K (Channel #3)
it should be
0 K (Channel #1); + 0.1 K (Channel #2); - 0.2 K (Channel #3)

# Metadata --> Measuring and test equipment --> Extension values --> Contacting extensometer
[ ] In lis files, entry name is currently "Is the extensometer incl. the data acquisition calibrated?". It must be "Calibration status". I json files it was correctly named "calibrationStatus"

