from flask import Flask, render_template, request, redirect, url_for, session, abort
import sqlite3
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# For local project testing
app.secret_key = "smart-campus-hub-demo-key"


def get_db():
    return sqlite3.connect("database.db")


def get_current_time():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            issue TEXT NOT NULL,
            room TEXT NOT NULL,
            priority TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted'
        )
    """)

    columns = [
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(requests)"
        ).fetchall()
    ]

    if "user_id" not in columns:
        connection.execute("""
            ALTER TABLE requests
            ADD COLUMN user_id INTEGER
        """)

    if "created_at" not in columns:
        connection.execute("""
            ALTER TABLE requests
            ADD COLUMN created_at TEXT
        """)

        connection.execute(
            """
            UPDATE requests
            SET created_at = ?
            WHERE created_at IS NULL
            """,
            (get_current_time(),)
        )

    student = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("student",)
    ).fetchone()

    if student is None:
        connection.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "student",
                generate_password_hash("student123"),
                "student"
            )
        )

    admin = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:
        connection.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "admin",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    connection.commit()
    connection.close()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            abort(403)

        return function(*args, **kwargs)

    return wrapper


@app.route("/")
def home():

    stats = {
        "total": 0,
        "submitted": 0,
        "progress": 0,
        "resolved": 0
    }

    recent_requests = []

    if "user_id" in session:

        connection = get_db()

        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM requests
            WHERE user_id = ? OR user_id IS NULL
            """,
            (session["user_id"],)
        ).fetchone()[0]

        submitted = connection.execute(
            """
            SELECT COUNT(*)
            FROM requests
            WHERE (user_id = ? OR user_id IS NULL)
            AND status = 'Submitted'
            """,
            (session["user_id"],)
        ).fetchone()[0]

        progress = connection.execute(
            """
            SELECT COUNT(*)
            FROM requests
            WHERE (user_id = ? OR user_id IS NULL)
            AND status = 'In Progress'
            """,
            (session["user_id"],)
        ).fetchone()[0]

        resolved = connection.execute(
            """
            SELECT COUNT(*)
            FROM requests
            WHERE (user_id = ? OR user_id IS NULL)
            AND status = 'Resolved'
            """,
            (session["user_id"],)
        ).fetchone()[0]

        recent_requests = connection.execute(
            """
            SELECT
                id,
                category,
                issue,
                room,
                priority,
                description,
                status,
                created_at
            FROM requests
            WHERE user_id = ? OR user_id IS NULL
            ORDER BY id DESC
            LIMIT 3
            """,
            (session["user_id"],)
        ).fetchall()

        connection.close()

        stats = {
            "total": total,
            "submitted": submitted,
            "progress": progress,
            "resolved": resolved
        }

    return render_template(
        "index.html",
        stats=stats,
        recent_requests=recent_requests
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        connection = get_db()

        user = connection.execute(
            """
            SELECT id, username, password, role
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]

            if user[3] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


@app.route("/create-request", methods=["GET", "POST"])
@login_required
def create_request():

    if request.method == "POST":

        category = request.form.get("category", "").strip()
        issue = request.form.get("issue", "").strip()
        room = request.form.get("room", "").strip()
        priority = request.form.get("priority", "").strip()
        description = request.form.get("description", "").strip()

        allowed_categories = {
            "Lab",
            "Library",
            "ID Card",
            "Network",
            "Other"
        }

        allowed_priorities = {
            "Low",
            "Medium",
            "High"
        }

        # Server-side validation
        if not category or not issue or not room or not priority or not description:

            return render_template(
                "create_request.html",
                error="Please fill in all fields before submitting."
            )

        if category not in allowed_categories:

            return render_template(
                "create_request.html",
                error="Please select a valid category."
            )

        if priority not in allowed_priorities:

            return render_template(
                "create_request.html",
                error="Please select a valid priority."
            )

        if len(issue) > 100:

            return render_template(
                "create_request.html",
                error="Issue must be 100 characters or less."
            )

        if len(room) > 100:

            return render_template(
                "create_request.html",
                error="Room / Location must be 100 characters or less."
            )

        if len(description) > 500:

            return render_template(
                "create_request.html",
                error="Description must be 500 characters or less."
            )

        created_at = get_current_time()

        connection = get_db()

        connection.execute(
            """
            INSERT INTO requests
            (
                category,
                issue,
                room,
                priority,
                description,
                status,
                user_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                issue,
                room,
                priority,
                description,
                "Submitted",
                session["user_id"],
                created_at
            )
        )

        connection.commit()
        connection.close()

        return redirect(
            url_for("create_request", success=1)
        )

    success = request.args.get("success")

    return render_template(
        "create_request.html",
        success=success
    )


@app.route("/my-requests")
@login_required
def my_requests():

    connection = get_db()

    all_requests = connection.execute(
        """
        SELECT
            id,
            category,
            issue,
            room,
            priority,
            description,
            status,
            created_at
        FROM requests
        WHERE user_id = ? OR user_id IS NULL
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "my_requests.html",
        requests=all_requests
    )


@app.route("/admin")
@admin_required
def admin_dashboard():

    connection = get_db()

    all_requests = connection.execute(
        """
        SELECT
            id,
            category,
            issue,
            room,
            priority,
            description,
            status,
            created_at
        FROM requests
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        requests=all_requests
    )


@app.route("/update-status/<int:request_id>", methods=["POST"])
@admin_required
def update_status(request_id):

    new_status = request.form.get("status")

    allowed_statuses = {
        "Submitted",
        "In Progress",
        "Resolved"
    }

    if new_status not in allowed_statuses:
        abort(400)

    connection = get_db()

    connection.execute(
        """
        UPDATE requests
        SET status = ?
        WHERE id = ?
        """,
        (new_status, request_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)