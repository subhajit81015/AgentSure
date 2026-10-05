from agentsure.authentication import authenticate_actor


def test_authenticate_valid_actor():
    result = authenticate_actor("human-reviewer-001")

    assert result.authenticated is True
    assert result.actor == "human-reviewer-001"
    assert result.reason == "Actor authenticated."


def test_authenticate_missing_actor():
    result = authenticate_actor(None)

    assert result.authenticated is False
    assert result.actor is None
    assert result.reason == "Actor authentication is required."


def test_authenticate_blank_actor():
    result = authenticate_actor("   ")

    assert result.authenticated is False
    assert result.actor is None
    assert result.reason == "Actor authentication is required."