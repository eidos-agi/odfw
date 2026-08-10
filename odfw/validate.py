"""Compatibility alias for :mod:`odwf.validate`."""

from odwf.validate import *  # noqa: F403
from odwf.validate import main


if __name__ == "__main__":
    raise SystemExit(main())
