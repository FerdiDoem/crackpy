"""Shared method metadata helpers.

This package contains small generic helpers around method identity and declared
artifacts. Numerical runners, source adapters, and result-specific projection
logic stay in their method-local modules.
"""

from crackpy.methods.definition import MethodArtifactDefinition, MethodDefinition
from crackpy.methods.contract import (
    MethodContractFixture,
    MethodContractReport,
    verify_method_module_contract,
)
from crackpy.methods.runtime import (
    MethodRunDependency,
    MethodRunIdentityPolicy,
    build_manual_crack_tip_estimate,
    build_method_run_dependencies,
)

__all__ = [
    "MethodArtifactDefinition",
    "MethodContractFixture",
    "MethodContractReport",
    "MethodDefinition",
    "MethodRunDependency",
    "MethodRunIdentityPolicy",
    "build_manual_crack_tip_estimate",
    "build_method_run_dependencies",
    "verify_method_module_contract",
]
