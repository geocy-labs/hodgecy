"""Typed query specification and lazy result APIs for HodgeCY."""
from .fields import FieldMetadata, FieldRegistry, FieldWeight, hodge_field
from .predicates import FieldExpression, Predicate, Q
from .spec import Aggregation, MaterializationPolicy, OrderBy, QuerySpec
from .results import LazyResultSet

__all__ = [
    "Aggregation", "FieldExpression", "FieldMetadata", "FieldRegistry", "FieldWeight", "LazyResultSet",
    "MaterializationPolicy", "OrderBy", "Predicate", "Q", "QuerySpec", "hodge_field",
]
