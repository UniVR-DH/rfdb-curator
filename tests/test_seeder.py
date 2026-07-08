"""Unit tests for the startup data seeder.

Covers the vocab_paths list handling added in the Glottolog language dropdown feature:
- bare string VOCAB_PATH is auto-wrapped in a list by the config validator
- JSON array with one path seeds one file
- JSON array with two paths seeds both files
- a missing file returns loaded=False without raising
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_oxigraph_stub():
    """Return a minimal Oxigraph stub that records load_turtle calls."""
    stub = MagicMock()
    stub.load_turtle = MagicMock()
    return stub


# ---------------------------------------------------------------------------
# Config validator: parse_vocab_paths
# ---------------------------------------------------------------------------


class TestParseVocabPaths:
    """Tests for Settings.parse_vocab_paths field validator."""

    def setup_method(self):
        # Re-import with a clean environment for each test.
        sys.modules.pop("core.config", None)
        sys.modules.pop("config", None)

    def _make_settings(self, vocab_path_value: str, monkeypatch):
        monkeypatch.setenv("OXIGRAPH_URL", "http://localhost:7878")
        monkeypatch.setenv("DATA_GRAPH_URI", "https://rfdb.it/graph/data")
        monkeypatch.setenv("SCHEMA_PATH", "schema/schema.ttl")
        monkeypatch.setenv("VOCAB_PATH", vocab_path_value)
        monkeypatch.setenv("DATA_PATH", "data/data.ttl")
        monkeypatch.setenv("RESET_DATA_ON_STARTUP", "false")
        monkeypatch.setenv("SEED_VOCAB_ON_STARTUP", "false")
        monkeypatch.setenv("SEED_TEST_DATA_ON_STARTUP", "false")
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')
        sys.modules.pop("core.config", None)
        config_mod = importlib.import_module("core.config")
        # Re-instantiate Settings with the patched env.
        return config_mod.Settings()

    def test_bare_string_is_wrapped_in_list(self, monkeypatch):
        """A JSON array with one element produces a single-element list."""
        settings = self._make_settings('["data/vocab.ttl"]', monkeypatch)
        assert settings.vocab_paths == ["data/vocab.ttl"]

    def test_json_array_single_path(self, monkeypatch):
        """A JSON array with one path is parsed correctly."""
        settings = self._make_settings('["data/vocab.ttl"]', monkeypatch)
        assert settings.vocab_paths == ["data/vocab.ttl"]

    def test_json_array_two_paths(self, monkeypatch):
        """A JSON array with two paths is parsed correctly."""
        settings = self._make_settings(
            '["data/vocab.ttl", "data/glottolog_language.ttl"]', monkeypatch
        )
        assert settings.vocab_paths == ["data/vocab.ttl", "data/glottolog_language.ttl"]


# ---------------------------------------------------------------------------
# seed_store: iterates all vocab_paths
# ---------------------------------------------------------------------------


class TestSeedStore:
    """Tests for seed_store() with vocab_paths list."""

    def setup_method(self):
        sys.modules.pop("core.seeder", None)

    def _import_seeder(self):
        return importlib.import_module("core.seeder")

    def test_missing_file_returns_loaded_false(self, tmp_path):
        """A path that does not exist produces loaded=False without raising."""
        seeder = self._import_seeder()
        ox = _make_oxigraph_stub()
        missing = str(tmp_path / "nonexistent.ttl")

        report = seeder.seed_store(
            oxigraph=ox,
            vocab_paths=[missing],
            test_data_path=str(tmp_path / "data.ttl"),
            seed_vocab=True,
            seed_test_data=False,
        )

        assert report["results"][0]["loaded"] is False
        assert report["results"][0]["reason"] == "missing"
        ox.load_turtle.assert_not_called()

    def test_single_vocab_path_is_loaded(self, tmp_path):
        """A single path in vocab_paths is loaded once."""
        vocab = tmp_path / "vocab.ttl"
        vocab.write_text("@prefix ex: <http://example.org/> .\n", encoding="utf-8")

        seeder = self._import_seeder()
        ox = _make_oxigraph_stub()

        report = seeder.seed_store(
            oxigraph=ox,
            vocab_paths=[str(vocab)],
            test_data_path=str(tmp_path / "data.ttl"),
            seed_vocab=True,
            seed_test_data=False,
        )

        assert len(report["results"]) == 1
        assert report["results"][0]["loaded"] is True
        ox.load_turtle.assert_called_once()

    def test_two_vocab_paths_both_loaded(self, tmp_path):
        """Two paths in vocab_paths are each loaded once."""
        v1 = tmp_path / "vocab.ttl"
        v2 = tmp_path / "glottolog.ttl"
        v1.write_text("@prefix ex: <http://example.org/> .\n", encoding="utf-8")
        v2.write_text("@prefix gl: <http://glottolog.org/> .\n", encoding="utf-8")

        seeder = self._import_seeder()
        ox = _make_oxigraph_stub()

        report = seeder.seed_store(
            oxigraph=ox,
            vocab_paths=[str(v1), str(v2)],
            test_data_path=str(tmp_path / "data.ttl"),
            seed_vocab=True,
            seed_test_data=False,
        )

        assert len(report["results"]) == 2
        assert all(r["loaded"] is True for r in report["results"])
        assert ox.load_turtle.call_count == 2

    def test_seed_vocab_false_skips_all_vocab_paths(self, tmp_path):
        """When seed_vocab=False, no vocab files are loaded regardless of the list."""
        vocab = tmp_path / "vocab.ttl"
        vocab.write_text("@prefix ex: <http://example.org/> .\n", encoding="utf-8")

        seeder = self._import_seeder()
        ox = _make_oxigraph_stub()

        report = seeder.seed_store(
            oxigraph=ox,
            vocab_paths=[str(vocab)],
            test_data_path=str(tmp_path / "data.ttl"),
            seed_vocab=False,
            seed_test_data=False,
        )

        assert report["results"] == []
        ox.load_turtle.assert_not_called()
