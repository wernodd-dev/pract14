import os

import psycopg2
from flask import Flask, jsonify, request

DEFAULT_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "library_db",
    "user": "postgres",
    "password": "secret",
}


def resolve_db_config(base):
    cfg = dict(base)
    if os.environ.get("PGHOST"):
        cfg["host"] = os.environ["PGHOST"]
    if os.environ.get("PGPORT"):
        cfg["port"] = int(os.environ["PGPORT"])
    if os.environ.get("PGUSER"):
        cfg["user"] = os.environ["PGUSER"]
    if "PGPASSWORD" in os.environ:
        cfg["password"] = os.environ["PGPASSWORD"]
    return cfg


def get_db_connection(db_config):
    return psycopg2.connect(**db_config)


def init_db(db_config):
    conn = get_db_connection(db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    birth_year INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(300) NOT NULL,
                    genre VARCHAR(100) DEFAULT '',
                    year_published INTEGER,
                    author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
                    created_by VARCHAR(200) NOT NULL
                )
            """)
            conn.commit()
    finally:
        conn.close()


def create_app(db_config=None):
    app = Flask(__name__)

    if db_config is None:
        db_config = resolve_db_config(DEFAULT_DB_CONFIG)
    else:
        db_config = resolve_db_config(db_config)

    app.config["DB_CONFIG"] = db_config

    init_db(db_config)

    @app.route("/api/authors", methods=["GET"])
    def get_authors():
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, birth_year FROM authors ORDER BY id"
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        authors = [
            {"id": r[0], "name": r[1], "birth_year": r[2]}
            for r in rows
        ]
        return jsonify(authors)

    @app.route("/api/authors", methods=["POST"])
    def create_author():
        data = request.json or {}

        if not data.get("name"):
            return jsonify({"error": "field 'name' is required"}), 400

        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO authors (name, birth_year)
                    VALUES (%s, %s)
                    RETURNING id, name, birth_year
                    """,
                    (data["name"], data.get("birth_year")),
                )
                row = cur.fetchone()
                conn.commit()
        finally:
            conn.close()

        return jsonify(
            {"id": row[0], "name": row[1], "birth_year": row[2]}
        ), 201

    @app.route("/api/authors/<int:author_id>", methods=["GET"])
    def get_author(author_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, birth_year FROM authors WHERE id = %s",
                    (author_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            return jsonify({"error": "Author not found"}), 404

        return jsonify({"id": row[0], "name": row[1], "birth_year": row[2]})

    @app.route("/api/authors/<int:author_id>", methods=["DELETE"])
    def delete_author(author_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM authors WHERE id = %s RETURNING id", (author_id,))
                deleted = cur.fetchone()
                conn.commit()
        finally:
            conn.close()

        if deleted is None:
            return jsonify({"error": "Author not found"}), 404

        return "", 204

    @app.route("/api/authors/<int:author_id>/books", methods=["GET"])
    def get_author_books(author_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM authors WHERE id = %s", (author_id,))
                if cur.fetchone() is None:
                    return jsonify({"error": "Author not found"}), 404

                cur.execute(
                    """
                    SELECT id, title, genre, year_published, author_id, created_by
                    FROM books WHERE author_id = %s ORDER BY id
                    """,
                    (author_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        books = [
            {
                "id": r[0],
                "title": r[1],
                "genre": r[2],
                "year_published": r[3],
                "author_id": r[4],
                "created_by": r[5],
            }
            for r in rows
        ]
        return jsonify(books)

    @app.route("/api/books", methods=["GET"])
    def get_books():
        genre = request.args.get("genre")
        author_id = request.args.get("author_id", type=int)
        q = request.args.get("q")

        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT id, title, genre, year_published, author_id, created_by
                    FROM books WHERE 1=1
                """
                params = []

                if genre is not None:
                    sql += " AND genre = %s"
                    params.append(genre)

                if author_id is not None:
                    sql += " AND author_id = %s"
                    params.append(author_id)

                if q:
                    sql += " AND LOWER(title) LIKE %s"
                    params.append(f"%{q.lower()}%")

                sql += " ORDER BY id"

                cur.execute(sql, params)
                rows = cur.fetchall()
        finally:
            conn.close()

        books = [
            {
                "id": r[0],
                "title": r[1],
                "genre": r[2],
                "year_published": r[3],
                "author_id": r[4],
                "created_by": r[5],
            }
            for r in rows
        ]
        return jsonify(books)

    @app.route("/api/books", methods=["POST"])
    def create_book():
        data = request.json or {}

        if not data.get("title"):
            return jsonify({"error": "field 'title' is required"}), 400

        if not data.get("created_by"):
            return jsonify({"error": "field 'created_by' is required"}), 400

        author_id = data.get("author_id")

        if author_id is not None:
            conn = get_db_connection(app.config["DB_CONFIG"])
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM authors WHERE id = %s", (author_id,))
                    if cur.fetchone() is None:
                        return jsonify({"error": "Author not found"}), 400
            finally:
                conn.close()

        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO books (title, genre, year_published, author_id, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, title, genre, year_published, author_id, created_by
                    """,
                    (
                        data["title"],
                        data.get("genre", ""),
                        data.get("year_published"),
                        author_id,
                        data["created_by"],
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        finally:
            conn.close()

        return jsonify(
            {
                "id": row[0],
                "title": row[1],
                "genre": row[2],
                "year_published": row[3],
                "author_id": row[4],
                "created_by": row[5],
            }
        ), 201

    @app.route("/api/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, genre, year_published, author_id, created_by
                    FROM books WHERE id = %s
                    """,
                    (book_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if row is None:
            return jsonify({"error": "Book not found"}), 404

        return jsonify(
            {
                "id": row[0],
                "title": row[1],
                "genre": row[2],
                "year_published": row[3],
                "author_id": row[4],
                "created_by": row[5],
            }
        )

    @app.route("/api/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        conn = get_db_connection(app.config["DB_CONFIG"])
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM books WHERE id = %s RETURNING id", (book_id,))
                deleted = cur.fetchone()
                conn.commit()
        finally:
            conn.close()

        if deleted is None:
            return jsonify({"error": "Book not found"}), 404

        return "", 204

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
