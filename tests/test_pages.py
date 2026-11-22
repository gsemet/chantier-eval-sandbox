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
        client.post("/items", {"title": title, "url": ""})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})


def test_the_filter_keeps_only_the_items_with_that_status(client):
    _three(client)
    page = client.get("/?status=reading").text
    assert "Emma" in page and "Dune" not in page and "Ubik" not in page


def test_no_or_empty_status_shows_all_items(client):
    _three(client)
    for path in ("/", "/?status="):
        page = client.get(path).text
        assert all(t in page for t in ("Dune", "Emma", "Ubik"))


def test_an_unknown_status_gets_400_with_the_escaped_value(client):
    response = client.get("/?status=<b>x")
    assert response.status == 400
    assert "Unknown status: &lt;b&gt;x" in response.text and "<b>x" not in response.text


def test_the_filters_nav_links_in_order(client):
    text = client.get("/").text
    nav = text[text.index('<nav class="filters">'):text.index("</nav>")]
    hrefs = ['href="/"', 'href="/?status=to-read"', 'href="/?status=reading"', 'href="/?status=done"']
    positions = [nav.index(h) for h in hrefs]
    assert positions == sorted(positions)
    for label in ("All", "To read", "Reading", "Done"):
        assert f">{label}</a>" in nav


def test_only_the_current_filter_has_aria_current(client):
    for path, href in (("/", 'href="/"'), ("/?status=done", 'href="/?status=done"')):
        text = client.get(path).text
        nav = text[text.index('<nav class="filters">'):text.index("</nav>")]
        assert nav.count("aria-current") == 1
        assert f'<a {href} aria-current="page">' in nav


def test_a_filter_with_no_match_says_so(client):
    client.post("/items", {"title": "Dune", "url": ""})
    assert "No items with this status." in client.get("/?status=done").text


def test_the_index_with_a_filter_rejects_other_methods(client):
    assert client.post("/?status=done", {}).status == 405


def _stats_rows(text):
    import re
    return re.findall(r"<tr><th>(.*?)</th><td>(.*?)</td></tr>", text)


def test_the_stats_page_of_an_empty_shelf_shows_four_zeros(client):
    response = client.get("/stats")
    assert response.status == 200
    assert "<h1>Statistics</h1>" in response.text
    assert '<table class="stats">' in response.text
    assert _stats_rows(response.text) == [("To read", "0"), ("Reading", "0"), ("Done", "0"), ("Total", "0")]


def test_the_stats_page_counts_items_by_status(client):
    for title in ("A", "B", "C", "D"):
        client.post("/items", {"title": title, "url": ""})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})
    client.post("/items/4/status", {"status": "done"})
    rows = _stats_rows(client.get("/stats").text)
    assert rows == [("To read", "1"), ("Reading", "1"), ("Done", "2"), ("Total", "4")]


def test_the_stats_page_shows_the_version(client):
    assert f"shelf {__version__}" in client.get("/stats").text


def test_every_page_links_to_the_stats(client):
    client.post("/items", {"title": "Dune", "url": ""})
    for path in ("/", "/stats", "/items/1", "/nope"):
        assert '<a href="/stats">Statistics</a>' in client.get(path).text


def test_the_stats_page_rejects_other_methods(client):
    response = client.post("/stats", {})
    assert response.status == 405
    assert response.headers["allow"] == "GET"
