from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "waste.db"
MAX_MASS_ON_SITE = 1000  # max kg allowed on-site

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date = request.form.get("date", datetime.today().strftime("%Y-%m-%d"))
        business = request.form["business"]
        stream = request.form["stream"]
        quantity = float(request.form["quantity"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        # Create table if it doesn't exist
        c.execute("""
            CREATE TABLE IF NOT EXISTS waste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                business TEXT,
                stream TEXT,
                quantity REAL
            )
        """)
        # Insert entry
        c.execute(
            "INSERT INTO waste (date, business, stream, quantity) VALUES (?, ?, ?, ?)",
            (date, business, stream, quantity)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    # Monthly summary
    month = datetime.today().strftime("%Y-%m")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT date, business, stream, quantity
        FROM waste
        WHERE date LIKE ?
        ORDER BY date ASC
    """, (f"{month}%",))
    summary = c.fetchall()

    # Compute totals
    total = sum(row[3] for row in summary)
    usage_percent = total / MAX_MASS_ON_SITE * 100

    business_totals = {}
    stream_totals = {}
    for row in summary:
        business_totals.setdefault(row[1], 0)
        business_totals[row[1]] += row[3]
        stream_totals.setdefault(row[2], 0)
        stream_totals[row[2]] += row[3]

    conn.close()

    # Dropdown options
    businesses = ["DAB", "CTI"]
    streams = ["ACN", "DCM"]

    default_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "index.html",
        summary=summary,
        total=total,
        business_totals=business_totals,
        stream_totals=stream_totals,
        businesses=businesses,
        streams=streams,
        default_date=default_date,
        usage_percent=usage_percent
    )

@app.route("/export")
def export_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, business, stream, quantity FROM waste ORDER BY date ASC")
    rows = c.fetchall()
    conn.close()

    csv_content = "Date,Business,Stream,Quantity (kg)\n"
    csv_content += "\n".join([f"{r[0]},{r[1]},{r[2]},{r[3]}" for r in rows])

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=waste.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
