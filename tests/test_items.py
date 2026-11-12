import pytest

from shelf.models import validate_new


def test_a_valid_item_is_trimmed():
    clean, error = validate_new("  A book  ", " https://example.com ")
    assert error is None
    assert clean == {"title": "A book", "url": "https://example.com"}


def _add(client, title="A book", url="https://example.com"):
    client.post("/items", {"title": title, "url": url})
    return 1


def test_edit_page_shows_the_form_with_current_values(client):
    item_id = _add(client, 'Tom & "Jerry"', "https://example.com/?a=1&b=2")
    page = client.get(f"/items/{item_id}/edit")
    assert page.status == 200
    assert f'<form method="post" action="/items/{item_id}/edit">' in page.text
    assert 'name="title"' in page.text and 'name="url"' in page.text
    assert "Tom &amp; &quot;Jerry&quot;" in page.text
    assert "https://example.com/?a=1&amp;b=2" in page.text


def test_edit_of_an_unknown_item_is_404(client):
    assert client.get("/items/99/edit").status == 404
    assert client.post("/items/99/edit", {"title": "x", "url": ""}).status == 404


def test_edit_saves_trimmed_values_and_keeps_status_and_date(client):
    from shelf import store

    item_id = _add(client)
    client.post(f"/items/{item_id}/status", {"status": "done"})
    before = store.get(item_id)
    response = client.post(f"/items/{item_id}/edit", {"title": "  New  ", "url": " https://new.example "})
    assert response.status == 303
    assert response.headers["location"] == f"/items/{item_id}"
    after = store.get(item_id)
    assert after["title"] == "New" and after["url"] == "https://new.example"
    assert after["status"] == "done" and after["added"] == before["added"]


def test_edit_can_clear_the_link(client):
    from shelf import store

    item_id = _add(client)
    assert client.post(f"/items/{item_id}/edit", {"title": "A book", "url": ""}).status == 303
    assert store.get(item_id)["url"] == ""


@pytest.mark.parametrize(
    "title, url, message",
    [("   ", "", "required"), ("x" * 201, "", "200"), ("A", "ftp://example.com", "http")],
)
def test_invalid_edit_is_400_and_saves_nothing(client, title, url, message):
    from shelf import store

    item_id = _add(client)
    before = store.get(item_id)
    response = client.post(f"/items/{item_id}/edit", {"title": title, "url": url})
    assert response.status == 400
    assert message in response.text
    assert f'action="/items/{item_id}/edit"' in response.text
    assert store.get(item_id) == before


def test_invalid_edit_shows_the_values_entered_escaped(client):
    item_id = _add(client)
    response = client.post(f"/items/{item_id}/edit", {"title": "<b>x</b>", "url": "nope"})
    assert response.status == 400
    assert 'value="&lt;b&gt;x&lt;/b&gt;"' in response.text
    assert 'value="nope"' in response.text


def test_item_page_links_to_edit(client):
    item_id = _add(client)
    assert f'<a href="/items/{item_id}/edit">Edit</a>' in client.get(f"/items/{item_id}").text


def test_edit_route_with_wrong_method_is_405(client):
    item_id = _add(client)
    for method in ("PUT", "DELETE"):
        assert client._call(method, f"/items/{item_id}/edit").status == 405


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


def test_the_item_page_has_a_delete_form(client):
    client.post("/items", {"title": "Book"})
    page = client.get("/items/1").text
    assert '<form method="post" action="/items/1/delete">' in page
    assert ">Delete</button>" in page


def test_delete_redirects_and_removes_only_that_item(client):
    client.post("/items", {"title": "Gone"})
    client.post("/items", {"title": "Kept"})
    response = client.post("/items/1/delete", {})
    assert response.status == 303
    assert response.headers["location"] == "/"
    assert "Gone" not in client.get("/").text
    assert "Kept" in client.get("/").text
    assert client.get("/items/1").status == 404
    assert client.get("/items/2").status == 200


def test_delete_of_an_unknown_item_is_the_404_page(client):
    response = client.post("/items/99/delete", {})
    assert response.status == 404
    assert "404" in response.text


def test_get_on_the_delete_path_is_405(client):
    client.post("/items", {"title": "Book"})
    response = client.get("/items/1/delete")
    assert response.status == 405
    assert response.headers["allow"] == "POST"
    assert client.get("/items/1").status == 200


def test_an_id_is_never_given_twice_even_after_deleting_the_highest(client):
    client.post("/items", {"title": "One"})
    client.post("/items", {"title": "Two"})
    client.post("/items/2/delete", {})
    client.post("/items", {"title": "Three"})
    assert client.get("/items/2").status == 404
    assert client.get("/items/3").status == 200
