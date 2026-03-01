from scraper.models import MatchStatus
from scraper.parsers.bracket import BracketParser


def make_match(match_id, first_team=None, second_team=None, has_scores=False,
               first_won=None, sets=None):
    m = {
        "MatchId": match_id,
        "MatchFullName": f"Match {abs(match_id)}",
        "MatchShortName": f"M{abs(match_id)}",
        "HasScores": has_scores,
        "FirstTeamWon": first_won,
        "Sets": sets or [],
        "Court": None,
        "ScheduledStartDateTime": None,
        "PlayId": None,
    }
    if first_team:
        m["FirstTeam"] = first_team
        m["FirstTeamText"] = first_team.get("Name", "")
    else:
        m["FirstTeam"] = None
        m["FirstTeamText"] = "1st R1P1"
    if second_team:
        m["SecondTeam"] = second_team
        m["SecondTeamText"] = second_team.get("Name", "")
    else:
        m["SecondTeam"] = None
        m["SecondTeamText"] = "2nd R1P2"
    return m


def make_node(key, match_id, x=0.0, y=0.0, reversed_=False, double_capped=False,
              children=None, first_team=None, second_team=None, has_scores=False,
              first_won=None, sets=None):
    return {
        "Key": key,
        "X": x,
        "Y": y,
        "Reversed": reversed_,
        "DoubleCapped": double_capped,
        "Match": make_match(match_id, first_team, second_team, has_scores, first_won, sets),
        "Children": children or [],
    }


TEAM_A = {"TeamId": 1, "Name": "Team A", "TeamCode": "ta", "Club": None}
TEAM_B = {"TeamId": 2, "Name": "Team B", "TeamCode": "tb", "Club": None}
TEAM_C = {"TeamId": 3, "Name": "Team C", "TeamCode": "tc", "Club": None}
TEAM_D = {"TeamId": 4, "Name": "Team D", "TeamCode": "td", "Club": None}


class TestBracketParser:
    def _parser(self, data):
        return BracketParser(data, "KEY", 193839)

    def test_single_root(self):
        data = [{"Roots": [make_node(0, -100, x=1.0, y=1.0)]}]
        result = self._parser(data).parse()
        assert len(result) == 1
        assert result[0].key == 0
        assert result[0].x == 1.0
        assert result[0].y == 1.0

    def test_recursive_children(self):
        # Tree: root with 2 children, each with 1 child = 5 nodes total... but
        # let's do root + 2 children + 2 grandchildren = 5
        child1 = make_node(1, -101, children=[make_node(3, -103)])
        child2 = make_node(2, -102, children=[make_node(4, -104)])
        root = make_node(0, -100, children=[child1, child2])
        data = [{"Roots": [root]}]
        result = self._parser(data).parse()
        assert len(result) == 5

    def test_placeholder_teams(self):
        node = make_node(0, -100)  # No teams, just placeholders
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert len(result) == 1
        bm = result[0]
        assert bm.match.home_team is None
        assert bm.match.away_team is None
        assert bm.match.home_placeholder == "1st R1P1"
        assert bm.match.away_placeholder == "2nd R1P2"

    def test_populated_teams(self):
        node = make_node(0, -100, first_team=TEAM_A, second_team=TEAM_B)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        bm = result[0]
        assert bm.match.home_team is not None
        assert bm.match.home_team.team_id == 1
        assert bm.match.home_team.name == "Team A"
        assert bm.match.away_team is not None
        assert bm.match.away_team.team_id == 2

    def test_xy_coordinates(self):
        node = make_node(0, -100, x=3.5, y=9.0)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result[0].x == 3.5
        assert result[0].y == 9.0

    def test_reversed_flag(self):
        node = make_node(0, -100, reversed_=True)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result[0].reversed is True

    def test_double_capped_flag(self):
        node = make_node(0, -100, double_capped=True)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result[0].double_capped is True

    def test_scores_on_bracket_match(self):
        sets = [
            {"FirstTeamScore": 25, "SecondTeamScore": 20, "ScoreText": "25-20", "IsDecidingSet": False},
            {"FirstTeamScore": 25, "SecondTeamScore": 15, "ScoreText": "25-15", "IsDecidingSet": False},
        ]
        node = make_node(0, -100, has_scores=True, first_won=True,
                         first_team=TEAM_A, second_team=TEAM_B, sets=sets)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        bm = result[0]
        assert bm.match.status == MatchStatus.FINISHED
        assert bm.match.home_won is True
        assert len(bm.match.set_scores) == 2
        assert bm.match.set_scores[0].score_text == "25-20"

    def test_in_progress_match(self):
        node = make_node(0, -100, has_scores=True, first_won=None,
                         first_team=TEAM_A, second_team=TEAM_B)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result[0].match.status == MatchStatus.IN_PROGRESS

    def test_scheduled_match(self):
        node = make_node(0, -100, has_scores=False)
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result[0].match.status == MatchStatus.SCHEDULED

    def test_empty_brackets(self):
        data = [{"Roots": []}]
        result = self._parser(data).parse()
        assert result == []

    def test_multiple_brackets(self):
        b1 = {"Roots": [make_node(0, -100)]}
        b2 = {"Roots": [make_node(1, -200)]}
        result = self._parser([b1, b2]).parse()
        assert len(result) == 2

    def test_node_without_match_skipped(self):
        node = {"Key": 0, "X": 0.0, "Y": 0.0, "Match": None, "Children": []}
        data = [{"Roots": [node]}]
        result = self._parser(data).parse()
        assert result == []
