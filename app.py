import os
DB = os.environ.get("DB_PATH", os.path.join(os.getcwd(), "waste.db"))
# then use DB wherever you previously used "waste.db"

from flask import Flask, render_template, request, redirect, send_file
import sqlite3, datetime, csv, os
from io import StringIO

app = Flask(__name__)

DB = "waste.db"
MONTHLY_LIMIT = 1000


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS waste
                 (id INTEGER PRIMARY KEY,
                  date TEXT,
                  business TEXT,
                  stream TEXT,
                  quantity REAL,
                  notes TEXT)''')
    conn.commit()
    conn.close()


def get_month_key():
    return datetime.date.today().strftime("%Y-%m")


@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Insert new entry
    if request.method == "POST":
        date = request.form["date"] or datetime.date.today().isoformat()
        business = request.form["business"]
        stream = request.form["stream"]
        qty = float(request.form["quantity"])
        notes = request.form.get("notes", "")
        c.execute("INSERT INTO waste (date, business, stream, quantity, notes) VALUES (?, ?, ?, ?, ?)",
                  (date, business, stream, qty, notes))
        conn.commit()

    # Fetch current month's totals
    month = get_month_key()
    c.execute("SELECT business, SUM(quantity) FROM waste WHERE date LIKE ? GROUP BY business", (f"{month}%",))
    business_totals = dict(c.fetchall())

    c.execute("SELECT stream, SUM(quantity) FROM waste WHERE date LIKE ? GROUP BY stream", (f"{month}%",))
    stream_totals = dict(c.fetchall())

    c.execute("SELECT date, SUM(quantity) FROM waste WHERE date LIKE ? GROUP BY date ORDER BY date", (f"{month}%",))
    trend = c.fetchall()

    c.execute("SELECT SUM(quantity) FROM waste WHERE date LIKE ?", (f"{month}%",))
    total = c.fetchone()[0] or 0

    # Fetch latest 10 entries
    c.execute("SELECT date, business, stream, quantity, notes FROM waste WHERE date LIKE ? ORDER BY id DESC LIMIT 10",
              (f"{month}%",))
    recent_entries = c.fetchall()

    conn.close()

    warn = total > 0.8 * MONTHLY_LIMIT

    return render_template("index.html",
                           total=total,
                           business_totals=business_totals,
                           stream_totals=stream_totals,
                           trend=trend,
                           recent_entries=recent_entries,
                           limit=MONTHLY_LIMIT,
                           warn=warn)


@app.route("/export")
def export_csv():
    month = get_month_key()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, business, stream, quantity, notes FROM waste WHERE date LIKE ? ORDER BY date", (f"{month}%",))
    rows = c.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Date", "Business", "Stream", "Quantity (kg)", "Notes"])
    cw.writerows(rows)
    output = si.getvalue()

    return send_file(
        StringIO(output),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"waste_{month}.csv"
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
