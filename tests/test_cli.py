"""Tests for scraper.cli."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import click.testing

from scraper.cli import (
    _collect_dates,
    _find_division_info,
    _make_slug,
    _update_index,
    _write_output,
    scrape,
)
from scraper.models import Division, Match, Pool, Round, Team


class TestMakeSlug:
    """Tests for _make_slug."""

    def test_simple(self) -> None:
        """Test basic division name slug conversion."""
        assert _make_slug("14s Power League") == "14s-power-league"

    def test_slashes(self) -> None:
        """Test slash replacement in slug."""
        assert _make_slug("Gold/Silver") == "gold-silver"

    def test_mixed_case(self) -> None:
        """Test mixed case is lowercased."""
        assert _make_slug("Boys 18U") == "boys-18u"

    def test_multiple_spaces(self) -> None:
        """Test multiple spaces are collapsed."""
        assert _make_slug("Men's  Club  Nationals") == "men's--club--nationals"


class TestFindDivisionInfo:
    """Tests for _find_division_info."""

    def test_found(self) -> None:
        """Test extracting info from found division."""
        event = {
            "Divisions": [
                {
                    "DivisionId": 123,
                    "Name": "14s",
                    "ColorHex": "#FF0000",
                    "CodeAlias": "14s",
                }
            ]
        }
        name, color, code = _find_division_info(event, 123)
        assert name == "14s"
        assert color == "#FF0000"
        assert code == "14s"

    def test_not_found(self) -> None:
        """Test default values when division not found."""
        name, color, code = _find_division_info({"Divisions": []}, 999)
        assert name == "Division 999"
        assert color == ""
        assert code == ""

    def test_partial_fields(self) -> None:
        """Test extraction with missing optional fields."""
        event = {
            "Divisions": [
                {
                    "DivisionId": 100,
                    "Name": "18s Open",
                }
            ]
        }
        name, color, code = _find_division_info(event, 100)
        assert name == "18s Open"
        assert color == ""
        assert code == ""

    def test_empty_divisions_list(self) -> None:
        """Test with empty divisions list."""
        name, color, code = _find_division_info({"Divisions": []}, 123)
        assert name == "Division 123"
        assert color == ""
        assert code == ""

    def test_none_divisions(self) -> None:
        """Test with None divisions field."""
        name, color, code = _find_division_info({"Divisions": None}, 123)
        assert name == "Division 123"


class TestCollectDates:
    """Tests for _collect_dates."""

    def test_collects_unique_dates(self) -> None:
        """Test collection of unique dates from pools."""
        division = Division(id=1, name="Test")
        pool = Pool(play_id=1, name="Pool A")
        pool.matches = [
            Match(id=1, date="2025-03-08"),
            Match(id=2, date="2025-03-08"),
            Match(id=3, date="2025-03-09"),
        ]
        division.pools = [pool]

        dates = _collect_dates(division)
        assert dates == ["2025-03-08", "2025-03-09"]

    def test_empty_pools(self) -> None:
        """Test with empty pools."""
        division = Division(id=1, name="Test")
        dates = _collect_dates(division)
        assert dates == []

    def test_matches_without_dates(self) -> None:
        """Test with matches that have no dates."""
        division = Division(id=1, name="Test")
        pool = Pool(play_id=1, name="Pool A")
        pool.matches = [Match(id=1, date="")]
        division.pools = [pool]

        dates = _collect_dates(division)
        assert dates == []

    def test_sorted_dates(self) -> None:
        """Test that dates are returned in sorted order."""
        division = Division(id=1, name="Test")
        pool = Pool(play_id=1, name="Pool A")
        pool.matches = [
            Match(id=1, date="2025-03-09"),
            Match(id=2, date="2025-03-08"),
            Match(id=3, date="2025-03-10"),
        ]
        division.pools = [pool]

        dates = _collect_dates(division)
        assert dates == ["2025-03-08", "2025-03-09", "2025-03-10"]


class TestWriteOutput:
    """Tests for _write_output."""

    def test_writes_json_file(self, tmp_path: Path) -> None:
        """Test writing tournament JSON to file."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            data = {"division": "14s", "teams": {}}
            _write_output("14s-power-league", data)

            file_path = tmp_path / "14s-power-league" / "tournament.json"
            assert file_path.exists()
            content = json.loads(file_path.read_text())
            assert content == data

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test that nested directories are created."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            data = {"division": "18s"}
            _write_output("deep/nested/slug", data)

            file_path = tmp_path / "deep" / "nested" / "slug" / "tournament.json"
            assert file_path.exists()

    def test_indented_json(self, tmp_path: Path) -> None:
        """Test that output JSON is properly indented."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            data = {"division": "14s", "teams": {"1": {"name": "Team A"}}}
            _write_output("14s", data)

            file_path = tmp_path / "14s" / "tournament.json"
            content = file_path.read_text()
            # Check that indentation is present (2-space indent)
            assert "  " in content


class TestUpdateIndex:
    """Tests for _update_index."""

    def test_creates_new_index(self, tmp_path: Path) -> None:
        """Test creating a new index.json."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            _update_index("14s-power-league", "14s Power League", "Spring Nationals")

            index_file = tmp_path / "index.json"
            assert index_file.exists()
            index = json.loads(index_file.read_text())
            assert index["event"] == "Spring Nationals"
            assert len(index["divisions"]) == 1
            assert index["divisions"][0]["slug"] == "14s-power-league"
            assert index["divisions"][0]["name"] == "14s Power League"

    def test_updates_existing_index(self, tmp_path: Path) -> None:
        """Test updating existing index with new division."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            # Create initial index
            tmp_path.mkdir(parents=True, exist_ok=True)
            index_file = tmp_path / "index.json"
            initial = {
                "event": "Spring Nationals",
                "divisions": [{"slug": "18s-gold", "name": "18s Gold"}],
            }
            index_file.write_text(json.dumps(initial))

            # Update with new division
            _update_index("14s-power-league", "14s Power League", "Spring Nationals")

            # Verify both divisions exist
            updated = json.loads(index_file.read_text())
            assert len(updated["divisions"]) == 2
            slugs = {div["slug"] for div in updated["divisions"]}
            assert slugs == {"18s-gold", "14s-power-league"}

    def test_updates_existing_division_name(self, tmp_path: Path) -> None:
        """Test updating existing division entry."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            # Create initial index
            tmp_path.mkdir(parents=True, exist_ok=True)
            index_file = tmp_path / "index.json"
            initial = {
                "event": "Spring Nationals",
                "divisions": [{"slug": "14s", "name": "14s Old Name"}],
            }
            index_file.write_text(json.dumps(initial))

            # Update with same slug
            _update_index("14s", "14s New Name", "Spring Nationals")

            # Verify division was updated, not duplicated
            updated = json.loads(index_file.read_text())
            assert len(updated["divisions"]) == 1
            assert updated["divisions"][0]["name"] == "14s New Name"

    def test_preserves_event_name(self, tmp_path: Path) -> None:
        """Test that event name is preserved/updated in index."""
        with patch("scraper.cli.WEB_DATA_DIR", tmp_path):
            tmp_path.mkdir(parents=True, exist_ok=True)
            index_file = tmp_path / "index.json"
            initial = {
                "event": "Old Event",
                "divisions": [{"slug": "14s", "name": "14s"}],
            }
            index_file.write_text(json.dumps(initial))

            _update_index("14s", "14s", "New Event")

            updated = json.loads(index_file.read_text())
            assert updated["event"] == "New Event"


