import pytest

from radrags.chunker import (
    Chunk,
    DocumentChunker,
    HEADING_LEVELS,
    RstChunker,
    chunk_docs,
    _is_adornment_line,
)


def test_chunk_fields():
    c = Chunk(
        heading="Interfaces",
        chunk_type="prose",
        text="Some content here.",
        source="configuration/interfaces/wireguard.rst",
    )
    assert c.heading == "Interfaces"
    assert c.chunk_type == "prose"
    assert c.text == "Some content here."
    assert c.source == "configuration/interfaces/wireguard.rst"


def test_rst_chunker_is_document_chunker():
    assert issubclass(RstChunker, DocumentChunker)


def test_rst_chunker_chunk_returns_list_of_chunks():
    chunker = RstChunker()
    result = chunker.chunk("")
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# 2.1 — Heading detection
# ---------------------------------------------------------------------------


class TestIsAdornmentLine:
    def test_equals(self):
        assert _is_adornment_line("=====") is True

    def test_hashes(self):
        assert _is_adornment_line("#####") is True

    def test_dashes(self):
        assert _is_adornment_line("-----") is True

    def test_tildes(self):
        assert _is_adornment_line("~~~~~") is True

    def test_empty_string_is_not_adornment(self):
        assert _is_adornment_line("") is False

    def test_mixed_chars_is_not_adornment(self):
        assert _is_adornment_line("=-==-") is False

    def test_plain_text_is_not_adornment(self):
        assert _is_adornment_line("hello") is False

    def test_single_char(self):
        assert _is_adornment_line("=") is True


class TestHeadingLevels:
    def test_hash_is_level_1(self):
        assert HEADING_LEVELS["#"] == 1

    def test_equals_is_level_2(self):
        assert HEADING_LEVELS["="] == 2

    def test_star_is_level_2(self):
        assert HEADING_LEVELS["*"] == 2

    def test_dash_is_level_3(self):
        assert HEADING_LEVELS["-"] == 3

    def test_tilde_is_level_4(self):
        assert HEADING_LEVELS["~"] == 4

    def test_caret_is_level_5(self):
        assert HEADING_LEVELS["^"] == 5

    def test_double_quote_is_level_6(self):
        assert HEADING_LEVELS['"'] == 6


class TestHeadingAt:
    """Tests for RstChunker._heading_at()."""

    def setup_method(self):
        self.chunker = RstChunker()

    # -- Form 1: title + underline ------------------------------------

    def test_form1_equals(self):
        lines = ["WireGuard", "=========", "some prose"]
        result = self.chunker._heading_at(lines, 0)
        assert result == (2, "WireGuard", 2)

    def test_form1_dashes(self):
        lines = ["Keypairs", "--------"]
        result = self.chunker._heading_at(lines, 0)
        assert result == (3, "Keypairs", 2)

    def test_form1_tildes(self):
        lines = ["Details", "~~~~~~~"]
        result = self.chunker._heading_at(lines, 0)
        assert result == (4, "Details", 2)

    # -- Form 2: overline + title + underline -------------------------

    def test_form2_hashes(self):
        lines = ["##########", "My Section", "##########"]
        result = self.chunker._heading_at(lines, 0)
        assert result == (1, "My Section", 3)

    def test_form2_equals(self):
        lines = ["==========", "My Section", "=========="]
        result = self.chunker._heading_at(lines, 0)
        assert result == (2, "My Section", 3)

    # -- Edge cases ---------------------------------------------------

    def test_underline_too_short_returns_none(self):
        lines = ["WireGuard", "==="]
        result = self.chunker._heading_at(lines, 0)
        assert result is None

    def test_unknown_adornment_char_returns_none(self):
        lines = ["WireGuard", "%%%%%%%%%"]
        result = self.chunker._heading_at(lines, 0)
        assert result is None

    def test_not_at_heading_returns_none(self):
        lines = ["just some prose", "more prose"]
        result = self.chunker._heading_at(lines, 0)
        assert result is None

    def test_form2_mismatched_over_under_returns_none(self):
        lines = ["==========", "My Section", "----------"]
        result = self.chunker._heading_at(lines, 0)
        assert result is None

    def test_heading_at_end_of_lines(self):
        lines = ["WireGuard"]
        result = self.chunker._heading_at(lines, 0)
        assert result is None

    def test_form1_at_nonzero_index(self):
        lines = ["intro", "WireGuard", "========="]
        result = self.chunker._heading_at(lines, 1)
        assert result == (2, "WireGuard", 2)

    def test_scanning_a_realistic_rst_document(self):
        """Walk a small RST document and collect every heading the way the
        section splitter will — this shows the full picture of what
        _heading_at does in practice.

        The document below uses three heading levels:

            ##########          <- Form 2 (overline+title+underline) → level 1
            VPN Guide
            ##########

            WireGuard           <- Form 1 (title+underline with =)  → level 2
            =========

            Keypairs            <- Form 1 (title+underline with -)  → level 3
            --------
        """
        doc = [
            "##########",  # 0  overline
            "VPN Guide",  # 1  title
            "##########",  # 2  underline
            "",  # 3
            "Some intro prose.",  # 4
            "",  # 5
            "WireGuard",  # 6  title
            "=========",  # 7  underline
            "",  # 8
            "WireGuard is a fast VPN tunnel.",  # 9
            "",  # 10
            "Keypairs",  # 11 title
            "--------",  # 12 underline
            "",  # 13
            "Generate keys with wg genkey.",  # 14
        ]

        # Scan every line, just like the section splitter does.
        headings = []
        i = 0
        while i < len(doc):
            result = self.chunker._heading_at(doc, i)
            if result is not None:
                level, title, consumed = result
                headings.append((level, title))
                i += consumed  # skip past the heading lines
            else:
                i += 1

        assert headings == [
            (1, "VPN Guide"),  # Form 2 — # is level 1
            (2, "WireGuard"),  # Form 1 — = is level 2
            (3, "Keypairs"),  # Form 1 — - is level 3
        ]


