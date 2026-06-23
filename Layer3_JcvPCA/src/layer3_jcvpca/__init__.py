"""Layer 3 JcvPCA-style comparison package (V1, Group 4 cross-repetition).

This package compares parent-child relative rotation-vector contribution
structure between a reference condition A and a comparison condition B, using a
conservative adaptation of the JcvPCA computational sequence from the paper's
``S1_File.py``.

The package is intentionally computational and auditable. It does NOT classify
changes as significant, robust, meaningful, or beyond variability. Those
judgements are made later, outside this package.
"""

from layer3_jcvpca.core import compute_jcvpca, select_selected_m_from_A

__all__ = ["compute_jcvpca", "select_selected_m_from_A"]

__version__ = "0.1.0"
