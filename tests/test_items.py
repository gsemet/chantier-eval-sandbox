import pytest

from shelf.models import validate_new


def test_a_valid_item_is_trimmed():
    clean, error = validate_new("  A book  ", " https://example.com ")
    assert error is None
    assert clean == {"title": "A book", "url": "https://example.com"}


def test_the_link_is_optional():
    assert validate_new("A book", "")[1] is None


@pytest.mark.parametrize("title", ["", "   "])
def test_the_title_is_required(title):
    assert "required" in validate_new(title, "")[1]


def test_the_title_has_at_most_200_characters():
    assert validate_new("x" * 200, "")[1] is None
    assert "200" in validate_new("x" * 201, "")[1]


@pytest.mark.parametrize("url", ["example.com", "ftp://example.com", "javascript:alert(1)"])
def test_the_link_starts_with_http_or_https(url):
    assert "http" in validate_new("A book", url)[1]


def _add(client, title):
    client.post("/items", {"title": title})


def test_the_item_page_has_a_delete_form(client):
    _add(client, "A book")
    page = client.get("/items/1").text
    assert '<form method="post" action="/items/1/delete">' in page
    assert "Delete</button>" in page


def test_deleting_an_item_redirects_and_removes_it(client):
    _add(client, "First")
    _add(client, "Second")
    response = client.post("/items/1/delete", {})
    assert response.status == 303
    assert response.headers["location"] == "/"
    assert client.get("/items/1").status == 404
    index = client.get("/").text
    assert "First" not in index
    assert "Second" in index
    assert client.get("/items/2").status == 200


def test_deleting_an_unknown_item_is_404(client):
    assert client.post("/items/99/delete", {}).status == 404


def test_get_on_the_delete_path_is_405(client):
    _add(client, "A book")
    response = client.get("/items/1/delete")
    assert response.status == 405
    assert response.headers["allow"] == "POST"
    assert client.get("/items/1").status == 200


def test_an_id_is_never_given_twice(client):
    _add(client, "First")
    _add(client, "Second")
    client.post("/items/2/delete", {})
    _add(client, "Third")
    assert client.get("/items/2").status == 404
    assert client.get("/items/3").status == 200
    client.post("/items/3/delete", {})
    client.post("/items/1/delete", {})
    _add(client, "Fourth")
    assert client.get("/items/4").status == 200
