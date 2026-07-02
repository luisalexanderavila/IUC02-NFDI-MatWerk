import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def Quantity(
            Symbol = '',
            Value = '',
            Unit = ''
            ):
    return dict(Value = Value, Unit = Unit, Symbol = Symbol)

def MissingQuantity():
    return Quantity(Value = 'MISSING')
