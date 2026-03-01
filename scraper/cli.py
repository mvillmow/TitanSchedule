import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from scraper.client import AESClient
from scraper.url import parse_aes_url


def _slugify(name: str) -> str:
    """Convert division name to URL-safe slug: '18s - 15s Power League' -> '18s-15s-power-league'"""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s or 'unknown'


def _update_index(division) -> None:
    """Upsert this division's entry into web/data/index.json."""
    index_path = Path("web/data/index.json")
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {"divisions": []}

    slug = _slugify(division.name)
    entry = {
        "slug": slug,
        "event_name": division.event_name,
        "division_name": division.name,
        "division_id": division.division_id,
        "event_key": division.event_key,
        "aes_url": division.aes_url,
        "scraped_at": division.scraped_at.isoformat() if division.scraped_at else None,
    }

    # Upsert by slug
    index["divisions"] = [d for d in index["divisions"] if d["slug"] != slug]
    index["divisions"].append(entry)
    index["divisions"].sort(key=lambda d: d["division_name"])

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Updated index: {index_path}")


async def capture_fixtures(url: str, output_dir: Path):
    """
    Fetch all API responses for a division and save as JSON fixtures.
    Saves to output_dir/{slug}/ where slug is derived from the division name.
    Used for TDD: all parser tests run against these saved responses.
    """
    parts = parse_aes_url(url)

    async with AESClient() as client:
        # Resolve division name first so we can name the subdirectory
        event = await client.get_event(parts.event_key)
        division_name = next(
            (
                d["Name"]
                for d in event.get("Divisions", [])
                if d["DivisionId"] == parts.division_id
            ),
            "unknown",
        )
        slug = _slugify(division_name)
        output_dir = output_dir / slug
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Capturing fixtures for '{division_name}' → {output_dir}/")

        # 2. Division plays structure
        plays = await client.get_division_plays(parts.event_key, parts.division_id)
        _save(output_dir / "plays.json", plays)

        # 3. Playdays
        playdays = await client.get_division_playdays(parts.event_key, parts.division_id)
        _save(output_dir / "playdays.json", playdays)

        # 4. Poolsheets for each pool play
        pool_plays = [p for p in plays.get("Plays", []) if p.get("Type") == 0]
        for play in pool_plays:
            play_id = play["PlayId"]
            sheet = await client.get_poolsheet(parts.event_key, play_id)
            _save(output_dir / f"poolsheet_{play_id}.json", sheet)

        # 5. Brackets for each date with HasBrackets
        for day in playdays:
            if day.get("HasBrackets"):
                date_str = day["DateTime"][:10]
                brackets = await client.get_division_brackets(
                    parts.event_key, parts.division_id, date_str
                )
                _save(output_dir / f"brackets_{date_str}.json", brackets)

        # 6. Pools standings for each date with HasPools
        for day in playdays:
            if day.get("HasPools"):
                date_str = day["DateTime"][:10]
                pools = await client.get_division_pools(
                    parts.event_key, parts.division_id, date_str
                )
                _save(output_dir / f"pools_{date_str}.json", pools)


