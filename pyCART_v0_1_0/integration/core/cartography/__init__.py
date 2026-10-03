"""Optional repo shim. Install deepsigma-cartography before enabling this module.

Copy this directory into the host repository's src/core/cartography/. Do not
replace src/core/__init__.py or overwrite another cartography implementation.
"""
from deepsigma_cartography import *  # noqa: F401,F403
from deepsigma_cartography import __all__, __version__  # noqa: F401
