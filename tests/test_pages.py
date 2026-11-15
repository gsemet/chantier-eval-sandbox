import json

from shelf import __version__, store


def test_the_index_shows_an_empty_shelf_and_the_form(client):
    response = client.get("/")
    assert response.status == 200
    assert "Nothing on the shelf yet." in response.text
    assert '<form method="post" action="/items">' in response.text
    assert __version__ in response.text  # the footer


def test_adding_an_item_redirects_and_the_list_shows_it(client):
    response = client.post("/items", {"title": "Dune", "url": "https://example.com/dune"})
    assert (response.status, response.headers["location"]) == (303, "/")
    page = client.get("/").text
    assert 'href="/items/1"' in page and "Dune" in page and "to-read" in page


def test_an_invalid_item_gets_400_with_the_message_and_the_values(client):
    response = client.post("/items", {"title": "", "url": "https://kept.example"})
    assert response.status == 400
    assert "The title is required." in response.text
    assert 'value="https://kept.example"' in response.text
    assert store.load() == []


def test_a_bad_link_gets_400(client):
    assert client.post("/items", {"title": "Dune", "url": "nope"}).status == 400


def test_the_item_page(client):
    client.post("/items", {"title": "Dune", "url": "https://example.com/dune"})
    response = client.get("/items/1")
    assert response.status == 200
    assert "Dune" in response.text and 'href="https://example.com/dune"' in response.text


def test_an_unknown_item_gets_the_404_page(client):
    response = client.get("/items/99")
    assert response.status == 404
    assert "Not Found" in response.text


def test_setting_the_status(client):
    client.post("/items", {"title": "Dune"})
    response = client.post("/items/1/status", {"status": "reading"})
    assert (response.status, response.headers["location"]) == (303, "/items/1")
    assert store.get(1)["status"] == "reading"


def test_a_status_must_be_known_and_the_item_must_exist(client):
    client.post("/items", {"title": "Dune"})
    assert client.post("/items/1/status", {"status": "lost"}).status == 400
    assert client.post("/items/9/status", {"status": "done"}).status == 404
    assert store.get(1)["status"] == "to-read"


def test_user_text_is_escaped(client):
    client.post("/items", {"title": "<script>alert(1)</script>", "url": 'https://x.example/"><b>'})
    for page in (client.get("/").text, client.get("/items/1").text):
        assert "<script>" not in page and "<b>" not in page
        assert "&lt;script&gt;" in page


def test_the_error_message_and_values_are_escaped(client):
    page = client.post("/items", {"title": "", "url": '"><i>'}).text
    assert "<i>" not in page


def test_unknown_paths_get_404_and_wrong_methods_get_405(client):
    assert client.get("/nope").status == 404
    assert client.get("/items").status == 405
    assert client.post("/", {}).status == 405
    assert client.get("/items/1/status").status == 405
    assert client.post("/healthz", {}).status == 405


def test_a_query_string_is_not_part_of_the_path(client):
    assert client.get("/?status=done").status == 200


def test_the_stylesheet(client):
    response = client.get("/static/style.css")
    assert response.status == 200
    assert response.headers["content-type"].startswith("text/css")


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status == 200
    assert json.loads(response.text) == {"status": "ok", "version": __version__}


def _three(client):
    for title in ("Dune", "Emma", "Ubik"):
        client.post("/items", {"title": title})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})


def test_filtering_the_list_by_status(client):
    _three(client)
    page = client.get("/?status=reading").text
    assert "Emma" in page and "Dune" not in page and "Ubik" not in page
    assert "Dune" in client.get("/?status=to-read").text
    assert "Ubik" in client.get("/?status=done").text


def test_no_or_empty_status_shows_all(client):
    _three(client)
    for path in ("/", "/?status="):
        page = client.get(path).text
        assert all(t in page for t in ("Dune", "Emma", "Ubik"))


def test_an_unknown_status_gets_400_with_the_escaped_value(client):
    response = client.get("/?status=<b>x</b>")
    assert response.status == 400
    assert "Unknown status: &lt;b&gt;x&lt;/b&gt;" in response.text
    assert "<b>x" not in response.text


def test_the_filter_nav_marks_the_current_link(client):
    import re

    expected = [("All", "/"), ("To read", "/?status=to-read"), ("Reading", "/?status=reading"), ("Done", "/?status=done")]
    for path, current in [("/", "All"), ("/?status=", "All"), ("/?status=to-read", "To read"),
                          ("/?status=reading", "Reading"), ("/?status=done", "Done")]:
        text = client.get(path).text
        nav = re.search(r'<nav class="filters">(.*?)</nav>', text, re.S).group(1)
        links = re.findall(r'<a href="([^"]*)"([^>]*)>([^<]*)</a>', nav)
        assert [(label, href) for href, _, label in links] == expected
        assert [label for _, attrs, label in links if 'aria-current="page"' in attrs] == [current]


def test_a_filter_matching_nothing_says_so(client):
    client.post("/items", {"title": "Dune"})
    assert "No items with this status." in client.get("/?status=done").text
    assert "No items with this status." not in client.get("/").text


def test_the_index_with_a_filter_rejects_other_methods(client):
    assert client.post("/?status=done", {}).status == 405


def test_the_stats_page_shows_four_zeros_on_an_empty_shelf(client):
    response = client.get("/stats")
    assert response.status == 200
    assert "<h1>Statistics</h1>" in response.text and '<table class="stats">' in response.text
    assert response.text.count("<td>0</td>") == 4
    assert __version__ in response.text


def test_the_stats_page_counts_by_status_in_order(client):
    client.post("/items", {"title": "A", "url": ""})
    client.post("/items", {"title": "B", "url": ""})
    client.post("/items", {"title": "C", "url": ""})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})
    client.post("/items/1/status", {"status": "done"})
    text = client.get("/stats").text
    rows = [
        "<tr><th>To read</th><td>0</td></tr>",
        "<tr><th>Reading</th><td>1</td></tr>",
        "<tr><th>Done</th><td>2</td></tr>",
        "<tr><th>Total</th><td>3</td></tr>",
    ]
    positions = [text.index(r) for r in rows]
    assert positions == sorted(positions)


def test_every_page_links_to_the_stats_page(client):
    client.post("/items", {"title": "A", "url": ""})
    for path in ("/", "/items/1", "/stats", "/missing"):
        assert '<a href="/stats">Statistics</a>' in client.get(path).text


def test_posting_to_stats_gets_405(client):
    response = client.post("/stats", {})
    assert response.status == 405
    assert response.headers["allow"] == "GET"
