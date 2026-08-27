"""
r370b_packages — Package-specific engineering data for R370B dossiers.

Each module returns engineering data for one package via get_data().
The data is REAL (governing equations, external precedents, failure modes)
and HONEST (UNKNOWN stays UNKNOWN per Constitution Article XXV).
"""

from . import constants
from .p02 import get_data as p02_data
from .p04 import get_data as p04_data
from .p07 import get_data as p07_data
from .p11 import get_data as p11_data
from .p15r1 import get_data as p15r1_data
from .p21r1 import get_data as p21r1_data
from .p22r1 import get_data as p22r1_data
from .p24 import get_data as p24_data
from .p26 import get_data as p26_data
from .p27r1 import get_data as p27r1_data
from .p28 import get_data as p28_data
from .p29 import get_data as p29_data

# Registry: package_id -> data function
PACKAGE_REGISTRY = {
    "P-02": p02_data,
    "P-04": p04_data,
    "P-07": p07_data,
    "P-11": p11_data,
    "P-15-R1": p15r1_data,
    "P-21-R1": p21r1_data,
    "P-22-R1": p22r1_data,
    "P-24": p24_data,
    "P-26": p26_data,
    "P-27-R1": p27r1_data,
    "P-28": p28_data,
    "P-29": p29_data,
}

__all__ = ["PACKAGE_REGISTRY", "constants"]
