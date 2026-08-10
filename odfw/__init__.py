"""Compatibility alias for the former ``odfw`` package name."""

from odwf import ODWF_VERSION, OKF_VERSION, __version__

ODFW_VERSION = ODWF_VERSION

__all__ = ["ODFW_VERSION", "ODWF_VERSION", "OKF_VERSION", "__version__"]
