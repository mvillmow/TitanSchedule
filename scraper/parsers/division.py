from scraper.models import Bracket, Court, PlayType, Pool, Round
from scraper.parsers.base import BaseParser


class DivisionParser(BaseParser):
    """
    Parses the division plays structure: rounds, pools, brackets, courts.

    Input JSON shape:
    {
        "Division": {"DivisionId": 193839, "Name": "12 Girls", ...},
        "Plays": [
            {"RoundId": -50094, "RoundName": "Round 1", "GroupId": -50095,
             "GroupName": "", "Type": 0, "PlayId": -51151,
             "FullName": "Pool 1", "ShortName": "P1",
             "CompleteShortName": "R1P1", "CompleteFullName": "Round 1 Pool 1",
             "Order": 0, "Courts": [...]}
        ]
    }

    Output: list[Round] with Pool/Bracket skeletons.
    """

    def parse(self) -> list[Round]:
        rounds_by_id: dict[int, Round] = {}

        for play in self._data.get("Plays", []):
            round_id = play.get("RoundId")
            if round_id is None:
                continue
            round_name = play.get("RoundName", "")
            play_id = play.get("PlayId")
            if play_id is None:
                continue
            raw_type = play.get("Type")
            if raw_type is None:
                continue
            try:
                play_type = PlayType(raw_type)
            except ValueError:
                continue

            if round_id not in rounds_by_id:
                rounds_by_id[round_id] = Round(
                    round_id=round_id,
                    round_name=round_name,
                )

            rnd = rounds_by_id[round_id]
            courts = [
                Court(c["CourtId"], c["Name"], c.get("VideoLink"))
                for c in play.get("Courts", [])
                if c.get("CourtId") is not None and c.get("Name") is not None
            ]
            full_name = play.get("FullName", "")
            short_name = play.get("ShortName", "")

            if play_type == PlayType.POOL:
                rnd.pools.append(
                    Pool(
                        play_id=play_id,
                        full_name=full_name,
                        short_name=short_name,
                        complete_name=play.get("CompleteFullName", full_name),
                        complete_short_name=play.get("CompleteShortName", short_name),
                        round_id=round_id,
                        round_name=round_name,
                        match_description="",
                        courts=courts,
                        order=play.get("Order", 0),
                    )
                )
            elif play_type == PlayType.BRACKET:
                rnd.brackets.append(
                    Bracket(
                        play_id=play_id,
                        full_name=full_name,
                        short_name=short_name,
                        complete_name=play.get("CompleteFullName", full_name),
                        complete_short_name=play.get("CompleteShortName", short_name),
                        round_id=round_id,
                        round_name=round_name,
                        group_name=play.get("GroupName", ""),
                        courts=courts,
                        order=play.get("Order", 0),
                    )
                )

        # AES round IDs are negative integers; higher values (less negative) = earlier rounds
        return sorted(rounds_by_id.values(), key=lambda r: r.round_id, reverse=True)
