from news_collector.normalizer import Deduper


def test_deduper_marks_first_seen_new():
    d = Deduper()
    item = {"source": "x", "url": "https://e.com/1", "title": "t"}
    assert d.is_new(item) is True
    assert d.is_new(item) is False


def test_deduper_distinguishes_items():
    d = Deduper()
    a = {"source": "x", "url": "https://e.com/1", "title": "t1"}
    b = {"source": "x", "url": "https://e.com/2", "title": "t2"}
    assert d.is_new(a) is True
    assert d.is_new(b) is True
    assert d.is_new(a) is False
