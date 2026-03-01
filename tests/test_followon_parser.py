from scraper.parsers.followon import FollowOnParser

# Real AES FutureRoundMatches shape (from live API fixture)
FUTURE_MATCHES = [
    {
        "RankText": "1 - Arbuckle 14 KJ (NC) (1)",
        "Match": {"MatchId": -55312, "Court": {"CourtId": -52787, "Name": "OMNI Ct.9"}, "ScheduledStartDateTime": "2026-02-01T07:30:00"},
        "WorkMatch": None,
        "Play": {"PlayId": -55121, "CompleteShortName": "LgQFeb1BAll 1s-2sGold A"},
        "WorkTeamAssignmentDecided": True,
        "NextPendingReseed": False,
    },
    {
        "RankText": "2 - EVC 14-Black (NC) (17)",
        "Match": {"MatchId": -55324, "Court": {"CourtId": -52785, "Name": "OMNI Ct.7"}, "ScheduledStartDateTime": "2026-02-01T07:30:00"},
        "WorkMatch": None,
        "Play": {"PlayId": -55304, "CompleteShortName": "LgQFeb1BAll 1s-2sGold D"},
        "WorkTeamAssignmentDecided": True,
        "NextPendingReseed": False,
    },
    {
        "RankText": "3 - FPVC 14 Derek (NC) (32)",
        "Match": {"MatchId": -55339, "Court": {"CourtId": -52786, "Name": "OMNI Ct.8"}, "ScheduledStartDateTime": "2026-02-01T07:30:00"},
        "WorkMatch": None,
        "Play": {"PlayId": -55331, "CompleteShortName": "LgQFeb1BAll 3s-4sSilver A"},
        "WorkTeamAssignmentDecided": True,
        "NextPendingReseed": False,
    },
    # Null Match entry — future bracket not yet scheduled
    {
        "RankText": "4 - ACVC 13 (NC) (16)",
        "Match": None,
        "WorkMatch": None,
        "Play": None,
        "WorkTeamAssignmentDecided": True,
        "NextPendingReseed": False,
    },
]


class TestFollowOnParser:
    def _parser(self, future_matches=None, source_play_id=-54281):
        return FollowOnParser(
            FUTURE_MATCHES if future_matches is None else future_matches,
            source_play_id,
            "KEY",
            193839,
        )

    def test_basic_followon(self):
        edges = self._parser([FUTURE_MATCHES[0]]).parse()
        assert len(edges) == 1
        e = edges[0]
        assert e.source_rank == 1
        assert e.source_play_id == -54281
        assert e.target_match_id == -55312
        assert e.source_text == "1 - Arbuckle 14 KJ (NC) (1)"

    def test_second_place(self):
        edges = self._parser([FUTURE_MATCHES[1]]).parse()
        assert len(edges) == 1
        assert edges[0].source_rank == 2
        assert edges[0].target_match_id == -55324

    def test_third_place(self):
        edges = self._parser([FUTURE_MATCHES[2]]).parse()
        assert len(edges) == 1
        assert edges[0].source_rank == 3

    def test_null_match_skipped(self):
        """Entries with Match=None are skipped (bracket not yet scheduled)."""
        edges = self._parser([FUTURE_MATCHES[3]]).parse()
        assert edges == []

    def test_multiple_entries(self):
        """Three valid entries + one null → 3 edges."""
        edges = self._parser(FUTURE_MATCHES).parse()
        assert len(edges) == 3

    def test_empty_future_matches(self):
        edges = self._parser([]).parse()
        assert edges == []

    def test_source_text_preserved(self):
        edges = self._parser([FUTURE_MATCHES[0]]).parse()
        assert edges[0].source_text == "1 - Arbuckle 14 KJ (NC) (1)"

    def test_source_play_id_set_from_constructor(self):
        """source_play_id comes from the pool's play_id, not the Play object."""
        edges = self._parser([FUTURE_MATCHES[0]], source_play_id=-99999).parse()
        assert edges[0].source_play_id == -99999

    def test_ranks_are_correct(self):
        edges = self._parser(FUTURE_MATCHES).parse()
        ranks = sorted(e.source_rank for e in edges)
        assert ranks == [1, 2, 3]

    def test_match_ids_are_correct(self):
        edges = self._parser(FUTURE_MATCHES).parse()
        match_ids = {e.target_match_id for e in edges}
        assert match_ids == {-55312, -55324, -55339}

    def test_unparseable_rank_text_skipped(self):
        bad = [{
            "RankText": "Winner of Gold A",  # No leading integer
            "Match": {"MatchId": -99001},
            "WorkMatch": None,
            "Play": {"PlayId": -99002},
        }]
        edges = self._parser(bad).parse()
        assert edges == []

    def test_match_missing_match_id_skipped(self):
        bad = [{
            "RankText": "1 - Some Team",
            "Match": {},  # No MatchId key
            "WorkMatch": None,
            "Play": {"PlayId": -99002},
        }]
        edges = self._parser(bad).parse()
        assert edges == []
