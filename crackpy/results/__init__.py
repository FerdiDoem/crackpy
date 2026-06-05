"""Result I/O package.

Keep this initializer passive. Shared provenance imports lightweight result
record types from this package, while plotting and writers can import fracture
analysis orchestration. Eager submodule imports would make those directions
cycle during package import.
"""
