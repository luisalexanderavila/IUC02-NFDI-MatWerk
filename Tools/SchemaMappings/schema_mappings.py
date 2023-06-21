import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from Tools.Metainfo.metainfo import Quantity, MissingQuantity

import copy

def map_bam_to_schema(schema, lisdata):
    schemed_data = copy.copy(schema)
    
    schemed_data_specified_test_params = {
        'Testing Standard' : Quantity(
            Value = lisdata['metadata']['Prüfnorm'],
        ),
        'Specified Temperature': Quantity(
            Value = re.findall('[0-9]+', lisdata['metadata']['Prüftemperatur PT'])[0],
            Symbol = 'T',
            Unit = re.findall('[^0-9]+', lisdata['metadata']['Prüftemperatur PT'])[0],
        ), 
        'Initial stress' : Quantity(
            Symbol = "R0", 
            Unit= 'MPa',
            Value = 'MISING'
        ),
        'Test type (interrupted/not interrupted)' : Quantity(
            Value = 'MISSING'
        ),
        'End of experiment (time limit/test piece break/extension limit)': Quantity(
            Value = 'MISSING - Time limit ?'
        ),
        'Test force' : Quantity(
            Unit = 'kN', 
            Value = re.findall('[0-9,]+', lisdata['metadata']['Prüfkraft'])[0]
        )
    }
    
    schemed_data_test_order =  {
        'Test date' : Quantity(
            Value = lisdata['metadata']['Versuchs-Datum']
        ),
        'Test ID' : Quantity(
            Value = lisdata['metadata']['Versuchsnummer']
        ), 
        'Project' : Quantity(
            Value = lisdata['metadata']['Projekt']
        ),
        'Operator' : Quantity(
            Value = lisdata['metadata']['Bearbeiter']
        )
    }
    
    schemd_data_material_and_state = {
        'Material ID' : Quantity(
            Value = lisdata['metadata']['Probenbezeichnung']
        ),
        'Manufacturing: Melting' : MissingQuantity(),
        'Manufacturing: Casting' : MissingQuantity(),
        'Manufacturing: Remelting' : MissingQuantity(),
        'Manufacturing: Atmosphere' : MissingQuantity(),
        'Manufacturing: Single or polycrystal solidified' : MissingQuantity(),
        'Manufacturing: Thermomechanical treatment' : MissingQuantity(),
        'Heat treatment: Atmosphere' : MissingQuantity(),
        'Ageing applied?' : MissingQuantity(),
        'Chemical composition, nominal' : MissingQuantity(),
        'Chemical composition, measured (including precision)' : MissingQuantity(),
        'Geometry/dimensions of blank' : [Quantity(
            Value = lisdata['metadata']['Probenform']
            )], 
        'Blank: Geometry/Dimensions' : MissingQuantity(),
        'Blank: date of supply' : MissingQuantity(),
        'Blank: order number' : MissingQuantity(),
        'Blank: supplier sample ID' : MissingQuantity(),
        'Microstructure: Heat treatment condition (annealed, hardened, …)' : MissingQuantity(),
        'Tensile properties at testing temperature available?' : MissingQuantity(),
        'Proof of syngle crystallinity' : MissingQuantity(),
        'Single Crystall Orientation ' : Quantity( Value = lisdata['metadata']['Zustand/Orientierung']) , 
        'Angle orientation' : MissingQuantity(),
        'Crack inspection details' : MissingQuantity(),
        'X-Ray film?' : MissingQuantity(),
        'Grain Defects mapzos?' : MissingQuantity(),
    }

    schemed_data_test_piece = {
            'Test piece ID' : Quantity(
                Value = lisdata['metadata']['Probenzeichnung']
                ), 
            }

    schemed_data_TestSequence = {
            'Elapsed time from end of loading' : MissingQuantity(), 
            'Test duration' : Quantity(
                Value = re.findall('[0-9,\.]+', lisdata['metadata']['Versuchsdauer'])[0],
                Unit = re.findall('[^0-9,\.]+', lisdata['metadata']['Versuchsdauer'])[0],
                ), 
            'Extension' : Quantity(
                Symbol = '$\Delta L et$',
                Unit = re.findall('[^0-9,]+', lisdata['metadata']['gesamte Dehnung'])[0],
                Value = re.findall('[0-9,]+', lisdata['metadata']['gesamte Dehnung'])[0]
                ), 
            }

    
    schemed_data['Metadata']['Test info']['Specified test parameters'] = schemed_data_specified_test_params
    schemed_data['Metadata']['Test info']['Test order'] = schemed_data_test_order
    schemed_data['Metadata']['Tested material']['Material and state'] = schemd_data_material_and_state
    schemed_data['Metadata']['Tested material']['Test piece'] = schemed_data_test_piece
    schemed_data['Primary data']['Test results']['Test sequence'] = schemed_data_TestSequence
    schemed_data['Primary data']['Test results']['raw_elongations'] = Quantity(
            Value = lisdata['data']['Dehnung']['values'],
            Unit = lisdata['data']['Dehnung']['unit'], 
            Symbol = "$\Delta L$",
            )
    schemed_data['Primary data']['Test results']['raw_times' ] = Quantity(
            Value = lisdata['data']['Zeit']['values'],
            Unit = lisdata['data']['Zeit']['unit'],
            Symbol = "t"
            )


    return schemed_data
