import json
import re

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


def _shelf(client):
    for title in ("Dune", "Emma", "Ulysses"):
        client.post("/items", {"title": title})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})


def test_filtering_by_status_keeps_only_matching_items(client):
    _shelf(client)
    for status, kept, dropped in (("to-read", "Dune", "Emma"), ("reading", "Emma", "Dune"), ("done", "Ulysses", "Emma")):
        page = client.get(f"/?status={status}").text
        assert kept in page and dropped not in page


def test_no_or_empty_status_lists_everything(client):
    _shelf(client)
    for path in ("/", "/?status="):
        page = client.get(path).text
        assert "Dune" in page and "Emma" in page and "Ulysses" in page


def test_an_unknown_status_gets_400_with_the_escaped_value(client):
    response = client.get("/?status=lost")
    assert response.status == 400
    assert "Unknown status: lost" in response.text
    page = client.get("/?status=%3Cscript%3E").text
    assert "<script>" not in page and "Unknown status: &lt;script&gt;" in page


def test_the_filter_nav_links_and_marks_the_current_one(client):
    expected = [("All", "/"), ("To read", "/?status=to-read"), ("Reading", "/?status=reading"), ("Done", "/?status=done")]
    for current, path in [(None, "/")] + [(label, href) for label, href in expected[1:]]:
        page = client.get(path).text
        nav = page[page.index('<nav class="filters">'):page.index("</nav>")]
        links = re.findall(r'<a href="([^"]*)"([^>]*)>([^<]*)</a>', nav)
        assert [(h, t) for h, _, t in links] == [(h, t) for t, h in expected]
        marked = [t for _, attrs, t in links if 'aria-current="page"' in attrs]
        assert marked == [current or "All"]


def test_a_filter_with_no_match_says_so(client):
    client.post("/items", {"title": "Dune"})
    assert "No items with this status." in client.get("/?status=done").text
    assert "No items with this status." not in client.get("/").text


def test_the_filtered_index_still_only_accepts_get(client):
    assert client.post("/?status=done", {}).status == 405


def test_the_stats_page_shows_zeros_on_an_empty_shelf(client):
    response = client.get("/stats")
    assert response.status == 200
    assert "<h1>Statistics</h1>" in response.text
    assert '<table class="stats">' in response.text
    rows = re.findall(r"<tr><th>(.*?)</th><td>(.*?)</td></tr>", response.text)
    assert rows == [("To read", "0"), ("Reading", "0"), ("Done", "0"), ("Total", "0")]


def test_the_stats_page_counts_items_by_status(client):
    for title in ("A", "B", "C"):
        client.post("/items", {"title": title, "url": ""})
    client.post("/items/2/status", {"status": "reading"})
    client.post("/items/3/status", {"status": "done"})
    rows = re.findall(r"<tr><th>(.*?)</th><td>(.*?)</td></tr>", client.get("/stats").text)
    assert rows == [("To read", "1"), ("Reading", "1"), ("Done", "1"), ("Total", "3")]


def test_every_page_links_to_the_stats_page(client):
    assert '<a href="/stats">Statistics</a>' in client.get("/").text
    assert '<a href="/stats">Statistics</a>' in client.get("/stats").text


def test_the_stats_page_shows_the_version_in_the_footer(client):
    assert f"<footer>shelf {__version__}</footer>" in client.get("/stats").text


def test_posting_to_the_stats_page_gets_405(client):
    response = client.post("/stats", {})
    assert (response.status, response.headers["allow"]) == (405, "GET")
