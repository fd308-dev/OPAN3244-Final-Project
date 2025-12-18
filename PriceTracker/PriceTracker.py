import os
import re
from datetime import datetime, timezone

import requests
import plotly.graph_objects as go
from dotenv import load_dotenv


# Load env vars from a .env file.
# If your .env is NOT in the same folder you run the script from,
# either move it there or change this to an explicit path like:
# load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
if not KEEPA_API_KEY:
    raise RuntimeError(
        "Missing KEEPA_API_KEY. Put it in a .env file (KEEPA_API_KEY=...) and run from the folder that contains it."
    )

KEEPA_ENDPOINT = "https://api.keepa.com/product"
DOMAIN_ID = 2  # UK for amazon.co.uk links

# Keepa API CSV indices
IDX_AMAZON = 0
IDX_NEW = 1
IDX_BUYBOX = 18
IDX_RATING = 16
IDX_REVIEWS = 17


# Helpers
def extract_asin(text: str) -> str:
    text = text.strip()
    if re.fullmatch(r"[A-Z0-9]{10}", text, flags=re.IGNORECASE):
        return text.upper()

    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()

    raise ValueError("Could not extract ASIN from input.")


def keepa_minutes_to_dt_utc(keepa_minutes: int) -> datetime:
    # Keepa minutes -> unix seconds: (m + 21564000) * 60
    unix_seconds = (int(keepa_minutes) + 21564000) * 60
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def parse_series(arr, min_time=None, price_series=False):
    """
    Keepa arrays are ALWAYS: [time, value, time, value, ...]
    Returns x (datetimes) and y (ints).
    min_time: if set, ignore points before this Keepa-minute timestamp (use trackingSince).
    price_series: if True, drop 0 and negative values.
    """
    if not arr or not isinstance(arr, list):
        return [], []

    xs, ys = [], []
    n = len(arr) - (len(arr) % 2)

    for i in range(0, n, 2):
        t = arr[i]
        v = arr[i + 1]
        if t is None or v is None:
            continue

        t = int(t)
        v = int(v)

        # Drop no-data markers
        if v in (-1, -2):
            continue

        # Drop anything before Keepa started tracking this ASIN
        if min_time is not None and t < int(min_time):
            continue

        # For price series, also drop zeros or nonsense
        if price_series and v <= 0:
            continue

        xs.append(keepa_minutes_to_dt_utc(t))
        ys.append(v)

    return xs, ys


def last_valid_value(arr, min_time=None, price_series=False):
    if not arr or not isinstance(arr, list):
        return None

    n = len(arr) - (len(arr) % 2)
    for i in range(n - 2, -1, -2):
        t = arr[i]
        v = arr[i + 1]
        if t is None or v is None:
            continue

        t = int(t)
        v = int(v)

        if v in (-1, -2):
            continue
        if min_time is not None and t < int(min_time):
            continue
        if price_series and v <= 0:
            continue
        return v

    return None


def price_to_float(v: int) -> float:
    return float(v) / 100.0  # pence -> GBP


def fetch_keepa_product(asin: str) -> dict:
    params = {
        "key": KEEPA_API_KEY,
        "domain": DOMAIN_ID,
        "asin": asin,
        "stats": 1,     # include summary stats (safe)
        "history": 1,   # include csv history arrays
    }

    r = requests.get(KEEPA_ENDPOINT, params=params, timeout=30)

    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise RuntimeError(f"Keepa error {r.status_code}: {err}")

    data = r.json()

    products = data.get("products", [])
    if not products:
        raise RuntimeError(f"No product returned. Response: {data}")
    return products[0]


# Main
def main():
    asin = extract_asin(input("Paste Amazon URL or ASIN: "))
    p = fetch_keepa_product(asin)

    title = p.get("title", asin)
    csv_data = p.get("csv", [])
    tracking_since = p.get("trackingSince")  # Keepa minutes when tracking began

    def get_arr(idx):
        return csv_data[idx] if isinstance(csv_data, list) and len(csv_data) > idx else None

    buybox_arr = get_arr(IDX_BUYBOX)
    new_arr = get_arr(IDX_NEW)
    amazon_arr = get_arr(IDX_AMAZON)
    rating_arr = get_arr(IDX_RATING)
    reviews_arr = get_arr(IDX_REVIEWS)

    # current price: Buy Box -> New -> Amazon (ignore pre-tracking + zero)
    current_int = (
        last_valid_value(buybox_arr, tracking_since, price_series=True)
        or last_valid_value(new_arr, tracking_since, price_series=True)
        or last_valid_value(amazon_arr, tracking_since, price_series=True)
    )
    if current_int is None:
        raise RuntimeError("No valid current price found in Keepa series.")
    current_price = price_to_float(current_int)

    # rating is typically 0..50 (divide by 10), reviews is count
    rating_int = last_valid_value(rating_arr, tracking_since, price_series=False)
    rating = (rating_int / 10.0) if rating_int is not None and rating_int >= 0 else None

    reviews_int = last_valid_value(reviews_arr, tracking_since, price_series=False)
    reviews = int(reviews_int) if reviews_int is not None and reviews_int >= 0 else None

    print("\n=== PRODUCT ===")
    print(f"Title:  {title}")
    print(f"ASIN:   {asin}")
    print(f"Price:  £{current_price:.2f}")
    if rating is not None:
        print(f"Rating: {rating:.1f} ⭐")
    if reviews is not None:
        print(f"Reviews:{reviews}")

    # plot: Buy Box preferred else New else Amazon
    x, y = parse_series(buybox_arr, tracking_since, price_series=True)
    series_name = "Buy Box"

    if not x:
        x, y = parse_series(new_arr, tracking_since, price_series=True)
        series_name = "New"
    if not x:
        x, y = parse_series(amazon_arr, tracking_since, price_series=True)
        series_name = "Amazon"

    if not x:
        print("\nNo valid history series available to plot.")
        return

    y_prices = [price_to_float(v) for v in y]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y_prices, mode="lines", name=series_name))
    fig.update_layout(
        title=f"{title} Price History ({series_name})",
        xaxis_title="Date (UTC)",
        yaxis_title="Price (GBP)",
        hovermode="x unified",
    )
    fig.show()


if __name__ == "__main__":
    main()
