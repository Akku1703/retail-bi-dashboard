import psycopg2
from datetime import date, timedelta

conn = psycopg2.connect(
    host="localhost",
    dbname="retail_bi",
    user="postgres",
    password="Akku@2003",
    port=5432
)
cur = conn.cursor()

# pretending today is this date since our data only goes up to end of 2025
simulated_today = date(2024, 1, 10)
yesterday = simulated_today - timedelta(days=1)

THRESHOLD = 0.30  # flag if sales dropped more than 30%

print(f"Checking sales for {yesterday}")

cur.execute("SELECT store_id, store_name FROM stores ORDER BY store_id")
all_stores = cur.fetchall()

anomalies_method1 = []
anomalies_method2 = []

for store_id, store_name in all_stores:

    # revenue for yesterday
    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE store_id = %s AND sale_date = %s
    """, (store_id, yesterday))
    yesterday_revenue = float(cur.fetchone()[0])

    # method 1: average of the same weekday over the last 4 weeks
    same_weekday_dates = [yesterday - timedelta(days=7 * i) for i in range(1, 5)]
    cur.execute("""
            SELECT COUNT(DISTINCT sale_date), COALESCE(AVG(daily_total), 0) FROM (
                SELECT sale_date, SUM(total_amount) AS daily_total
                FROM sales
                WHERE store_id = %s AND sale_date = ANY(%s)
                GROUP BY sale_date
            ) daily_sums
        """, (store_id, same_weekday_dates))
    days_found, trailing_avg = cur.fetchone()
    trailing_avg = float(trailing_avg)

    if days_found >= 3 and trailing_avg > 0:
        pct_change_1 = (yesterday_revenue - trailing_avg) / trailing_avg
        if pct_change_1 <= -THRESHOLD:
            anomalies_method1.append((store_name, yesterday_revenue, trailing_avg, pct_change_1))
    # method 2: compare to the same weekday last week only (single point, not averaged)
    last_week_same_day = yesterday - timedelta(days=7)
    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE store_id = %s AND sale_date = %s
    """, (store_id, last_week_same_day))
    last_week_revenue = float(cur.fetchone()[0])

    if last_week_revenue > 0:
        pct_change_2 = (yesterday_revenue - last_week_revenue) / last_week_revenue
        if pct_change_2 <= -THRESHOLD:
            anomalies_method2.append((store_name, yesterday_revenue, last_week_revenue, pct_change_2))

print("\nMethod 1 - same weekday, last 4 weeks average")
if anomalies_method1:
    for name, yest, avg, pct in anomalies_method1:
        print(f"{name}: {yest:,.2f} vs avg {avg:,.2f} ({pct*100:.1f}%)")
else:
    print("no anomalies")

print(f"\nMethod 2 - same day last week ({last_week_same_day})")
if anomalies_method2:
    for name, yest, last_wk, pct in anomalies_method2:
        print(f"{name}: {yest:,.2f} vs last week {last_wk:,.2f} ({pct*100:.1f}%)")
else:
    print("no anomalies")

cur.close()
conn.close()
