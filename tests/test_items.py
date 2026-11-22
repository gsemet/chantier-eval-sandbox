import pytest

from shelf import store
from shelf.models import validate_item


def test_a_valid_item_is_trimmed():
    clean, error = validate_item("  A book  ", " https://example.com ")
    assert error is None
    assert clean == {"title": "A book", "url": "https://example.com"}


def test_the_link_is_optional():
    assert validate_item("A book", "")[1] is None


@pytest.mark.parametrize("title", ["", "   "])
def test_the_title_is_required(title):
    assert "required" in validate_item(title, "")[1]


def test_the_title_has_at_most_200_characters():
    assert validate_item("x" * 200, "")[1] is None
    assert "200" in validate_item("x" * 201, "")[1]


@pytest.mark.parametrize("url", ["example.com", "ftp://example.com", "javascript:alert(1)"])
def test_the_link_starts_with_http_or_https(url):
    assert "http" in validate_item("A book", url)[1]


def _add(client, title="A book", url="https://example.com"):
    client.post("/items", {"title": title, "url": url})
    return 1


def test_edit_page_has_a_form_with_current_values(client):
    _add(client, 'A "quoted" <b>book</b>', "https://example.com/?a=1&b=2")
    page = client.get("/items/1/edit")
    assert page.status == 200
    assert '<form method="post" action="/items/1/edit">' in page.text
    assert 'name="title" value="A &quot;quoted&quot; &lt;b&gt;book&lt;/b&gt;"' in page.text
    assert 'name="url" value="https://example.com/?a=1&amp;b=2"' in page.text
    assert "<b>book</b>" not in page.text


def test_edit_page_of_an_unknown_item_is_404(client):
    assert client.get("/items/9/edit").status == 404
    assert client.post("/items/9/edit", {"title": "x", "url": ""}).status == 404


def test_a_valid_edit_is_saved_trimmed_and_redirects(client):
    _add(client)
    client.post("/items/1/status", {"status": "reading"})
    before = store.get(1)
    response = client.post("/items/1/edit", {"title": "  New  ", "url": " https://new.example "})
    assert response.status == 303
    assert response.headers["location"] == "/items/1"
    after = store.get(1)
    assert after["title"] == "New"
    assert after["url"] == "https://new.example"
    assert after["status"] == "reading"
    assert after["added"] == before["added"]


def test_an_edit_can_clear_the_link(client):
    _add(client)
    assert client.post("/items/1/edit", {"title": "A book", "url": ""}).status == 303
    assert store.get(1)["url"] == ""


@pytest.mark.parametrize(
    "title, url, message",
    [("  ", "", "required"), ("x" * 201, "", "200"), ("A book", "ftp://x", "http")],
)
def test_an_invalid_edit_is_400_and_saves_nothing(client, title, url, message):
    _add(client)
    response = client.post("/items/1/edit", {"title": title, "url": url})
    assert response.status == 400
    assert message in response.text
    assert 'action="/items/1/edit"' in response.text
    assert f'name="url" value="{url}"' in response.text
    assert store.get(1)["title"] == "A book"
    assert store.get(1)["url"] == "https://example.com"


def test_an_invalid_edit_escapes_the_values_entered(client):
    _add(client)
    response = client.post("/items/1/edit", {"title": "", "url": '"><script>'})
    assert response.status == 400
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_edit_route_rejects_other_methods(client):
    _add(client)
    for method in ("PUT", "DELETE"):
        response = client._call(method, "/items/1/edit")
        assert response.status == 405
        assert response.headers["allow"] == "GET, POST"


def test_the_item_page_links_to_the_edit_page(client):
    _add(client)
    assert '<a href="/items/1/edit">Edit</a>' in client.get("/items/1").text
