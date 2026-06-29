"""Shared method metadata helpers.

This package contains small generic helpers around method identity and declared
artifacts. Numerical runners, source adapters, and result-specific projection
logic stay in their method-local modules.
"""

from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition
from crackpy.methods.runtime import (
    MethodRunDependency,
    MethodRunIdentityPolicy,
    build_manual_crack_tip_estimate,
    build_method_run_dependencies,
)

__all__ = [
    "MethodArtifactDefinition",
    "MethodDefinition",
    "MethodRunDependency",
    "MethodRunIdentityPolicy",
    "build_manual_crack_tip_estimate",
    "build_method_run_dependencies",
]
