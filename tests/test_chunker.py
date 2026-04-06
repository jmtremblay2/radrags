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
