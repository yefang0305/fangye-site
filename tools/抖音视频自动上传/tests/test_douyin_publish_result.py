from publisher import douyin


class _MissingLocator:
    @property
    def first(self):
        return self

    def wait_for(self, *args, **kwargs):
        raise TimeoutError("not visible")


class _FakeContentManagePage:
    url = douyin.URL_CONTENT_MANAGE
    frames = []

    def __init__(self, clock):
        self._clock = clock
        self.wait_calls = 0

    def locator(self, selector):
        return _MissingLocator()

    def wait_for_timeout(self, timeout_ms):
        self.wait_calls += 1
        self._clock["now"] += timeout_ms / 1000


def test_wait_for_submit_result_accepts_stable_content_manage_page(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(douyin.time, "time", lambda: clock["now"])
    monkeypatch.setattr(douyin, "SUCCESS_TIMEOUT_MS", 20_000)
    page = _FakeContentManagePage(clock)

    ok, reason = douyin._wait_for_submit_result(page)

    assert ok is True
    assert reason == ""
    assert page.wait_calls <= 6
