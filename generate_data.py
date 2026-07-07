import psycopg2
from datetime import date, timedelta
import random

# ---- DB CONNECTION ----
conn = psycopg2.connect(
    host="localhost",
    dbname="retail_bi",
    user="postgres",       # change if your pgAdmin user is different
    password="Akku@2003",  # replace with your actual password
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

# ---- 2. PRODUCTS: 15 products across 5 categories ----
products = [
    ("Samsung Galaxy A54", "Mobiles", 32999),
    ("iPhone 13", "Mobiles", 54999),
    ("OnePlus Nord CE3", "Mobiles", 24999),
    ("Samsung 55in QLED TV", "TVs", 62999),
    ("LG 43in Smart TV", "TVs", 34999),
    ("Sony Bravia 50in", "TVs", 54999),
    ("LG Front Load Washing Machine", "Appliances", 28999),
    ("Samsung Double Door Fridge", "Appliances", 36999),
    ("Voltas 1.5 Ton AC", "Appliances", 33999),
    ("HP Pavilion 15", "Laptops", 54999),
    ("Dell Inspiron 14", "Laptops", 48999),
    ("Lenovo IdeaPad Slim 5", "Laptops", 51999),
    ("boAt Airdopes 141", "Accessories", 1299),
    ("Samsung 25W Charger", "Accessories", 1499),
    ("Mi Power Bank 20000mAh", "Accessories", 1899),
]

product_ids = []
for name, category, price in products:
    cur.execute(
        "INSERT INTO products (product_name, category, unit_price) VALUES (%s, %s, %s) RETURNING product_id",
        (name, category, price)
    )
    product_ids.append((cur.fetchone()[0], category, price))

# ---- 3. CUSTOMERS: segments ----
segments = ["Retail", "Corporate", "Online"]
customer_ids = []
for seg in segments:
    for _ in range(20):  # 20 dummy customers per segment = 60 total
        cur.execute(
            "INSERT INTO customers (customer_segment) VALUES (%s) RETURNING customer_id",
            (seg,)
        )
        customer_ids.append(cur.fetchone()[0])

conn.commit()
print("Stores, products, customers loaded.")

# ---- 4. SALES: 2 years daily, with seasonality ----
start_date = date(2024, 1, 1)
end_date = date(2025, 12, 31)
current = start_date

def seasonality_multiplier(d):
    # Diwali roughly Oct-Nov, New Year Dec-Jan -> spike
    if d.month in (10, 11):
        return 2.2   # Diwali season
    elif d.month == 12 or d.month == 1:
        return 1.6   # New Year season
    elif d.weekday() >= 5:
        return 1.3   # weekend bump
    else:
        return 1.0

rows_inserted = 0
batch = []

while current <= end_date:
    mult = seasonality_multiplier(current)
    # number of transactions today, scaled by seasonality
    num_transactions = int(random.randint(15, 30) * mult)

    for _ in range(num_transactions):
        store_id = random.choice(store_ids)
        product_id, category, price = random.choice(product_ids)
        customer_id = random.choice(customer_ids)

        units = random.randint(1, 3) if category in ("Mobiles", "Laptops", "TVs", "Appliances") else random.randint(1, 5)
        total_amount = round(units * price * random.uniform(0.95, 1.0), 2)  # small discount variance

        batch.append((current, store_id, product_id, customer_id, units, total_amount))

    current += timedelta(days=1)

    # insert in batches of 1000 for speed
    if len(batch) >= 1000:
        cur.executemany(
            "INSERT INTO sales (sale_date, store_id, product_id, customer_id, units_sold, total_amount) VALUES (%s,%s,%s,%s,%s,%s)",
            batch
        )
        conn.commit()
        rows_inserted += len(batch)
        batch = []

# insert remaining
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