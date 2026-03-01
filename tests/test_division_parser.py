from scraper.parsers.division import DivisionParser

PLAYS_DATA = {
    "Division": {"DivisionId": 193839, "Name": "12 Girls"},
    "Plays": [
        {
            "RoundId": -50094,
            "RoundName": "Round 1",
            "GroupId": -50095,
            "GroupName": "",
            "Type": 0,
            "PlayId": -51151,
            "FullName": "Pool 1",
            "ShortName": "P1",
            "CompleteShortName": "R1P1",
            "CompleteFullName": "Round 1 Pool 1",
            "Order": 0,
            "Courts": [{"CourtId": -52201, "Name": "Court 3", "VideoLink": "https://example.com"}],
        },
        {
            "RoundId": -50094,
            "RoundName": "Round 1",
            "GroupId": -50095,
            "GroupName": "",
            "Type": 0,
            "PlayId": -51152,
            "FullName": "Pool 2",
            "ShortName": "P2",
            "CompleteShortName": "R1P2",
            "CompleteFullName": "Round 1 Pool 2",
            "Order": 1,
            "Courts": [],
        },
        {
            "RoundId": -50094,
            "RoundName": "Round 1",
            "GroupId": -50095,
            "GroupName": "",
            "Type": 0,
            "PlayId": -51153,
            "FullName": "Pool 3",
            "ShortName": "P3",
            "CompleteShortName": "R1P3",
            "CompleteFullName": "Round 1 Pool 3",
            "Order": 2,
            "Courts": [],
        },
        {
            "RoundId": -50094,
            "RoundName": "Round 1",
            "GroupId": -50095,
            "GroupName": "",
            "Type": 0,
            "PlayId": -51154,
            "FullName": "Pool 4",
            "ShortName": "P4",
            "CompleteShortName": "R1P4",
            "CompleteFullName": "Round 1 Pool 4",
            "Order": 3,
            "Courts": [],
        },
        {
            "RoundId": -52479,
            "RoundName": "Gold Bracket",
            "GroupId": -52480,
            "GroupName": "GoldBracket",
            "Type": 1,
            "PlayId": -52481,
            "FullName": "Gold",
            "ShortName": "G1",
            "CompleteShortName": "GoldG1",
            "CompleteFullName": "Gold Bracket Gold",
            "Order": 0,
            "Courts": [],
        },
        {
            "RoundId": -52479,
            "RoundName": "Gold Bracket",
            "GroupId": -52480,
            "GroupName": "SilverBracket",
            "Type": 1,
            "PlayId": -52482,
            "FullName": "Silver",
            "ShortName": "S1",
            "CompleteShortName": "GoldS1",
            "CompleteFullName": "Gold Bracket Silver",
            "Order": 1,
            "Courts": [],
        },
    ],
}


class TestDivisionParser:
    def _parser(self, data=None):
        return DivisionParser(data or PLAYS_DATA, "KEY", 193839)

    def test_parses_pools_and_brackets(self):
        rounds = self._parser().parse()
        assert len(rounds) == 2
        round1 = rounds[0]
        assert len(round1.pools) == 4
        assert len(round1.brackets) == 0
        round2 = rounds[1]
        assert len(round2.pools) == 0
        assert len(round2.brackets) == 2

    def test_round_grouping(self):
        rounds = self._parser().parse()
        assert rounds[0].round_id == -50094
        assert rounds[0].round_name == "Round 1"
        assert rounds[1].round_id == -52479
        assert rounds[1].round_name == "Gold Bracket"

    def test_pool_type_detection(self):
        rounds = self._parser().parse()
        assert all(hasattr(p, "match_description") for p in rounds[0].pools)

    def test_bracket_type_detection(self):
        rounds = self._parser().parse()
        brackets = rounds[1].brackets
        assert brackets[0].full_name == "Gold"
        assert brackets[1].full_name == "Silver"

    def test_courts_attached(self):
        rounds = self._parser().parse()
        pool1 = rounds[0].pools[0]
        assert len(pool1.courts) == 1
        assert pool1.courts[0].name == "Court 3"
        assert pool1.courts[0].court_id == -52201
        assert pool1.courts[0].video_link == "https://example.com"

    def test_empty_plays(self):
        rounds = self._parser({"Plays": []}).parse()
        assert rounds == []

    def test_ordering_preserved(self):
        rounds = self._parser().parse()
        pools = rounds[0].pools
        assert [p.order for p in pools] == [0, 1, 2, 3]

    def test_pool_fields(self):
        rounds = self._parser().parse()
        pool = rounds[0].pools[0]
        assert pool.play_id == -51151
        assert pool.full_name == "Pool 1"
        assert pool.short_name == "P1"
        assert pool.complete_short_name == "R1P1"
        assert pool.complete_name == "Round 1 Pool 1"

    def test_bracket_fields(self):
        rounds = self._parser().parse()
        bracket = rounds[1].brackets[0]
        assert bracket.play_id == -52481
        assert bracket.full_name == "Gold"
        assert bracket.group_name == "GoldBracket"

    def test_rounds_sorted_by_id(self):
        """Rounds returned in order from least-negative to most-negative RoundId.
        AES uses negative IDs where less negative = earlier round."""
        rounds = self._parser().parse()
        ids = [r.round_id for r in rounds]
        # Less negative = higher value = earlier round, so descending sort
        assert ids == sorted(ids, reverse=True)

    def test_single_round_only_pools(self):
        data = {
            "Plays": [
                {
                    "RoundId": 1,
                    "RoundName": "R1",
                    "Type": 0,
                    "PlayId": 10,
                    "FullName": "Pool 1",
                    "ShortName": "P1",
                    "Order": 0,
                    "Courts": [],
                }
            ]
        }
        rounds = self._parser(data).parse()
        assert len(rounds) == 1
        assert len(rounds[0].pools) == 1
        assert len(rounds[0].brackets) == 0
