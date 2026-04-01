"""Platform adapters for the TrendR research state machine."""

from .base import PlatformAdapter
from .cli import CLIAdapter

__all__ = ["PlatformAdapter", "CLIAdapter"]