class TestScrapeCommand:
    """Tests for the scrape CLI command."""

    def test_command_structure(self) -> None:
        """Test that scrape command is properly defined."""
        assert scrape.name == "scrape"
        assert scrape.help is not None

    def test_full_pipeline(self, tmp_path: Path) -> None:
        """End-to-end test with mocked HTTP and graph modules."""
        runner = click.testing.CliRunner()

        # Mock all the dependencies
        with patch("scraper.cli.parse_aes_url") as mock_parse_url, \
             patch("scraper.cli.AESClient") as MockClient, \
             patch("scraper.cli.parse_division_plays") as mock_parse_plays, \
             patch("scraper.cli.parse_pool_sheet") as mock_parse_pool, \
             patch("scraper.cli.parse_brackets") as mock_parse_brackets, \
             patch("scraper.cli.GraphBuilder") as MockGraphBuilder, \
             patch("scraper.cli.TeamScheduleExporter") as MockExporter, \
             patch("scraper.cli.WEB_DATA_DIR", tmp_path):

            # Setup mocks
            mock_parse_url.return_value = ("TEST_KEY", 123)

            # Mock client
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            MockClient.return_value = mock_client_instance

            mock_client_instance.get_event.return_value = {
                "Name": "Test Tournament",
                "Divisions": [
                    {
                        "DivisionId": 123,
                        "Name": "14s",
                        "ColorHex": "#FF0000",
                        "CodeAlias": "14s",
                    }
                ],
            }

            # Mock parsers
            mock_round = Round(id=-100, name="Pool Play", type="pool")
            mock_parse_plays.return_value = [mock_round]

            mock_pool = Pool(play_id=-100, name="Pool A")
            mock_pool.teams = [Team(id=1, name="Team A", club="Club A")]
            mock_parse_pool.return_value = mock_pool

            mock_parse_brackets.return_value = []

            # Mock graph builder and exporter
            mock_builder = MagicMock()
            MockGraphBuilder.return_value = mock_builder

            mock_exporter = MagicMock()
            MockExporter.return_value = mock_exporter
            mock_exporter.export.return_value = {
                "division": "14s",
                "dates": ["2025-03-08"],
                "teams": {},
            }

            # Run command
            result = runner.invoke(scrape, ["https://example.com/event/TEST_KEY/division/123"])

            # Verify success
            assert result.exit_code == 0
            assert "Done: web/data/14s/tournament.json" in result.output

            # Verify files were created
            tournament_file = tmp_path / "14s" / "tournament.json"
            assert tournament_file.exists()

            index_file = tmp_path / "index.json"
            assert index_file.exists()
            index = json.loads(index_file.read_text())
            assert index["event"] == "Test Tournament"

    def test_invalid_url(self) -> None:
        """Test command with invalid URL."""
        runner = click.testing.CliRunner()

        with patch("scraper.cli.parse_aes_url") as mock_parse_url:
            mock_parse_url.side_effect = ValueError("Cannot parse AES URL")

            result = runner.invoke(scrape, ["https://invalid.com"])

            assert result.exit_code != 0

    def test_url_argument_required(self) -> None:
        """Test that URL argument is required."""
        runner = click.testing.CliRunner()
        result = runner.invoke(scrape, [])

        assert result.exit_code != 0
        assert "Error" in result.output or "missing" in result.output.lower()

    def test_help_message(self) -> None:
        """Test that help message is available."""
        runner = click.testing.CliRunner()
        result = runner.invoke(scrape, ["--help"])

        assert result.exit_code == 0
        assert "AES tournament division" in result.output
        assert "URL" in result.output