# ---------------------------------------------------------------------------
# 2.2 — Section splitting
# ---------------------------------------------------------------------------


class TestSplitSections:
    """Tests for RstChunker._split_sections()."""

    def setup_method(self):
        self.chunker = RstChunker()

    def test_empty_document_returns_empty(self):
        assert self.chunker._split_sections([]) == []

    def test_prose_before_any_heading(self):
        """Content before the first heading gets an empty heading path."""
        lines = ["Some intro text.", "", "More intro."]
        sections = self.chunker._split_sections(lines)
        assert len(sections) == 1
        path, blocks = sections[0]
        assert path == []
        assert any("Some intro text." in b for b in blocks)

    def test_single_heading_collects_prose(self):
        lines = [
            "WireGuard",
            "=========",
            "",
            "WireGuard is a fast VPN.",
        ]
        sections = self.chunker._split_sections(lines)
        assert len(sections) == 1
        path, blocks = sections[0]
        assert path == ["WireGuard"]
        assert any("WireGuard is a fast VPN." in b for b in blocks)

    def test_two_sibling_headings(self):
        """Two headings at the same level produce two separate sections."""
        lines = [
            "WireGuard",
            "=========",
            "",
            "VPN tunnel.",
            "",
            "OpenVPN",
            "=======",
            "",
            "SSL-based VPN.",
        ]
        sections = self.chunker._split_sections(lines)
        assert len(sections) == 2
        assert sections[0][0] == ["WireGuard"]
        assert sections[1][0] == ["OpenVPN"]
        assert any("VPN tunnel." in b for b in sections[0][1])
        assert any("SSL-based VPN." in b for b in sections[1][1])

    def test_nested_heading_builds_path(self):
        """A child heading includes its parent in the heading path."""
        lines = [
            "WireGuard",
            "=========",
            "",
            "Overview.",
            "",
            "Keypairs",
            "--------",
            "",
            "Generate keys.",
        ]
        sections = self.chunker._split_sections(lines)
        assert len(sections) == 2
        assert sections[0][0] == ["WireGuard"]
        assert sections[1][0] == ["WireGuard", "Keypairs"]

    def test_sibling_after_child_pops_stack(self):
        """When a sibling appears after a nested child, the stack pops back."""
        lines = [
            "##########",
            "VPN Guide",
            "##########",
            "",
            "Intro.",
            "",
            "WireGuard",
            "=========",
            "",
            "Fast VPN.",
            "",
            "Keypairs",
            "--------",
            "",
            "Generate keys.",
            "",
            "OpenVPN",
            "=======",
            "",
            "SSL VPN.",
        ]
        sections = self.chunker._split_sections(lines)
        paths = [s[0] for s in sections]
        assert paths == [
            ["VPN Guide"],
            ["VPN Guide", "WireGuard"],
            ["VPN Guide", "WireGuard", "Keypairs"],
            ["VPN Guide", "OpenVPN"],
        ]

    def test_heading_only_section_no_prose(self):
        """A heading with no prose below it still produces no section
        (nothing to chunk)."""
        lines = [
            "WireGuard",
            "=========",
            "Keypairs",
            "--------",
            "",
            "Generate keys.",
        ]
        sections = self.chunker._split_sections(lines)
        # WireGuard has no prose — should not appear as a section
        # Only Keypairs with its prose should appear
        paths = [s[0] for s in sections]
        assert ["WireGuard", "Keypairs"] in paths
        for path, blocks in sections:
            assert len(blocks) > 0, f"Section {path} has no content blocks"