async def scrape(url: str, output: str | None):
    """Full scrape: API → parse → DAG → JSON."""
    # Import here to avoid circular imports at module load
    from scraper.graph.builder import GraphBuilder
    from scraper.graph.exporter import CytoscapeExporter
    from scraper.graph.pruner import PathPruner
    from scraper.models import Division
    from scraper.parsers.bracket import BracketParser
    from scraper.parsers.division import DivisionParser
    from scraper.parsers.followon import FollowOnParser
    from scraper.parsers.pool import PoolParser

    parts = parse_aes_url(url)

    async with AESClient() as client:
        # 1. Event metadata
        event_data = await client.get_event(parts.event_key)
        event_name = event_data.get("Name", "Unknown Event")
        division_name = next(
            (
                d["Name"]
                for d in event_data.get("Divisions", [])
                if d["DivisionId"] == parts.division_id
            ),
            "Unknown Division",
        )

        # Auto-compute output path from division name if not explicitly set
        if output is None:
            slug = _slugify(division_name)
            output_dir = Path("web/data") / slug
            output_dir.mkdir(parents=True, exist_ok=True)
            output = str(output_dir / "tournament.json")
        else:
            Path(output).parent.mkdir(parents=True, exist_ok=True)

        # 2. Division structure (rounds, pools, brackets)
        plays_data = await client.get_division_plays(parts.event_key, parts.division_id)
        rounds = DivisionParser(plays_data, parts.event_key, parts.division_id).parse()

        # 3. Fetch and parse poolsheets for each pool
        all_teams: dict[int, object] = {}
        all_follow_on_edges = []

        for rnd in rounds:
            for pool in rnd.pools:
                sheet = await client.get_poolsheet(parts.event_key, pool.play_id)
                parsed_pool = PoolParser(sheet, parts.event_key, parts.division_id).parse()

                # Merge parsed data into the round's pool skeleton
                pool.teams = parsed_pool.teams
                pool.matches = parsed_pool.matches
                pool.match_description = parsed_pool.match_description

                # Collect all teams (skip placeholder slots with no team_id)
                for standing in pool.teams:
                    if standing.team.team_id is not None:
                        all_teams[standing.team.team_id] = standing.team

                # Parse follow-on edges from FutureRoundMatches
                future_matches = sheet.get("FutureRoundMatches", [])
                if future_matches:
                    followon_parser = FollowOnParser(
                        future_matches,
                        pool.play_id,
                        parts.event_key,
                        parts.division_id,
                    )
                    all_follow_on_edges.extend(followon_parser.parse())

        # 4. Fetch and parse brackets — accumulate across all dates
        playdays = await client.get_division_playdays(parts.event_key, parts.division_id)
        all_bracket_matches_by_play_id: dict[int, list] = {}
        for day in playdays:
            if day.get("HasBrackets"):
                date_str = day["DateTime"][:10]
                brackets_data = await client.get_division_brackets(
                    parts.event_key, parts.division_id, date_str
                )
                for bm in BracketParser(brackets_data, parts.event_key, parts.division_id).parse():
                    pid = bm.match.play_id
                    all_bracket_matches_by_play_id.setdefault(pid, []).append(bm)

        # Assign accumulated bracket matches to their Bracket objects
        for rnd in rounds:
            for bracket in rnd.brackets:
                bracket.bracket_matches = all_bracket_matches_by_play_id.get(bracket.play_id, [])

        # 5. Assemble Division
        division = Division(
            division_id=parts.division_id,
            name=division_name,
            event_key=parts.event_key,
            event_name=event_name,
            rounds=rounds,
            follow_on_edges=all_follow_on_edges,
            all_teams=list(all_teams.values()),
            aes_url=url,
            scraped_at=datetime.now(),
        )

        # 6. Build DAG
        builder = GraphBuilder(division)
        nodes, edges = builder.build()

        # 7. Prune paths
        pruner = PathPruner(nodes, edges)
        edges = pruner.prune()

        # 8. Export
        exporter = CytoscapeExporter(nodes, edges, division)
        exporter.export_to_file(output)
        print(f"Exported {len(nodes)} nodes, {len(edges)} edges to {output}")

        # 9. Update index
        _update_index(division)


def _save(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="TitanSchedule AES Scraper")
    parser.add_argument("urls", nargs="+", help="One or more AES division URLs")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output JSON path (only valid when scraping a single URL)",
    )
    parser.add_argument(
        "--capture-fixtures",
        action="store_true",
        help="Save raw API JSON to tests/fixtures/ for TDD",
    )
    args = parser.parse_args()

    if args.output and len(args.urls) > 1:
        parser.error("--output can only be used with a single URL")

    async def _run():
        if args.capture_fixtures:
            await asyncio.gather(
                *(capture_fixtures(url, Path("tests/fixtures")) for url in args.urls)
            )
        else:
            await asyncio.gather(
                *(scrape(url, args.output if len(args.urls) == 1 else None) for url in args.urls)
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
