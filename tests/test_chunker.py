import pytest
from pathlib import Path

from app.core.chunker import DocumentChunker


class TestDocumentChunker:
    def test_init(self):
        chunker = DocumentChunker()
        assert chunker.speakers == ["Dhritirashtra:", "Sanjaya:", "Arjuna:", "Krishna:"]

    def test_extract_speaker(self):
        chunker = DocumentChunker()
        assert chunker._extract_speaker("Krishna: Listen Arjuna") == "Krishna"
        assert chunker._extract_speaker("Arjuna: I am confused") == "Arjuna"
        assert chunker._extract_speaker("Unknown text") == "Unknown"

    def test_clean_text(self):
        chunker = DocumentChunker()
        text = "Hello   world  [FN#1] test"
        assert chunker._clean_text(text) == "Hello world test"

    def test_get_chapter_number(self):
        chunker = DocumentChunker()
        assert chunker._get_chapter_number("CHAPTER I") == 1
        assert chunker._get_chapter_number("CHAPTER II") == 2
        assert chunker._get_chapter_number("CHAPTER X") == 10
        assert chunker._get_chapter_number("CHAPTER XVIII") == 18
        assert chunker._get_chapter_number("No chapter") == 0

    def test_process_documentation(self, tmp_path):
        chunker = DocumentChunker()
        # Create a small test markdown file
        test_file = tmp_path / "test_gita.md"
        test_file.write_text(
            "# Title\n\n### **CHAPTER I**\n\nKrishna: Test verse one.\n\nArjuna: Test verse two.\n\n"
        )
        chunks = chunker.process_documentation(str(test_file))
        assert len(chunks) > 0
        assert any(c["type"] == "verse" for c in chunks)