# ---------------------------------------------------------------------------
# 2.3 — Metadata filtering
# ---------------------------------------------------------------------------


class TestIsMetadataOnly:
    """Tests for RstChunker._is_metadata_only()."""

    def setup_method(self):
        self.chunker = RstChunker()

    # -- Positive cases: should be detected as metadata ----------------

    def test_empty_block(self):
        assert self.chunker._is_metadata_only("") is True

    def test_whitespace_only(self):
        assert self.chunker._is_metadata_only("   \n  \n") is True

    def test_field_list(self):
        assert self.chunker._is_metadata_only(":lastproofread: 2023-01-26") is True

    def test_rst_label(self):
        assert self.chunker._is_metadata_only(".. _wireguard:") is True

    def test_anonymous_target(self):
        assert self.chunker._is_metadata_only("__ https://example.com") is True

    def test_figure_directive(self):
        assert (
            self.chunker._is_metadata_only(
                ".. figure:: /_static/images/wireguard_site2site_diagram.jpg"
            )
            is True
        )

    def test_image_directive(self):
        assert (
            self.chunker._is_metadata_only(".. image:: /_static/images/logo.png")
            is True
        )

    # -- Negative cases: real content, must NOT be filtered -------------

    def test_prose_paragraph(self):
        assert (
            self.chunker._is_metadata_only(
                "WireGuard is an extremely simple yet fast VPN."
            )
            is False
        )

    def test_opcmd_directive(self):
        assert (
            self.chunker._is_metadata_only(".. opcmd:: show interfaces wireguard")
            is False
        )

    def test_cfgcmd_directive(self):
        assert (
            self.chunker._is_metadata_only(".. cfgcmd:: set interfaces wireguard wg0")
            is False
        )

    def test_code_block_directive(self):
        assert (
            self.chunker._is_metadata_only(".. code-block:: none\n\n   some code")
            is False
        )


# ---------------------------------------------------------------------------
# 2.4 — Prose-code pairing
# ---------------------------------------------------------------------------


class TestPairProseWithCode:
    """Tests for RstChunker._pair_prose_with_code()."""

    def setup_method(self):
        self.chunker = RstChunker()

    def test_prose_then_code_merges(self):
        blocks = [
            "Install the key with this command:",
            ".. code-block:: shell\n\n   set interfaces wireguard wg0",
        ]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 1
        assert flags[0] is True
        assert "Install the key" in paired[0]
        assert "code-block" in paired[0]

    def test_prose_only_not_paired(self):
        blocks = ["Just some prose.", "More prose."]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 2
        assert flags == [False, False]

    def test_code_only_not_paired(self):
        blocks = [".. code-block:: shell\n\n   echo hello"]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 1
        assert flags == [False]

    def test_two_prose_code_pairs(self):
        blocks = [
            "First explanation.",
            ".. code-block:: shell\n\n   cmd1",
            "Second explanation.",
            ".. code-block:: shell\n\n   cmd2",
        ]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 2
        assert flags == [True, True]

    def test_prose_code_prose_trailing(self):
        blocks = [
            "Explanation.",
            ".. code-block:: shell\n\n   cmd1",
            "Trailing prose.",
        ]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 2
        assert flags == [True, False]

    def test_parsed_literal_pairs(self):
        blocks = [
            "Output example:",
            ".. parsed-literal::\n\n   some output",
        ]
        paired, flags = self.chunker._pair_prose_with_code(blocks)
        assert len(paired) == 1
        assert flags[0] is True


