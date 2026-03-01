"""
Integration tests: end-to-end pipeline using fixture JSON files.

These tests require fixture files captured via:
    pixi run capture-fixtures <URL>

Fixtures live in per-division subdirectories under tests/fixtures/:
    tests/fixtures/{slug}/event.json
    tests/fixtures/{slug}/plays.json
    ...

Tests are skipped automatically if no fixture directories are present.
"""
import json
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


def _fixture_dirs() -> list[Path]:
    """Return all subdirectories of fixtures/ that contain plays.json."""
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(d for d in FIXTURES_ROOT.iterdir() if d.is_dir() and (d / "plays.json").exists())


def _load(fixture_dir: Path, name: str) -> dict | list:
    with open(fixture_dir / name) as f:
        return json.load(f)


# Collect fixture dirs once at module load for parameterization
_ALL_FIXTURE_DIRS = _fixture_dirs()
_FIXTURE_IDS = [d.name for d in _ALL_FIXTURE_DIRS]

skip_no_fixtures = pytest.mark.skipif(
    len(_ALL_FIXTURE_DIRS) == 0,
    reason="No fixture directories found. Run: pixi run capture-fixtures <URL>",
)


@skip_no_fixtures
@pytest.mark.parametrize("fixture_dir", _ALL_FIXTURE_DIRS, ids=_FIXTURE_IDS)
class TestDivisionParserWithFixtures:
    def test_plays_produces_rounds(self, fixture_dir):
        from scraper.parsers.division import DivisionParser

        plays = _load(fixture_dir, "plays.json")
        rounds = DivisionParser(plays, "KEY", 0).parse()
        assert len(rounds) > 0

    def test_plays_has_pools_or_brackets(self, fixture_dir):
        from scraper.parsers.division import DivisionParser

        plays = _load(fixture_dir, "plays.json")
        rounds = DivisionParser(plays, "KEY", 0).parse()
        has_pools = any(len(r.pools) > 0 for r in rounds)
        has_brackets = any(len(r.brackets) > 0 for r in rounds)
        assert has_pools or has_brackets


@skip_no_fixtures
@pytest.mark.parametrize(
    "fixture_dir",
    [d for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
    ids=[d.name for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
)
class TestPoolParserWithFixtures:
    def test_poolsheet_produces_pool(self, fixture_dir):
        from scraper.parsers.pool import PoolParser

        poolsheet_files = list(fixture_dir.glob("poolsheet_*.json"))
        data = _load(fixture_dir, poolsheet_files[0].name)
        pool = PoolParser(data, "KEY", 0).parse()
        assert pool.play_id != 0
        assert pool.full_name != ""

    def test_poolsheet_has_teams(self, fixture_dir):
        from scraper.parsers.pool import PoolParser

        poolsheet_files = list(fixture_dir.glob("poolsheet_*.json"))
        data = _load(fixture_dir, poolsheet_files[0].name)
        pool = PoolParser(data, "KEY", 0).parse()
        assert len(pool.teams) > 0

    def test_poolsheet_has_matches(self, fixture_dir):
        from scraper.parsers.pool import PoolParser

        poolsheet_files = list(fixture_dir.glob("poolsheet_*.json"))
        data = _load(fixture_dir, poolsheet_files[0].name)
        pool = PoolParser(data, "KEY", 0).parse()
        assert len(pool.matches) > 0


@skip_no_fixtures
@pytest.mark.parametrize(
    "fixture_dir",
    [d for d in _ALL_FIXTURE_DIRS if any(d.glob("brackets_*.json"))],
    ids=[d.name for d in _ALL_FIXTURE_DIRS if any(d.glob("brackets_*.json"))],
)
class TestBracketParserWithFixtures:
    def test_bracket_produces_matches(self, fixture_dir):
        from scraper.parsers.bracket import BracketParser

        bracket_files = list(fixture_dir.glob("brackets_*.json"))
        data = _load(fixture_dir, bracket_files[0].name)
        bm_list = BracketParser(data, "KEY", 0).parse()
        assert isinstance(bm_list, list)


@skip_no_fixtures
@pytest.mark.parametrize(
    "fixture_dir",
    [d for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
    ids=[d.name for d in _ALL_FIXTURE_DIRS if any(d.glob("poolsheet_*.json"))],
)
class TestEndToEndWithFixtures:
    def test_full_pipeline_produces_valid_json(self, fixture_dir, tmp_path):
        """End-to-end: fixtures → parsers → DAG → valid Cytoscape JSON."""
        from datetime import datetime

        from scraper.graph.builder import GraphBuilder
        from scraper.graph.exporter import CytoscapeExporter
        from scraper.graph.pruner import PathPruner
        from scraper.models import Division
        from scraper.parsers.division import DivisionParser
        from scraper.parsers.followon import FollowOnParser
        from scraper.parsers.pool import PoolParser

        plays = _load(fixture_dir, "plays.json")
        rounds = DivisionParser(plays, "TESTKEY", 999999).parse()

        all_teams = {}
        all_edges = []

        for rnd in rounds:
            for pool in rnd.pools:
                fixture_path = fixture_dir / f"poolsheet_{pool.play_id}.json"
                if not fixture_path.exists():
                    continue
                data = _load(fixture_dir, fixture_path.name)
                parsed = PoolParser(data, "TESTKEY", 999999).parse()
                pool.teams = parsed.teams
                pool.matches = parsed.matches
                pool.match_description = parsed.match_description
                for s in pool.teams:
                    all_teams[s.team.team_id] = s.team
                future = data.get("FutureRoundMatches", [])
                if future:
                    edges = FollowOnParser(future, pool.play_id, "TESTKEY", 999999).parse()
                    all_edges.extend(edges)

        division = Division(
            division_id=999999,
            name="Test Division",
            event_key="TESTKEY",
            event_name="Test Event",
            rounds=rounds,
            follow_on_edges=all_edges,
            all_teams=list(all_teams.values()),
            scraped_at=datetime.now(),
        )

        nodes, edges = GraphBuilder(division).build()
        edges = PathPruner(nodes, edges).prune()

        output = CytoscapeExporter(nodes, edges, division).export()

        assert "metadata" in output
        assert "elements" in output
        assert len(output["elements"]["nodes"]) > 0
        assert len(output["elements"]["edges"]) > 0

        for node in output["elements"]["nodes"]:
            d = node["data"]
            assert "id" in d
            assert "type" in d
            assert "status" in d

        out_path = tmp_path / "tournament.json"
        CytoscapeExporter(nodes, edges, division).export_to_file(str(out_path))
        assert out_path.exists()
        with open(out_path) as f:
            reloaded = json.load(f)
        assert len(reloaded["elements"]["nodes"]) == len(output["elements"]["nodes"])
