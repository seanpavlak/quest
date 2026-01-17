"""
BLS Data Sync Module (Compatibility Shim)

This module is maintained for backward compatibility.
New code should import directly from bls_sync, bls_parser, or bls_s3_ops.
"""

# Re-export main function for backward compatibility
from .bls_sync import sync_bls_data, BLS_BASE_URL

__all__ = ['sync_bls_data', 'BLS_BASE_URL']
