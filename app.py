from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "waste.db"  # adjust path if needed

# Ensure the table exists at app startup
def init_db():
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

init_db()

@app.route("/", methods=["GET", "POST"])
def index():
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

    # Display monthly summary
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

    # Compute totals
    total = sum(row[2] for row in summary)
    business_totals = {}
    stream_totals = {}
    for row in summary:
        business_totals.setdefault(row[0], 0)
        business_totals[row[0]] += row[2]
        stream_totals.setdefault(row[1], 0)
        stream_totals[row[1]] += row[2]

    conn.close()

    # Dropdown options
    businesses = ["DAB", "CTI"]
    streams = ["ACN", "DCM"]

    # Default date for form and footer
    default_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "index.html",
        summary=summary,
        total=total,
        business_totals=business_totals,
        stream_totals=stream_totals,
        businesses=businesses,
        streams=streams,
        default_date=default_date
    )

# CSV export route
@app.route("/export")
def export_csv():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, business, stream, quantity FROM waste")
    rows = c.fetchall()
    conn.close()

    csv_content = "Date,Business,Stream,Quantity\n"
    csv_content += "\n".join([f"{r[0]},{r[1]},{r[2]},{r[3]}" for r in rows])

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=waste.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
