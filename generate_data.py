import psycopg2
from datetime import date, timedelta
import random

# ---- DB CONNECTION ----
conn = psycopg2.connect(
    host="localhost",
    dbname="retail_bi",
    user="postgres",
    password="Akku@2003",  # your actual password
    port=5432
)
cur = conn.cursor()

# ---- 1. STORES: 8 stores across 5 southern states ----
stores = [
    ("Croma Kochi",       "Kerala",         "Kochi"),
    ("Croma Trivandrum",  "Kerala",         "Trivandrum"),
    ("Croma Bangalore",   "Karnataka",      "Bangalore"),
    ("Croma Mysore",      "Karnataka",      "Mysore"),
    ("Croma Chennai",     "Tamil Nadu",     "Chennai"),
    ("Croma Coimbatore",  "Tamil Nadu",     "Coimbatore"),
    ("Croma Hyderabad",   "Telangana",      "Hyderabad"),
    ("Croma Vizag",       "Andhra Pradesh", "Visakhapatnam"),
]

cur.execute("DELETE FROM sales")
cur.execute("DELETE FROM stores")
cur.execute("DELETE FROM products")
cur.execute("DELETE FROM customers")
conn.commit()

store_ids = []
for name, region, city in stores:
    cur.execute(
        "INSERT INTO stores (store_name, region, city) VALUES (%s, %s, %s) RETURNING store_id",
        (name, region, city)
    )
    store_ids.append(cur.fetchone()[0])

# ---- 2. PRODUCTS: current-gen lineup, appliances split into sub-categories ----
products = [
    ("Samsung Galaxy S24 FE", "Mobiles", 39999),
    ("iPhone 16", "Mobiles", 79999),
    ("OnePlus 13R", "Mobiles", 39999),
    ("Samsung 55in QLED TV", "TVs", 62999),
    ("LG 43in Smart TV", "TVs", 34999),
    ("Sony Bravia 50in", "TVs", 54999),
    ("LG Front Load Washing Machine", "Appliances_Washing", 28999),
    ("Samsung Double Door Fridge", "Appliances_Fridge", 36999),
    ("Voltas 1.5 Ton AC", "Appliances_AC", 33999),
    ("HP Pavilion 15", "Laptops", 54999),
    ("Dell Inspiron 14", "Laptops", 48999),
    ("Lenovo IdeaPad Slim 5", "Laptops", 51999),
    ("boAt Airdopes 141", "Accessories", 1299),
    ("Samsung 25W Charger", "Accessories", 1499),
    ("Mi Power Bank 20000mAh", "Accessories", 1899),
]

# product_ids now stores (id, category, price, name) - name needed for the multiplier lookup below
product_ids = []
for name, category, price in products:
    cur.execute(
        "INSERT INTO products (product_name, category, unit_price) VALUES (%s, %s, %s) RETURNING product_id",
        (name, category, price)
    )
    product_ids.append((cur.fetchone()[0], category, price, name))

# ---- 3. CUSTOMERS ----
segments = ["Retail", "Corporate", "Online"]
customer_ids = []
for seg in segments:
    for _ in range(20):
        cur.execute(
            "INSERT INTO customers (customer_segment) VALUES (%s) RETURNING customer_id",
            (seg,)
        )
        customer_ids.append(cur.fetchone()[0])

conn.commit()
print("Stores, products, customers loaded.")

# ---- 4. SALES LOGIC ----

def get_day_type(d):
    if d.weekday() == 4:
        return 'friday'
    elif d.weekday() in (5, 6):
        return 'weekend'
    return 'weekday'

def is_festival(d):
    return d.month in (10, 11) or (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 5)

def get_season(d):
    if d.month in (4, 5, 6):
        return 'summer'
    elif d.month in (11, 12, 1):
        return 'winter'
    return 'normal'

