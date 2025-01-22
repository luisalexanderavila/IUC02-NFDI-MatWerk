import os
import pandas as pd
import json 

def get_string(row_cell):
    if isinstance(row_cell, str):
        return row_cell
    else:
        return '' 

class SchemaUpdater(object):
    """ this is a simple class to get the latest schema from an excel file """

    def __init__(
            self, 
            excel_file = '../Data Schema IUC02/2023_Creep-Data-Structure_IUC02.xlsx', 
            sheet_name = '2023-26-05',
            header = '6'
            ):
        """ initiate the schema updater from a given excel file """

        self.excel_file = excel_file
        self.sheet_name = sheet_name
        self.header = header


        schema_xls = pd.read_excel(
                '../Data Schema IUC02/2023_Creep-Data-Structure_IUC02.xlsx', sheet_name='2023-26-05', header=6, 
                )
        schema_creep_test = {}
        for index, row in schema_xls.iterrows():
            this_item = {
                    row['ITEM EN'] :
                    {
                        'Symbol' : get_string(row['Symbol'],),
                        'Unit' : get_string(row['Unit'],),
                        'Value' : '', # this should depend on a defined Type
                        }
                    }
            this_category_I = row['Category I - EN']
            if isinstance(this_category_I, str):
                if this_category_I not in schema_creep_test.keys():
                    schema_creep_test.update( { this_category_I  : {} } )
            this_category_II = row['Category II - EN']
            if isinstance(this_category_II, str):
                if this_category_II not in schema_creep_test[this_category_I].keys():
                    schema_creep_test[this_category_I].update( { this_category_II :  {} } )
            this_category_III = row['Category III - EN']
            if isinstance(this_category_III, str):
                if this_category_III not in schema_creep_test[this_category_I][this_category_II].keys():
                    schema_creep_test[this_category_I][this_category_II][this_category_III]={}
                schema_creep_test[this_category_I][this_category_II][this_category_III].update(this_item)
            else:
                schema_creep_test[this_category_I][this_category_II].update(this_item)
        
        self.schema_creep_test = schema_creep_test


    def dump_json(self, json_file = None):
        if json_file is None:
            self.json_file = os.path.join(os.path.dirname(self.excel_file), 'schema_creep_test.json') 
        else:
            self.json_file = json_file

        with open(self.json_file, 'w') as f:
            json.dump(self.schema_creep_test, f,  indent=4, allow_nan=True)

