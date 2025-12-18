import pytest

# Adjust import depending on your structure:
# If PriceTracker.py is in PriceTracker/PriceTracker.py:
from PriceTracker.PriceTracker import extract_asin, keepa_minutes_to_dt_utc, parse_series, last_valid_value


def test_extract_asin_direct():
    assert extract_asin("B08N5WRWNW") == "B08N5WRWNW"


def test_extract_asin_from_url_dp():
    url = "https://www.amazon.co.uk/dp/B08N5WRWNW/ref=something"
    assert extract_asin(url) == "B08N5WRWNW"


def test_extract_asin_from_url_gp():
    url = "https://www.amazon.co.uk/gp/product/B08N5WRWNW"
    assert extract_asin(url) == "B08N5WRWNW"


def test_extract_asin_invalid():
    with pytest.raises(ValueError):
        extract_asin("not-an-asin")


def test_keepa_minutes_to_dt_utc_type():
    dt = keepa_minutes_to_dt_utc(0)
    assert dt.tzinfo is not None


def test_parse_series_basic():
    # [time, value, time, value]
    arr = [100, 12345, 101, 12400]
    x, y = parse_series(arr, min_time=None, price_series=True)
    assert len(x) == 2
    assert y == [12345, 12400]


def test_parse_series_filters_by_min_time():
    arr = [100, 12345, 101, 12400]
    x, y = parse_series(arr, min_time=101, price_series=True)
    assert len(x) == 1
    assert y == [12400]


def test_last_valid_value_price_series_ignores_zero():
    arr = [100, 0, 101, 12000]
    assert last_valid_value(arr, min_time=None, price_series=True) == 12000