#Due to our unfamiliarity with this API, we used ChatGPT for debudding and ideating, particularly in lines 72-162
#To demonstrate our understanding of the debugging, we added comments to show our thought process

import os
import re
from datetime import datetime, timezone

import requests
import plotly.graph_objects as go
from dotenv import load_dotenv


# Load env vars from a .env file.
load_dotenv()

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
KEEPA_ENDPOINT = "https://api.keepa.com/product"

DOMAIN_CHOICES = {
    "US": 1,
    "UK": 2,
    "DE": 3,
    "FR": 4,
    "CA": 6,
    "IT": 8,
    "ES": 9,
}

#Making sure currency labels match the region
DOMAIN_CURRENCY = {
    "US": "$",
    "UK": "£",
    "DE": "€",
    "FR": "€",
    "CA": "CA$",
    "IT": "€",
    "ES": "€",
}


# Keepa API CSV indices
IDX_AMAZON = 0
IDX_NEW = 1
IDX_RATING = 16
IDX_REVIEWS = 17
IDX_BUYBOX = 18


# Helpers
def extract_asin(text: str) -> str:
    #Remove accidental spaces
    text = text.strip()
    #Check if text already is an ASIN
    if re.fullmatch(r"[A-Z0-9]{10}", text, flags=re.IGNORECASE):
        return text.upper()
    #If it isn't already an ASIN, find the ASIN using the three most common Amazon URL formats
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]
    #Loop over each pattern searching for a match
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    #Tell the user via a value error if match could not be found, 
    raise ValueError("Could not extract ASIN from input. Consider pasting in just the ASIN")

#Time conversion from Keepa (minutes to UTC)
def keepa_minutes_to_dt_utc(keepa_minutes: int) -> datetime:
    unix_seconds = (int(keepa_minutes) + 21564000) * 60
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)

#Parse the Keepa time-series array into datetime and value lists
def parse_series(arr, min_time=None, price_series=False):
    #Validate input array
    if not arr or not isinstance(arr, list):
        #Return empty lists if invalid
        return [], []

#Initialize
    xs, ys = [], []
    n = len(arr) - (len(arr) % 2)

#Loop through time value pairs
    for i in range(0, n, 2):
        t = arr[i] #Extract time value
        v = arr[i + 1] #Extract corresponding price
        if t is None or v is None: #Skip over missing entries
            continue

        t = int(t)
        v = int(v)

        #Drop no-data markers
        if v in (-1, -2):
            continue

        #Drop anything before Keepa started tracking this ASIN
        if min_time is not None and t < int(min_time):
            continue

        #For price series, also drop zeros
        if price_series and v <= 0:
            continue

#Convert time to datetime using prviously defined function and store the raw data
        xs.append(keepa_minutes_to_dt_utc(t))
        ys.append(v)

    return xs, ys #Return parsed dates and values

#Define a function to get last value
def last_valid_value(arr, min_time=None, price_series=False):
    if not arr or not isinstance(arr, list): #Validate input
        return None #Return none if invalid

    n = len(arr) - (len(arr) % 2) #Here we ensure the array length is even so time/value pairs are complete
    for i in range(n - 2, -1, -2): #Iterate backwards through the array, stepping by two to read pairs
        t = arr[i] #Extract timestamp
        v = arr[i + 1] # Extract value
        if t is None or v is None: #skip entries where either t or v is missing
            continue

        #Convert t and v to integers
        t = int(t)
        v = int(v)

        #Skip invalid values
        if v in (-1, -2):
            continue
        if min_time is not None and t < int(min_time):
            continue
        if price_series and v <= 0:
            continue
        return v

    return None

#Convert keeps price format (cents) into $
def price_to_float(v: int) -> float:
    return float(v) / 100.0

#Fetch data from keepa 
def fetch_keepa_product(asin: str, domain_id: int) -> dict:
    params = {
        "key": KEEPA_API_KEY,
        "domain": domain_id,
        "asin": asin,
        "stats": 1,
        "history": 1,
    }

    #Send HTTP request
    r = requests.get(KEEPA_ENDPOINT, params=params, timeout=30)

    #Parse JSON
    data = r.json()

    products = data.get("products", [])
    if not products:
        raise RuntimeError(f"No product returned. Response: {data}")
    return products[0]


def main():
    # Marketplace loop
    while True:
        choice = input("Input Marketplace (US, UK, DE, FR, IT, ES, CA): ").strip().upper()
        if choice in DOMAIN_CHOICES:
            break
        print("Invalid marketplace. Please enter either: US, UK, DE, FR, IT, ES, CA.")

    domain_id = DOMAIN_CHOICES[choice]
    currency = DOMAIN_CURRENCY.get(choice, "")
    print(f"Marketplace selected: {choice}")

    asin = extract_asin(input("Paste Amazon URL or ASIN: "))
    p = fetch_keepa_product(asin, domain_id)

    title = p.get("title", asin)
    csv_data = p.get("csv", [])
    tracking_since = p.get("trackingSince")

    def get_arr(idx):
        return csv_data[idx] if isinstance(csv_data, list) and len(csv_data) > idx else None

    buybox_arr = get_arr(IDX_BUYBOX)
    new_arr = get_arr(IDX_NEW)
    amazon_arr = get_arr(IDX_AMAZON)
    rating_arr = get_arr(IDX_RATING)
    reviews_arr = get_arr(IDX_REVIEWS)

    current_int = (
        last_valid_value(buybox_arr, tracking_since, price_series=True)
        or last_valid_value(new_arr, tracking_since, price_series=True)
        or last_valid_value(amazon_arr, tracking_since, price_series=True)
    )
    if current_int is None:
        raise RuntimeError("No valid current price found in Keepa series.")
    current_price = price_to_float(current_int)

    rating_int = last_valid_value(rating_arr, tracking_since, price_series=False)
    rating = (
        rating_int / 10.0
        if rating_int is not None and rating_int >= 0
        else None
    )

    reviews_int = last_valid_value(reviews_arr, tracking_since, price_series=False)
    reviews = int(reviews_int) if reviews_int is not None and reviews_int >= 0 else None

    print("\n=== PRODUCT ===")
    print(f"Title:  {title}")
    print(f"ASIN:   {asin}")
    print(f"Price:  {currency}{current_price:.2f}")
    if rating is not None:
        print(f"Rating: {rating:.1f} ⭐")
    if reviews is not None:
        print(f"Reviews:{reviews}")

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
        yaxis_title=f"Price ({currency})" if currency else "Price",
        hovermode="x unified",
    )
    fig.show()


#Looping the code to make sure the program runs again
if __name__ == "__main__":
    again = "y"
    while again == "y" or again == "yes":
        main()
        again = input("\nRun again? (y/yes to continue): ").strip().lower()
    else:
        print("Goodbye!")


