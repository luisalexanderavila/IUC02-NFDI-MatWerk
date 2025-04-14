import os
import sys
sys.path.insert (0, os.path.dirname(os.path.dirname(__file__)))
from Tools.Metainfo.metainfo import MissingQuantity

import pandas as pd

def make_df_values ( compliant_json : dict) -> pd.core.frame.DataFrame: 
    """
    converts a json which is compliant with the schema to a pandas dataframe, 
    where the categories are expressed as multiindex and values are in columns 
    """

    multilevel_dict = {}
    for outerkey, outerdict in compliant_json.items():
        for innerkey, innerdict in outerdict.items():
            for lastkey, lastdict in innerdict.items():
                for itemname, itemdef in lastdict.items():
                    if not isinstance(itemdef, dict):
                        itemdef = MissingQuantity()
                    multilevel_dict[(outerkey, innerkey, lastkey, itemname)] = itemdef
    return pd.DataFrame.from_dict(multilevel_dict, orient='index', )
