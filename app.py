from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ==========================================
# FLASK SETTINGS
# ==========================================

app.secret_key = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY"

DATABASE = "freeverse.db"

NEWS_UPLOAD_FOLDER = "static/uploads/news"
FREELANCER_UPLOAD_FOLDER = "static/uploads/freelancers"

os.makedirs(
    NEWS_UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    FREELANCER_UPLOAD_FOLDER,
    exist_ok=True
)


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================
# CREATE DATABASE
# ==========================================

def create_database():

    conn = get_db()

    # --------------------------------------
    # NEWS TABLE
    # --------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            author TEXT NOT NULL,
            image TEXT
        )
    """)

    # Check whether image column exists
    columns = conn.execute(
        "PRAGMA table_info(news)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "image" not in column_names:

        conn.execute(
            "ALTER TABLE news ADD COLUMN image TEXT"
        )

    # --------------------------------------
    # COORDINATORS TABLE
    # --------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS coordinators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # --------------------------------------
    # DEFAULT COORDINATOR ACCOUNT
    # --------------------------------------

    existing = conn.execute(
        """
        SELECT id
        FROM coordinators
        WHERE email=?
        """,
        ("coordinator@freeverse.com",)
    ).fetchone()

    if not existing:

        password_hash = generate_password_hash(
            "ChangeThisPassword123!"
        )

        conn.execute("""
            INSERT INTO coordinators
            (
                name,
                email,
                password
            )
            VALUES (?, ?, ?)
        """, (
            "FREEVERSE Coordinator",
            "coordinator@freeverse.com",
            password_hash
        ))

    # --------------------------------------
    # FREELANCERS TABLE
    # --------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS freelancers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            year TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT NOT NULL,
            projects TEXT NOT NULL,
            email TEXT NOT NULL,
            linkedin TEXT,
            portfolio TEXT,
            image TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    conn.close()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# COORDINATOR LOGIN
# ==========================================

@app.route(
    "/coordinator-login",
    methods=["POST"]
)
def coordinator_login():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid request."
        }), 400

    email = data.get(
        "email",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    conn = get_db()

    coordinator = conn.execute(
        """
        SELECT *
        FROM coordinators
        WHERE email=?
        """,
        (email,)
    ).fetchone()

    conn.close()

    if coordinator and check_password_hash(
        coordinator["password"],
        password
    ):

        session["coordinator_id"] = (
            coordinator["id"]
        )

        session["coordinator_name"] = (
            coordinator["name"]
        )

        return jsonify({
            "success": True,
            "message": "Coordinator login successful."
        })

    return jsonify({
        "success": False,
        "message": "Invalid coordinator email or password."
    }), 401


# ==========================================
# COORDINATOR LOGIN STATUS
# ==========================================

@app.route(
    "/api/coordinator-status"
)
def coordinator_status():

    if "coordinator_id" in session:

        return jsonify({
            "logged_in": True,
            "name": session.get(
                "coordinator_name",
                "Coordinator"
            )
        })

    return jsonify({
        "logged_in": False
    })


# ==========================================
# COORDINATOR LOGOUT
# ==========================================

@app.route(
    "/coordinator-logout"
)
def coordinator_logout():

    session.pop(
        "coordinator_id",
        None
    )

    session.pop(
        "coordinator_name",
        None
    )

    return redirect("/")


# ==========================================
# GET NEWS
# ==========================================

@app.route(
    "/api/news",
    methods=["GET"]
)
def get_news():

    conn = get_db()

    news = conn.execute("""
        SELECT *
        FROM news
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([
        dict(item)
        for item in news
    ])


# ==========================================
# ADD NEWS
# ==========================================

