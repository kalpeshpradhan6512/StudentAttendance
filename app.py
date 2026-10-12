from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def connect_db():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn

def setup_db():
    conn = connect_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(student_id, date),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    conn.commit()
    conn.close()

setup_db()

@app.route("/", methods=["GET", "POST"])
def home():
    conn = connect_db()
    message = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name", "").strip()
            roll_no = request.form.get("roll_no", "").strip()

            if name and roll_no:
                try:
                    conn.execute(
                        "INSERT INTO students (name, roll_no) VALUES (?, ?)",
                        (name, roll_no)
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    message = "Roll number already exists."

        elif action == "attendance":
            date = request.form.get("date", "")
            if date:
                for student in conn.execute("SELECT id FROM students").fetchall():
                    status = request.form.get(f"status_{student['id']}")
                    if status in ("Present", "Absent"):
                        conn.execute("""
                            INSERT INTO attendance (student_id, date, status)
                            VALUES (?, ?, ?)
                            ON CONFLICT(student_id, date)
                            DO UPDATE SET status = excluded.status
                        """, (student["id"], date, status))
                conn.commit()

        elif action == "delete":
            student_id = request.form.get("student_id")
            if student_id:
                conn.execute(
                    "DELETE FROM attendance WHERE student_id = ?",
                    (student_id,)
                )
                conn.execute(
                    "DELETE FROM students WHERE id = ?",
                    (student_id,)
                )
                conn.commit()

        conn.close()
        if message:
            return message
        return redirect("/")

    students = conn.execute("""
        SELECT s.id, s.name, s.roll_no,
        (SELECT COUNT(*) FROM attendance a
         WHERE a.student_id = s.id AND a.status = 'Present') AS present_count,
        (SELECT COUNT(*) FROM attendance a
         WHERE a.student_id = s.id) AS total_count
        FROM students s ORDER BY s.id DESC
    """).fetchall()

    total = len(students)
    today = request.args.get("date")
    if not today:
        from datetime import date
        today = date.today().isoformat()

    present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'",
        (today,)
    ).fetchone()[0]

    absent = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'",
        (today,)
    ).fetchone()[0]

    records = conn.execute("""
        SELECT s.name, s.roll_no, a.status, a.date
        FROM attendance a JOIN students s ON s.id = a.student_id
        WHERE a.date = ? ORDER BY s.roll_no
    """, (today,)).fetchall()

    conn.close()

    return render_template(
        "index.html",
        students=students,
        total=total,
        present=present,
        absent=absent,
        today=today,
        records=records,
        message=message
    )

if __name__ == "__main__":
    app.run(debug=True)