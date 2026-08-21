# Top-level package for HodgeCY.
from .config import HodgeCYConfig, HodgeCYDataRoot, open_data_root

__all__ = ["HodgeCYConfig", "HodgeCYDataRoot", "__version__", "open_data_root"]

__version__ = "0.2.0"
