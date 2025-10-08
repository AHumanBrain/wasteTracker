# app.py
# Lines 1-10: imports
from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
from io import StringIO
import csv

# Line 12: app setup
app = Flask(__name__)
DB = "waste.db"

# After app = Flask(__name__) and DB = "waste.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Create the table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS waste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            business TEXT NOT NULL,
            stream TEXT NOT NULL,
            quantity REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Initialize the DB when the app starts
init_db()

# ROUTES
@app.route("/", methods=["GET", "POST"])
def index():
    # Step 1: handle POST
    if request.method == "POST":
        date = request.form.get("date", datetime.today().strftime("%Y-%m-%d"))
        business = request.form["business"]
        stream = request.form["stream"]
        quantity = float(request.form["quantity"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO waste (date, business, stream, quantity) VALUES (?, ?, ?, ?)",
            (date, business, stream, quantity)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    # Step 2: compute summary for current month
    month = datetime.today().strftime("%Y-%m")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT business, stream, SUM(quantity) 
        FROM waste 
        WHERE date LIKE ? 
        GROUP BY business, stream
    """, (f"{month}%",))
    summary = c.fetchall()

    # Step 3: get dropdown options for business and stream
    c.execute("SELECT DISTINCT business FROM waste")
    businesses = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT stream FROM waste")
    streams = [row[0] for row in c.fetchall()]
    conn.close()

    # Step 4: compute totals
    total = sum(row[2] for row in summary)
    business_totals = {}
    stream_totals = {}
    for row in summary:
        business_totals.setdefault(row[0], 0)
        business_totals[row[0]] += row[2]

        stream_totals.setdefault(row[1], 0)
        stream_totals[row[1]] += row[2]

    default_date = datetime.today().strftime("%Y-%m-%d")
    
    # Step 5: render template
    return render_template(
        "index.html",
        summary=summary,
        total=total,
        business_totals=business_totals,
        stream_totals=stream_totals,
        default_date=default_date,
        businesses=businesses,
        streams=streams,
        today=datetime.today().strftime("%Y-%m-%d")  # for default date input
    )

# CSV EXPORT ROUTE
@app.route("/export_csv")
def export_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, business, stream, quantity FROM waste ORDER BY date")
    rows = c.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Date", "Business", "Stream", "Quantity"])
    cw.writerows(rows)
    si.seek(0)

    return send_file(
        si,
        mimetype="text/csv",
        download_name=f"waste_export_{datetime.today().strftime('%Y-%m-%d')}.csv",
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
