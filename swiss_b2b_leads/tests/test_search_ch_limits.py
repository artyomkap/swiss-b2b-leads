from sources import search_ch


class FakeResponse:
    status_code = 200
    url = "https://tel.search.ch/?q=test"

    def __init__(self, html: str):
        self.text = html


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        html = "".join(
            f"""
            <article class="tel-resultentry">
              <h2><a>Company {params['where']} {params['pos']} {i}</a></h2>
              <a href="tel:+41123456{i}">Call</a>
              <span class="locality">{params['where']}</span>
            </article>
            """
            for i in range(10)
        )
        return FakeResponse(html)


def test_search_ch_max_results_is_global_not_per_location(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(search_ch.requests, "Session", lambda: fake_session)

    leads = search_ch.collect(
        ["Lugano", "Bellinzona", "Locarno"],
        ["shopping center"],
        max_results=15,
    )

    assert len(leads) == 15
    assert len(fake_session.calls) == 2
    assert fake_session.calls[0][1]["where"] == "Lugano"
    assert fake_session.calls[1][1]["where"] == "Bellinzona"