@app.route(
    "/api/news",
    methods=["POST"]
)
def add_news():

    if "coordinator_id" not in session:

        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    title = request.form.get(
        "title",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if not title or not category or not description:

        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    image = request.files.get(
        "image"
    )

    image_filename = None

    if image and image.filename:

        filename = secure_filename(
            image.filename
        )

        if filename:

            unique_name = (
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                + "_"
                + filename
            )

            image_path = os.path.join(
                NEWS_UPLOAD_FOLDER,
                unique_name
            )

            image.save(
                image_path
            )

            image_filename = (
                "uploads/news/"
                + unique_name
            )

    date = datetime.now().strftime(
        "%B %Y"
    )

    conn = get_db()

    conn.execute("""
        INSERT INTO news
        (
            title,
            category,
            description,
            date,
            author,
            image
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        title,
        category,
        description,
        date,
        session.get(
            "coordinator_name",
            "FREEVERSE Coordinator"
        ),
        image_filename
    ))

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Update published successfully.",
        "image": image_filename
    })


# ==========================================
# DELETE NEWS
# ==========================================

@app.route(
    "/api/news/<int:news_id>",
    methods=["DELETE"]
)
def delete_news(news_id):

    if "coordinator_id" not in session:

        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    conn = get_db()

    news = conn.execute(
        """
        SELECT *
        FROM news
        WHERE id=?
        """,
        (news_id,)
    ).fetchone()

    if not news:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Post not found."
        }), 404

    image_path = news["image"]

    conn.execute(
        """
        DELETE FROM news
        WHERE id=?
        """,
        (news_id,)
    )

    conn.commit()

    conn.close()

    # Delete uploaded image
    if image_path:

        full_image_path = os.path.join(
            "static",
            image_path
        )

        if os.path.exists(
            full_image_path
        ):

            try:

                os.remove(
                    full_image_path
                )

            except OSError as error:

                print(
                    "Could not delete image:",
                    error
                )

    return jsonify({
        "success": True,
        "message": "Post deleted successfully."
    })


# ==========================================
# EDIT NEWS
# ==========================================

@app.route(
    "/api/news/<int:news_id>",
    methods=["PUT"]
)
def edit_news(news_id):

    if "coordinator_id" not in session:

        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    conn = get_db()

    news = conn.execute(
        """
        SELECT *
        FROM news
        WHERE id=?
        """,
        (news_id,)
    ).fetchone()

    if not news:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Post not found."
        }), 404

    title = request.form.get(
        "title",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if not title or not category or not description:

        conn.close()

        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    image_filename = news["image"]

    image = request.files.get(
        "image"
    )

    if image and image.filename:

        filename = secure_filename(
            image.filename
        )

        if filename:

            unique_name = (
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                + "_"
                + filename
            )

            image_path = os.path.join(
                NEWS_UPLOAD_FOLDER,
                unique_name
            )

            image.save(
                image_path
            )

            old_image = news["image"]

            if old_image:

                old_image_path = os.path.join(
                    "static",
                    old_image
                )

                if os.path.exists(
                    old_image_path
                ):

                    try:

                        os.remove(
                            old_image_path
                        )

                    except OSError as error:

                        print(
                            "Could not delete old image:",
                            error
                        )

            image_filename = (
                "uploads/news/"
                + unique_name
            )

    conn.execute(
        """
        UPDATE news
        SET
            title=?,
            category=?,
            description=?,
            image=?
        WHERE id=?
        """,
        (
            title,
            category,
            description,
            image_filename,
            news_id
        )
    )

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Post updated successfully."
    })


# ==========================================
# SUBMIT STUDENT FREELANCER PROFILE
# ==========================================

@app.route(
    "/api/freelancers",
    methods=["POST"]
)
def add_freelancer():

    name = request.form.get(
        "name",
        ""
    ).strip()

    year = request.form.get(
        "year",
        ""
    ).strip()

    department = request.form.get(
        "department",
        ""
    ).strip()

    role = request.form.get(
        "role",
        ""
    ).strip()

    skills = request.form.get(
        "skills",
        ""
    ).strip()

    projects = request.form.get(
        "projects",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    linkedin = request.form.get(
        "linkedin",
        ""
    ).strip()

    portfolio = request.form.get(
        "portfolio",
        ""
    ).strip()

    # --------------------------------------
    # REQUIRED FIELD VALIDATION
    # --------------------------------------

    if not name or not year or not department or not role:

        return jsonify({
            "success": False,
            "message": "Please fill in all required fields."
        }), 400

    if not skills or not projects or not email:

        return jsonify({
            "success": False,
            "message": "Please complete all required profile information."
        }), 400

    # --------------------------------------
    # PROFILE IMAGE
    # --------------------------------------

    image = request.files.get(
        "image"
    )

    image_filename = None

    if image and image.filename:

        filename = secure_filename(
            image.filename
        )

        if filename:

            unique_name = (
                datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                )
                + "_"
                + filename
            )

            image_path = os.path.join(
                FREELANCER_UPLOAD_FOLDER,
                unique_name
            )

            image.save(
                image_path
            )

            image_filename = (
                "uploads/freelancers/"
                + unique_name
            )

    # --------------------------------------
    # CREATED DATE
    # --------------------------------------

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------
    # SAVE PROFILE
    # --------------------------------------

    conn = get_db()

    conn.execute("""
        INSERT INTO freelancers
        (
            name,
            year,
            department,
            role,
            skills,
            projects,
            email,
            linkedin,
            portfolio,
            image,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        year,
        department,
        role,
        skills,
        projects,
        email,
        linkedin,
        portfolio,
        image_filename,
        "pending",
        created_at
    ))

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Freelancer profile submitted successfully. It is waiting for coordinator approval."
    })


