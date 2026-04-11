"""Platform adapters for the TrendR research state machine."""

from .base import PlatformAdapter
from .cli import CLIAdapter
from .openclaw import OpenClawAdapter

__all__ = ["PlatformAdapter", "CLIAdapter", "OpenClawAdapter"]