# ---------------------------------------------------------------------------
# 2.5 — Prose splitting
# ---------------------------------------------------------------------------


class TestSplitProseBlock:
    """Tests for RstChunker._split_prose_block()."""

    def test_short_block_stays_whole(self):
        chunker = RstChunker(chunk_size=200, chunk_overlap=20)
        pieces = chunker._split_prose_block("A short paragraph.")
        assert pieces == ["A short paragraph."]

    def test_two_paragraphs_within_limit(self):
        chunker = RstChunker(chunk_size=200, chunk_overlap=20)
        text = "First paragraph.\n\nSecond paragraph."
        pieces = chunker._split_prose_block(text)
        assert len(pieces) == 1
        assert "First" in pieces[0] and "Second" in pieces[0]

    def test_splits_at_paragraph_boundary(self):
        chunker = RstChunker(chunk_size=50, chunk_overlap=10)
        text = "A" * 40 + "\n\n" + "B" * 40
        pieces = chunker._split_prose_block(text)
        assert len(pieces) == 2
        assert pieces[0].strip() == "A" * 40
        assert pieces[1].strip() == "B" * 40

    def test_hard_splits_oversized_paragraph(self):
        chunker = RstChunker(chunk_size=50, chunk_overlap=10)
        text = " ".join(["word"] * 50)  # ~250 chars, single paragraph
        pieces = chunker._split_prose_block(text)
        assert len(pieces) > 1
        assert all(len(p) <= 60 for p in pieces)  # some tolerance

    def test_empty_text_returns_empty(self):
        chunker = RstChunker(chunk_size=200, chunk_overlap=20)
        assert chunker._split_prose_block("") == []

    def test_overlap_between_hard_split_pieces(self):
        chunker = RstChunker(chunk_size=50, chunk_overlap=15)
        text = " ".join(["word"] * 50)
        pieces = chunker._split_prose_block(text)
        # Consecutive pieces should share some text (overlap)
        for i in range(len(pieces) - 1):
            tail = pieces[i][-15:]
            assert tail in pieces[i + 1] or pieces[i + 1].startswith(
                tail.lstrip()
            ), f"No overlap between piece {i} and {i + 1}"


# ---------------------------------------------------------------------------
# 2.6 — Small chunk merging
# ---------------------------------------------------------------------------


class TestMergeSmallChunks:
    """Tests for RstChunker._merge_small_chunks()."""

    def setup_method(self):
        self.chunker = RstChunker()

    def test_no_small_chunks_unchanged(self):
        chunks = [
            Chunk("WireGuard", "prose", "A" * 400, "src.rst"),
            Chunk("Keypairs", "prose", "B" * 400, "src.rst"),
        ]
        result = self.chunker._merge_small_chunks(chunks, min_size=300)
        assert len(result) == 2

    def test_small_chunk_merges_backward(self):
        chunks = [
            Chunk("WireGuard", "prose", "A" * 400, "src.rst"),
            Chunk("WireGuard", "prose", "Tiny.", "src.rst"),
        ]
        result = self.chunker._merge_small_chunks(chunks, min_size=300)
        assert len(result) == 1
        assert "Tiny." in result[0].text
        # Heading preserved from the earlier (preceding) chunk
        assert result[0].heading == "WireGuard"

    def test_first_tiny_chunk_merges_forward(self):
        chunks = [
            Chunk("Intro", "prose", "Hi.", "src.rst"),
            Chunk("WireGuard", "prose", "B" * 400, "src.rst"),
        ]
        result = self.chunker._merge_small_chunks(chunks, min_size=300)
        assert len(result) == 1
        assert "Hi." in result[0].text

    def test_single_chunk_returned_as_is(self):
        chunks = [Chunk("WireGuard", "prose", "Short.", "src.rst")]
        result = self.chunker._merge_small_chunks(chunks, min_size=300)
        assert len(result) == 1
        assert result[0].text == "Short."

    def test_empty_list(self):
        assert self.chunker._merge_small_chunks([], min_size=300) == []

    def test_multiple_small_chunks_merge_into_predecessor(self):
        chunks = [
            Chunk("A", "prose", "X" * 400, "src.rst"),
            Chunk("A", "prose", "tiny1", "src.rst"),
            Chunk("A", "prose", "tiny2", "src.rst"),
        ]
        result = self.chunker._merge_small_chunks(chunks, min_size=300)
        assert len(result) == 1
        assert "tiny1" in result[0].text
        assert "tiny2" in result[0].text