# ==========================================
# GET FREELANCER PROFILES
# ==========================================

@app.route(
    "/api/freelancers",
    methods=["GET"]
)
def get_freelancers():

    conn = get_db()

    freelancers = conn.execute("""
        SELECT *
        FROM freelancers
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([
        dict(item)
        for item in freelancers
    ])


# ==========================================
# GET ONLY APPROVED FREELANCERS
# ==========================================

@app.route(
    "/api/freelancers/approved",
    methods=["GET"]
)
def get_approved_freelancers():

    conn = get_db()

    freelancers = conn.execute("""
        SELECT *
        FROM freelancers
        WHERE status='approved'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([
        dict(item)
        for item in freelancers
    ])


# ==========================================
# COORDINATOR APPROVE FREELANCER
# ==========================================

@app.route(
    "/api/freelancers/<int:freelancer_id>/approve",
    methods=["PUT"]
)
def approve_freelancer(freelancer_id):

    if "coordinator_id" not in session:

        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    conn = get_db()

    freelancer = conn.execute(
        """
        SELECT *
        FROM freelancers
        WHERE id=?
        """,
        (freelancer_id,)
    ).fetchone()

    if not freelancer:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Freelancer profile not found."
        }), 404

    conn.execute(
        """
        UPDATE freelancers
        SET status='approved'
        WHERE id=?
        """,
        (freelancer_id,)
    )

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Freelancer profile approved successfully."
    })


# ==========================================
# COORDINATOR REJECT FREELANCER
# ==========================================

@app.route(
    "/api/freelancers/<int:freelancer_id>/reject",
    methods=["PUT"]
)
def reject_freelancer(freelancer_id):

    if "coordinator_id" not in session:

        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    conn = get_db()

    freelancer = conn.execute(
        """
        SELECT *
        FROM freelancers
        WHERE id=?
        """,
        (freelancer_id,)
    ).fetchone()

    if not freelancer:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Freelancer profile not found."
        }), 404

    conn.execute(
        """
        UPDATE freelancers
        SET status='rejected'
        WHERE id=?
        """,
        (freelancer_id,)
    )

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Freelancer profile rejected."
    })


# ==========================================
# DELETE FREELANCER PROFILE
# ==========================================

@app.route(
    "/api/freelancers/<int:freelancer_id>",
    methods=["DELETE"]
)
def delete_freelancer(freelancer_id):

    if "coordinator_id" not in session:
        return jsonify({
            "success": False,
            "message": "Coordinator login required."
        }), 401

    conn = get_db()

    freelancer = conn.execute(
        "SELECT * FROM freelancers WHERE id=?",
        (freelancer_id,)
    ).fetchone()

    if not freelancer:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Freelancer profile not found."
        }), 404

    image_path = freelancer["image"]

    conn.execute(
        "DELETE FROM freelancers WHERE id=?",
        (freelancer_id,)
    )

    conn.commit()
    conn.close()

    if image_path:
        full_path = os.path.join(
            "static",
            image_path
        )

        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    return jsonify({
        "success": True,
        "message": "Freelancer profile deleted successfully."
    })
    if __name__ == "__main__":
     create_database()

    app.run(
        debug=True
    )