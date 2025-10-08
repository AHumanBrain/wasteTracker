import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
from datetime import datetime

# -----------------------------
# DATABASE SETUP
# -----------------------------
DB = os.environ.get("DB_PATH", os.path.join(os.getcwd(), "waste.db"))

# Ensure directory exists
os.makedirs(os.path.dirname(DB), exist_ok=True)

# Create table if it doesn't exist
conn = sqlite3.connect(DB)
c = conn.cursor()
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

def init_db():
    # Optional: additional initialization logic
    pass

# -----------------------------
# FLASK APP SETUP
# -----------------------------
app = Flask(__name__)

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Example form data
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
    conn.close()

    # Compute total and by-business totals
    total = sum(row[2] for row in summary)
    business_totals = {}
    for row in summary:
        business_totals.setdefault(row[0], 0)
        business_totals[row[0]] += row[2]

    return render_template("index.html", summary=summary, total=total, business_totals=business_totals)

# -----------------------------
# CSV EXPORT ROUTE
# -----------------------------
@app.route("/export")
def export_csv():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM waste", conn)
    conn.close()
    df.to_csv("waste_backup.csv", index=False)
    return send_file("waste_backup.csv", as_attachment=True)

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
