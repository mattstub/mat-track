"""Purchase order PDF builder using ReportLab.

Supports two output modes:
  Standard PO       — includes unit prices and totals
  Field Receipt Sheet — prices suppressed, blank qty_received write-in column,
                        signature/date line at bottom
"""

from pathlib import Path


def build(po_data: dict, output_path: Path, field_receipt_mode: bool = False) -> None:
    """Write the PO PDF to output_path.

    Args:
        po_data:             Dict containing PO, line items, supplier, and project info.
        output_path:         Destination file path.
        field_receipt_mode:  If True, suppress prices and add receipt write-in column.
    """
    raise NotImplementedError
