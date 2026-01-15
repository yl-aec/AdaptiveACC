"""
IFC Operations - Independent atomic functions for IFC data manipulation

This module provides low-level atomic functions for working with IFC files.
These functions are designed to be reused across different domain tools.

Modules:
- element_queries: Basic element query operations
- property_queries: Property and property set queries
- relationship_queries: Relationship and connection queries
- quantity_queries: Quantity set queries (areas, volumes, dimensions)
- geometry_queries: Geometric operations (placement, elevation, bounding box, distance)
"""

from .element_queries import *
from .property_queries import *
from .relationship_queries import *
from .quantity_queries import *
from .geometry_queries import *