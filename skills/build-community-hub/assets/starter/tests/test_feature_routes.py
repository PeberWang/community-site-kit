from app.main import app


def test_disabled_plaza_routes_are_not_registered():
    paths = set(app.openapi()["paths"])
    assert "/plaza" not in paths
    assert "/guides" in paths
    assert "/articles" in paths
    assert "/events" in paths
    assert "/contribute" in paths
