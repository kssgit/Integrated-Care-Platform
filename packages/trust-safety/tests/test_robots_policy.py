from trust_safety.robots_policy import is_path_allowed_by_robots

ROBOTS_TEXT = """
User-agent: *
Disallow: /private
Allow: /private/public
"""


def test_robots_disallow_private() -> None:
    assert not is_path_allowed_by_robots(ROBOTS_TEXT, "/private/data", user_agent="test-bot")


def test_robots_allow_nested_path() -> None:
    assert is_path_allowed_by_robots(ROBOTS_TEXT, "/private/public/page", user_agent="test-bot")


def test_robots_allow_other_path() -> None:
    assert is_path_allowed_by_robots(ROBOTS_TEXT, "/open", user_agent="test-bot")

