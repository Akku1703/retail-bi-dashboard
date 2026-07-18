import psycopg2
import sys
from datetime import date, timedelta, datetime

conn = psycopg2.connect(
    host="localhost",
    dbname="retail_bi",
    user="postgres",
    password="Akku@2003",
    port=5432
)
cur = conn.cursor()

# get the date to check from the command line, e.g. python3 anomaly_check.py 2024-06-15
# if nothing is typed, default to a fallback date so the script still runs
if len(sys.argv) > 1:
    simulated_today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
else:
    simulated_today = date.today()
    print(f"No date given, using today: {simulated_today}")

yesterday = simulated_today - timedelta(days=1)

THRESHOLD = 0.30  # flag if sales dropped more than 30%

log_lines = []
log_lines.append(f"Anomaly check run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log_lines.append(f"Checking sales for {yesterday}")

print(f"Checking sales for {yesterday}")

cur.execute("SELECT store_id, store_name FROM stores ORDER BY store_id")
all_stores = cur.fetchall()

anomalies_method1 = []
anomalies_method2 = []

for store_id, store_name in all_stores:

    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE store_id = %s AND sale_date = %s
    """, (store_id, yesterday))
    yesterday_revenue = float(cur.fetchone()[0])

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
log_lines.append("")
log_lines.append("Method 1 - same weekday, last 4 weeks average")
if anomalies_method1:
    for name, yest, avg, pct in anomalies_method1:
        line = f"{name}: {yest:,.2f} vs avg {avg:,.2f} ({pct*100:.1f}%)"
        print(line)
        log_lines.append(line)
else:
    print("no anomalies")
    log_lines.append("no anomalies")

print(f"\nMethod 2 - same day last week ({last_week_same_day})")
log_lines.append("")
log_lines.append(f"Method 2 - same day last week ({last_week_same_day})")
if anomalies_method2:
    for name, yest, last_wk, pct in anomalies_method2:
        line = f"{name}: {yest:,.2f} vs last week {last_wk:,.2f} ({pct*100:.1f}%)"
        print(line)
        log_lines.append(line)
else:
    print("no anomalies")
    log_lines.append("no anomalies")

log_lines.append("-" * 40)

# append this run's results to a log file, so past checks aren't lost
with open("anomaly_log.txt", "a") as f:
    f.write("\n".join(log_lines) + "\n")

cur.close()
conn.close()
