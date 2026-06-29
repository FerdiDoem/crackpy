"""Shared method metadata helpers.

This package contains small generic helpers around method identity and declared
artifacts. Numerical runners, source adapters, and result-specific projection
logic stay in their method-local modules.
"""

from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition

__all__ = ["MethodArtifactDefinition", "MethodDefinition"]
