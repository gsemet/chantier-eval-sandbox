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


def _add(client, title="A book", url="https://example.com"):
    client.post("/items", {"title": title, "url": url})


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


def test_the_edit_page_holds_the_current_values_escaped(client):
    _add(client, 'A "quoted" <b>', "https://example.com/?a=1&b=2")
    page = client.get("/items/1/edit")
    assert page.status == 200
    assert '<form method="post" action="/items/1/edit">' in page.text
    assert 'name="title" value="A &quot;quoted&quot; &lt;b&gt;"' in page.text
    assert 'name="url" value="https://example.com/?a=1&amp;b=2"' in page.text


def test_the_edit_page_of_an_unknown_item_is_404(client):
    assert client.get("/items/9/edit").status == 404
    assert client.post("/items/9/edit", {"title": "x", "url": ""}).status == 404


def test_a_valid_edit_saves_trimmed_values_and_keeps_status_and_date(client):
    _add(client)
    client.post("/items/1/status", {"status": "reading"})
    before = client.get("/items/1").text
    response = client.post("/items/1/edit", {"title": "  New  ", "url": " http://x.org "})
    assert response.status == 303
    assert response.headers["location"] == "/items/1"
    after = client.get("/items/1").text
    assert "<h1>New</h1>" in after
    assert 'href="http://x.org"' in after
    assert 'class="status">reading<' in after
    added = before.split("Added ")[1].split(".")[0]
    assert f"Added {added}." in after


def test_a_valid_edit_may_clear_the_link(client):
    _add(client)
    assert client.post("/items/1/edit", {"title": "A book", "url": ""}).status == 303
    assert "example.com" not in client.get("/items/1").text


@pytest.mark.parametrize(
    "title, url, message",
    [("   ", "", "required"), ("x" * 201, "", "200"), ("Ok", "ftp://x", "http")],
)
def test_an_invalid_edit_is_400_and_saves_nothing(client, title, url, message):
    _add(client)
    response = client.post("/items/1/edit", {"title": title, "url": url})
    assert response.status == 400
    assert message in response.text
    assert f'name="title" value="{title.strip()}"' in response.text
    assert f'name="url" value="{url}"' in response.text
    assert "<h1>A book</h1>" in client.get("/items/1").text
    assert "https://example.com" in client.get("/items/1").text


def test_the_item_page_links_to_the_edit_page(client):
    _add(client)
    assert '<a href="/items/1/edit">Edit</a>' in client.get("/items/1").text


def test_the_edit_route_refuses_other_methods(client):
    _add(client)
    for method in ("PUT", "DELETE"):
        assert client._call(method, "/items/1/edit").status == 405
