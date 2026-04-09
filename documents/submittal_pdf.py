"""Submittal package PDF builder using ReportLab.

Receives plain data objects (not DB connections) so this module is
reusable in a web context during ProManage migration.

Output structure:
  Page 1:  Cover sheet (company logo, project info, stamp boxes)
  Page 2:  Table of contents (tag | description | manufacturer | model | qty)
  Page 3+: Section divider + cut sheet PDFs per fixture group
"""

from pathlib import Path


def build(package_data: dict, output_path: Path) -> None:
    """Write the submittal package PDF to output_path.

    Args:
        package_data: Dict containing package, fixture_groups, materials,
                      project, and company info assembled by document_builder.py.
        output_path:  Destination file path.
    """
    raise NotImplementedError
