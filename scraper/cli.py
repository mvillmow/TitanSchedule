"""CLI entry point for TitanSchedule scraper."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import click

from scraper.client import AESClient
from scraper.graph.builder import GraphBuilder
from scraper.graph.team_exporter import ExportDict, TeamScheduleExporter
from scraper.models import Division
from scraper.parsers import parse_brackets, parse_division_plays, parse_pool_sheet
from scraper.url import parse_aes_url

WEB_DATA_DIR = Path("web/data")


async def _scrape(url: str) -> None:
    """Main scrape pipeline."""
    event_key, division_id = parse_aes_url(url)

    async with AESClient() as client:
        # 1. Fetch event metadata
        event_data = await client.get_event(event_key)
        event_name = event_data.get("Name", "Unknown Tournament")

        # 2. Find division info from event data
        division_name, division_color, division_code = _find_division_info(
            event_data, division_id
        )

        # 3. Fetch division plays (rounds)
        plays_data = await client.get_division_plays(event_key, division_id)
        rounds = parse_division_plays(plays_data)

        # 4. Create division and fetch pools and brackets based on round types
        division = Division(
            id=division_id,
            name=division_name,
            rounds=rounds,
            color_hex=division_color,
            code_alias=division_code,
        )

        # Fetch pool data for pool rounds — each round entry has a unique play_id
        for round_ in rounds:
            if round_.type == "pool" and round_.play_id is not None:
                pool_data = await client.get_pool_sheet(event_key, round_.play_id)
                pool = parse_pool_sheet(pool_data)
                division.pools.append(pool)
                # Collect teams from pools
                for team in pool.teams:
                    division.teams[team.id] = team

        # Fetch bracket data - collect unique dates from pool matches
        dates = _collect_dates(division)
        for date in dates:
            bracket_data = await client.get_brackets(event_key, division_id, date)
            if bracket_data:
                bracket_matches = parse_brackets(bracket_data)
                division.bracket_matches.extend(bracket_matches)

        # 5. Build graph
        builder = GraphBuilder()
        builder.build(division)

        # 6. Export team-centric JSON
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        # 7. Write output
        slug = _make_slug(division_name)
        _write_output(slug, result)
        _update_index(slug, division_name, event_name)

    click.echo(f"Done: web/data/{slug}/tournament.json")


def _find_division_info(
    event_data: dict[str, Any], division_id: int
) -> tuple[str, str, str]:
    """Extract division name, color, and code from event data."""
    divisions = event_data.get("Divisions") or []
    for div in divisions:
        if div.get("DivisionId") == division_id:
            return (
                str(div.get("Name", f"Division {division_id}")),
                str(div.get("ColorHex", "")),
                str(div.get("CodeAlias", "")),
            )
    return f"Division {division_id}", "", ""


def _collect_dates(division: Division) -> list[str]:
    """Collect unique dates from pool matches."""
    dates: set[str] = set()
    for pool in division.pools:
        for match in pool.matches:
            if match.date:
                dates.add(match.date)
    return sorted(dates)


def _make_slug(name: str) -> str:
    """Convert division name to URL-safe slug."""
    return name.lower().replace(" ", "-").replace("/", "-")


def _write_output(slug: str, data: ExportDict) -> None:
    """Write tournament JSON to web/data/{slug}/tournament.json."""
    out_dir = WEB_DATA_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "tournament.json"
    out_file.write_text(json.dumps(data, indent=2))


def _update_index(slug: str, division_name: str, event_name: str) -> None:
    """Update web/data/index.json with this division."""
    index_file = WEB_DATA_DIR / "index.json"
    index: dict[str, Any] = {"event": event_name, "divisions": []}
    if index_file.exists():
        raw = json.loads(index_file.read_text())
        if isinstance(raw, dict):
            index = raw
    else:
        WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Update or add division entry
    divisions = index.get("divisions", [])
    for div in divisions:
        if div.get("slug") == slug:
            div["name"] = division_name
            break
    else:
        divisions.append({"slug": slug, "name": division_name})

    index["divisions"] = divisions
    index["event"] = event_name
    index_file.write_text(json.dumps(index, indent=2))


@click.command()
@click.argument("url")
def scrape(url: str) -> None:
    """Scrape an AES tournament division and export team schedules."""
    asyncio.run(_scrape(url))


if __name__ == "__main__":
    scrape()
