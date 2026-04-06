import pytest

from radrags.chunker import (
    Chunk,
    DocumentChunker,
    HEADING_LEVELS,
    RstChunker,
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
