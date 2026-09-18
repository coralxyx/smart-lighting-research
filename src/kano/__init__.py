"""Reproducible Kano-inspired aggregation utilities."""

from .aggregate import build_aggregates
from .input import TaggedRecord, load_tagged_records

__all__ = ["TaggedRecord", "build_aggregates", "load_tagged_records"]
