"""Shared pytest fixtures for radrags tests.

Fixtures load example RST files from the cloned VyOS documentation in
``vendor/vyos-documentation/``.  If that directory is absent (the clone
script has not been run), fixtures that depend on it skip automatically.

All tests are pinned to a single VyOS documentation release tag
(``VYOS_DOCS_TAG``).  Multi-tag indexing is out of scope for now.
"""

from pathlib import Path

import pytest

#: Pinned VyOS documentation tag used for all test fixtures.
VYOS_DOCS_TAG = "1.4.3"

VENDOR_ROOT = Path(__file__).resolve().parent.parent / "vendor" / "vyos-documentation"
VYOS_DOCS = VENDOR_ROOT / "docs"


# ---------------------------------------------------------------------------
# VyOS document fixtures (skip when vendor/ is not cloned)
# ---------------------------------------------------------------------------


@pytest.fixture
def wireguard_rst() -> str:
    """Full text of the VyOS WireGuard RST page (427 lines at tag 1.4.3).

    Medium-complexity page with headings, code blocks, field lists, labels,
    and ``cmdinclude`` directives.  Used as the golden-file target for
    ``RstChunker``.
    """
    path = VYOS_DOCS / "configuration" / "interfaces" / "wireguard.rst"
    if not path.exists():
        pytest.skip("VyOS docs not cloned – run scripts/clone_vyos_docs.sh")
    return path.read_text()


@pytest.fixture
def firewall_rst() -> str:
    """Full text of the VyOS firewall index RST page (180 lines at tag 1.4.3).

    Shorter page useful for edge-case and section-splitting tests.
    """
    path = VYOS_DOCS / "configuration" / "firewall" / "index.rst"
    if not path.exists():
        pytest.skip("VyOS docs not cloned – run scripts/clone_vyos_docs.sh")
    return path.read_text()
