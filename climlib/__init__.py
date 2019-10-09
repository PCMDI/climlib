"""
PCMDI custom package of helpful utilities. 

Includes these modules: 
    -- wrangle  - functions to wrangle model data
    -- io   	- functions to help read/write data
    -- util     - functions to help with uvcdat issues
    -- calc     - functions to help with calculations
    -- plot     - functions to help with plotting
    -- constant - library of constants/lookups

"""


from .wrangle import trimModelList
from .wrangle import getFileMeta


