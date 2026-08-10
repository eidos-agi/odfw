"""Compatibility entry point for ``python -m odfw``."""

from odwf.validate import main

raise SystemExit(main())