def daily_revenue_cap(day_type, festival):
    if day_type == 'weekend':
        base = random.uniform(800000, 2000000)
    elif day_type == 'friday':
        base = random.uniform(400000, 900000)
    else:
        base = random.uniform(400000, 1200000)
    if festival:
        base *= random.uniform(1.5, 2.5)
        # rare mega-day: ~1 in 150 festival days per store hits 1 Cr+
        if random.random() < 0.007:
            base = random.uniform(9500000, 11000000)
    return base

def units_for_category(category, day_type, season, festival):
    if category == "Accessories":
        base = random.randint(15, 22) if day_type != 'weekend' else random.randint(20, 30)
        return base

    elif category == "Appliances_AC":
        if season == 'summer':
            base = random.randint(4, 6) if day_type != 'weekend' else random.randint(18, 28)
        else:
            base = 0 if day_type != 'weekend' else random.randint(1, 3)
        return base

    elif category == "TVs":
        base = random.randint(3, 5) if day_type != 'weekend' else random.randint(5, 9)
        if festival:
            base = int(base * 1.5)
        return base

    elif category == "Appliances_Washing":
        base = random.randint(2, 4)
        if season == 'winter':
            base = int(base * 1.6)
        return base

    elif category == "Appliances_Fridge":
        base = random.randint(1, 3)
        if season == 'summer' or festival:
            base = int(base * 1.6)
        return base

    elif category == "Mobiles":
        base = random.randint(3, 6) if day_type != 'weekend' else random.randint(5, 9)
        if festival:
            base = int(base * random.uniform(2, 3))
        return base

    elif category == "Laptops":
        base = random.randint(1, 2) if day_type != 'weekend' else random.randint(2, 3)
        if festival:
            base = int(base * 1.5)
        return base

    return random.randint(1, 2)

# per-product unit multiplier: adjusts WITHIN a category so mass-market models
# outsell premium models in units, even though premium models earn more revenue per unit
product_unit_multiplier = {
    "LG 43in Smart TV": 1.0,
    "Samsung 55in QLED TV": 0.35,
    "Sony Bravia 50in": 0.3,
    "Samsung Galaxy S24 FE": 1.0,
    "OnePlus 13R": 0.85,
    "iPhone 16": 0.4,
    "Dell Inspiron 14": 1.0,
    "HP Pavilion 15": 0.6,
    "Lenovo IdeaPad Slim 5": 0.55,
}

start_date = date(2024, 1, 1)
end_date = date(2025, 12, 31)
current = start_date

rows_inserted = 0
batch = []

while current <= end_date:
    day_type = get_day_type(current)
    season = get_season(current)
    festival = is_festival(current)

    for store_id in store_ids:
        cap = daily_revenue_cap(day_type, festival)
        day_transactions = []
        running_total = 0

        for pid, category, price, name in product_ids:
            units = units_for_category(category, day_type, season, festival)
            multiplier = product_unit_multiplier.get(name, 1.0)
            units = max(0, int(units * multiplier))
            if units > 0:
                amount = units * price * random.uniform(0.95, 1.0)
                day_transactions.append((pid, units, amount))
                running_total += amount

        if running_total > cap and running_total > 0:
            scale = cap / running_total
            day_transactions = [
                (pid, max(1, int(u * scale)), amt * scale)
                for pid, u, amt in day_transactions
            ]

        for pid, units, amount in day_transactions:
            customer_id = random.choice(customer_ids)
            batch.append((current, store_id, pid, customer_id, units, round(amount, 2)))

    current += timedelta(days=1)

    if len(batch) >= 1000:
        cur.executemany(
            "INSERT INTO sales (sale_date, store_id, product_id, customer_id, units_sold, total_amount) VALUES (%s,%s,%s,%s,%s,%s)",
            batch
        )
        conn.commit()
        rows_inserted += len(batch)
        batch = []

if batch:
    cur.executemany(
        "INSERT INTO sales (sale_date, store_id, product_id, customer_id, units_sold, total_amount) VALUES (%s,%s,%s,%s,%s,%s)",
        batch
    )
    conn.commit()
    rows_inserted += len(batch)

print(f"Done. Approximately {rows_inserted} sales rows inserted.")

cur.close()
conn.close()