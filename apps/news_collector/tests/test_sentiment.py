from news_collector.sentiment_lexicon import score_text


def test_positive_text():
    s = score_text("Bitcoin surges to ATH amid bullish breakout and ETF approval")
    assert s.label == "positive"
    assert s.score > 0


def test_negative_text():
    s = score_text("Major exchange hacked, lawsuit follows, panic sell-off and crash")
    assert s.label == "negative"
    assert s.score < 0


def test_neutral_text():
    s = score_text("The market opened. Volume was steady. Prices closed flat.")
    assert s.label == "neutral"
    assert s.score == 0.0


def test_empty():
    s = score_text("")
    assert s.label == "neutral"