# ---------------------------------------------------------------------------
# 2.7 — Full RstChunker + golden fixture
# ---------------------------------------------------------------------------

import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


class TestRstChunkerGolden:
    """End-to-end test against the real VyOS WireGuard RST page."""

    def test_wireguard_matches_golden_fixture(self, wireguard_rst):
        fixture_path = FIXTURE_DIR / "wireguard_chunks.json"
        if not fixture_path.exists():
            pytest.skip("Golden fixture not yet generated")

        expected = json.loads(fixture_path.read_text())
        chunker = RstChunker()
        chunks = chunker.chunk(wireguard_rst)

        actual = [
            {"heading": c.heading, "type": c.chunk_type, "text": c.text} for c in chunks
        ]

        assert len(actual) == len(
            expected
        ), f"Chunk count mismatch: got {len(actual)}, expected {len(expected)}"

        for i, (act, exp) in enumerate(zip(actual, expected)):
            assert (
                act["heading"] == exp["heading"]
            ), f"Chunk {i} heading mismatch: {act['heading']!r} != {exp['heading']!r}"
            assert (
                act["type"] == exp["type"]
            ), f"Chunk {i} type mismatch: {act['type']!r} != {exp['type']!r}"
            assert act["text"] == exp["text"], (
                f"Chunk {i} text mismatch (first 80 chars):\n"
                f"  got:      {act['text'][:80]!r}\n"
                f"  expected: {exp['text'][:80]!r}"
            )


# ---------------------------------------------------------------------------
# Integration — end-to-end chunking demonstration
# ---------------------------------------------------------------------------

#: A small RST document adapted from the VyOS WireGuard page.
#: Uses three heading levels to exercise the full RstChunker pipeline:
#: Form 2 (``#`` overline+underline) for the document title,
#: Form 1 (``=`` underline) for a section, and
#: Form 1 (``-`` underline) for a subsection.
SAMPLE_RST = """\
#########
WireGuard
#########

WireGuard is a simple yet fast VPN that uses state-of-the-art
cryptography. It aims to be faster and simpler than IPsec while
being considerably more performant than OpenVPN. WireGuard is
designed as a general-purpose VPN for running on embedded
interfaces and super computers alike, fit for many different
circumstances. It runs over UDP and can be configured with a
handful of commands. See https://www.wireguard.com for more
information about the protocol.

Generate Keypair
================

WireGuard requires the generation of a keypair. The private key
is used to decrypt incoming traffic, and the public key is shared
with peer(s) so they can encrypt outgoing traffic destined for
this host. Keys are generated locally and never leave the device
unless explicitly exported by the administrator.

.. code-block:: shell

   $ generate pki wireguard key-pair
   Private key: iJJyEARGK52Ls1GYRCcFvPuTj7WyWYDo//BknoDU0XY=
   Public key: EKY0dxRrSD98QHjfHOK13mZ5PJ7hnddRZt5woB3szyw=

Server Configuration
--------------------

Each side of the WireGuard tunnel needs a private key and the
public key of its remote peer. Configure the local interface
address and the peer endpoint. The listen-port is optional;
WireGuard will select a random port if it is not set. Peers
are added with their public key and the allowed IP ranges
that should be routed through the tunnel.
"""


