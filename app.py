from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "waste.db"
MAX_MASS_ON_SITE = 1000  # kg

def ensure_table():
    """Ensure the waste table exists before any DB operations."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS waste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            business TEXT,
            stream TEXT,
            quantity REAL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    # Make sure table exists for GET or POST
    ensure_table()

    # Static dropdown choices (you can change this or source from DB)
    businesses = ["DAB", "CTI"]
    streams = ["ACN", "DCM"]

    # default date for form
    default_date = datetime.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        # Get and validate form values
        date = request.form.get("date", default_date)
        business = request.form.get("business", "").strip()
        stream = request.form.get("stream", "").strip()
        try:
            quantity = float(request.form.get("quantity", "0"))
        except ValueError:
            quantity = 0.0

        # Basic validation: require non-empty business/stream and positive quantity
        if business and stream and quantity >= 0:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute(
                "INSERT INTO waste (date, business, stream, quantity) VALUES (?, ?, ?, ?)",
                (date, business, stream, quantity)
            )
            conn.commit()
            conn.close()

        return redirect(url_for("index"))

    # GET path: fetch monthly rows (date, business, stream, quantity)
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
    conn.close()

    # Totals
    total = sum(row[3] for row in summary) if summary else 0.0
    usage_percent = min((total / MAX_MASS_ON_SITE * 100) if MAX_MASS_ON_SITE > 0 else 0, 100)

    # Aggregate dicts
    business_totals = {}
    stream_totals = {}
    for row in summary:
        _, b, s, q = row
        business_totals.setdefault(b, 0.0)
        business_totals[b] += q
        stream_totals.setdefault(s, 0.0)
        stream_totals[s] += q

    # Build ordered arrays for charts (so a label always has a corresponding value)
    ordered_stream_values = [stream_totals.get(s, 0.0) for s in streams]
    ordered_business_values = [business_totals.get(b, 0.0) for b in businesses]

    return render_template(
        "index.html",
        summary=summary,
        total=round(total, 2),
        business_totals=business_totals,
        stream_totals=stream_totals,
        businesses=businesses,
        streams=streams,
        ordered_stream_values=ordered_stream_values,
        ordered_business_values=ordered_business_values,
        default_date=default_date,
        usage_percent=round(usage_percent, 2),
        max_mass_on_site=MAX_MASS_ON_SITE
    )

@app.route("/export")
def export_csv():
    ensure_table()
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