def test_rst_chunker_end_to_end():
    """Chunk a short RST document and verify every field of every chunk.

    This test exercises the complete `RstChunker` pipeline on a small
    document adapted from the VyOS WireGuard page.  The document uses
    three heading levels and a code block:

    ```rst
    #########
    WireGuard
    #########

    WireGuard is a simple yet fast VPN ...

    Generate Keypair
    ================

    WireGuard requires the generation of a keypair ...

    .. code-block:: shell

       $ generate pki wireguard key-pair
       Private key: iJJy...
       Public key: EKY0...

    Server Configuration
    --------------------

    Each side of the WireGuard tunnel needs a private key ...
    ```

    The chunker produces **three chunks** from this input:

    | Chunk | Heading | Type |
    |-------|---------|------|
    | 0 | `WireGuard` | prose |
    | 1 | `WireGuard > Generate Keypair` | prose |
    | 2 | `WireGuard > Generate Keypair > Server Configuration` | prose |

    Key behaviours demonstrated:

    - **Heading hierarchy** — child sections carry their full ancestor
      path joined by ` > ` (e.g. `WireGuard > Generate Keypair`).
    - **Prose-code pairing** — the code block under *Generate Keypair*
      is merged into its preceding prose chunk rather than split into
      a separate code-only chunk, keeping explanation and example together.
    - **Section boundaries** — each heading starts a new chunk; prose
      below a heading belongs to that chunk until the next heading.
    """
    chunker = RstChunker()
    chunks = chunker.chunk(SAMPLE_RST)

    assert len(chunks) == 3

    # -- Chunk 0: document-level prose under the top heading ---------------
    c0 = chunks[0]
    assert c0.heading == "WireGuard"
    assert c0.chunk_type == "prose"
    assert c0.text == (
        "WireGuard is a simple yet fast VPN that uses state-of-the-art\n"
        "cryptography. It aims to be faster and simpler than IPsec while\n"
        "being considerably more performant than OpenVPN. WireGuard is\n"
        "designed as a general-purpose VPN for running on embedded\n"
        "interfaces and super computers alike, fit for many different\n"
        "circumstances. It runs over UDP and can be configured with a\n"
        "handful of commands. See https://www.wireguard.com for more\n"
        "information about the protocol."
    )
    assert c0.source == ""

    # -- Chunk 1: prose + code block paired together -----------------------
    c1 = chunks[1]
    assert c1.heading == "WireGuard > Generate Keypair"
    assert c1.chunk_type == "prose"
    assert "keypair" in c1.text.lower()
    assert ".. code-block:: shell" in c1.text
    assert "generate pki wireguard key-pair" in c1.text
    assert c1.source == ""

    # -- Chunk 2: subsection prose -----------------------------------------
    c2 = chunks[2]
    assert c2.heading == "WireGuard > Generate Keypair > Server Configuration"
    assert c2.chunk_type == "prose"
    assert "private key" in c2.text
    assert "listen-port" in c2.text
    assert c2.source == ""


# ---------------------------------------------------------------------------
# 3.1 — Discover RST files (chunk_docs)
# ---------------------------------------------------------------------------

VYOS_DOCS = (
    Path(__file__).resolve().parent.parent / "vendor" / "vyos-documentation" / "docs"
)


class TestChunkDocs:
    """Tests for chunk_docs() doc-tree traversal."""

    def test_returns_non_empty_list_of_chunks(self):
        """chunk_docs on the VyOS docs tree returns a non-empty list."""
        if not VYOS_DOCS.exists():
            pytest.skip("VyOS docs not cloned – run scripts/clone_vyos_docs.sh")
        chunks = chunk_docs(VYOS_DOCS)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_every_chunk_has_non_empty_source(self):
        """Every chunk returned by chunk_docs has a non-empty source field."""
        if not VYOS_DOCS.exists():
            pytest.skip("VyOS docs not cloned – run scripts/clone_vyos_docs.sh")
        chunks = chunk_docs(VYOS_DOCS)
        for c in chunks:
            assert c.source, f"Chunk has empty source: heading={c.heading!r}"

    def test_all_sources_end_with_rst(self):
        """Every chunk's source field ends with .rst."""
        if not VYOS_DOCS.exists():
            pytest.skip("VyOS docs not cloned – run scripts/clone_vyos_docs.sh")
        chunks = chunk_docs(VYOS_DOCS)
        for c in chunks:
            assert c.source.endswith(".rst"), f"Bad source: {c.source!r}"
