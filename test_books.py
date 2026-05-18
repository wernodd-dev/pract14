CREATED_BY = "Павло Хруустовський"


class TestBooks:
    def test_get_books_empty(self, client):
        response = client.get("/api/books")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_create_book(self, client):
        response = client.post(
            "/api/books",
            json={
                "title": "Повість",
                "genre": "novel",
                "year_published": 2020,
                "created_by": CREATED_BY,
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "Повість"
        assert data["genre"] == "novel"
        assert data["year_published"] == 2020
        assert data["created_by"] == CREATED_BY
        assert "id" in data

    def test_create_book_without_title(self, client):
        response = client.post(
            "/api/books",
            json={"created_by": CREATED_BY},
        )

        assert response.status_code == 400

    def test_create_book_without_created_by(self, client):
        response = client.post("/api/books", json={"title": "Без автора поля"})

        assert response.status_code == 400

    def test_create_book_with_author(self, client):
        author = client.post(
            "/api/authors",
            json={"name": "Леся Українка", "birth_year": 1871},
        ).get_json()

        response = client.post(
            "/api/books",
            json={
                "title": "Lisova Pisnia",
                "genre": "drama",
                "year_published": 1911,
                "author_id": author["id"],
                "created_by": CREATED_BY,
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["author_id"] == author["id"]
        assert data["created_by"] == CREATED_BY

    def test_create_book_with_nonexistent_author(self, client):
        response = client.post(
            "/api/books",
            json={
                "title": "Книга",
                "author_id": 99999,
                "created_by": CREATED_BY,
            },
        )

        assert response.status_code == 400

    def test_get_book_by_id(self, client):
        created = client.post(
            "/api/books",
            json={
                "title": "Знайти мене",
                "created_by": CREATED_BY,
            },
        ).get_json()

        response = client.get(f"/api/books/{created['id']}")

        assert response.status_code == 200
        assert response.get_json()["title"] == "Знайти мене"

    def test_get_book_not_found(self, client):
        response = client.get("/api/books/99999")

        assert response.status_code == 404

    def test_delete_book(self, client):
        created = client.post(
            "/api/books",
            json={"title": "Видалити", "created_by": CREATED_BY},
        ).get_json()

        response = client.delete(f"/api/books/{created['id']}")

        assert response.status_code == 204

        response = client.get(f"/api/books/{created['id']}")
        assert response.status_code == 404


class TestBooksFilter:
    def test_filter_by_genre(self, client):
        client.post(
            "/api/books",
            json={
                "title": "Kobzar",
                "genre": "poetry",
                "created_by": CREATED_BY,
            },
        )
        client.post(
            "/api/books",
            json={
                "title": "Tygrolovy",
                "genre": "novel",
                "created_by": CREATED_BY,
            },
        )

        response = client.get("/api/books?genre=poetry")
        data = response.get_json()

        assert len(data) == 1
        assert data[0]["title"] == "Kobzar"

    def test_filter_by_author_id(self, client):
        author = client.post(
            "/api/authors",
            json={"name": "Автор один"},
        ).get_json()

        client.post(
            "/api/books",
            json={
                "title": "Книга 1",
                "author_id": author["id"],
                "created_by": CREATED_BY,
            },
        )
        client.post(
            "/api/books",
            json={
                "title": "Інша",
                "created_by": CREATED_BY,
            },
        )

        response = client.get(f"/api/books?author_id={author['id']}")
        data = response.get_json()

        assert len(data) == 1
        assert data[0]["title"] == "Книга 1"

    def test_search_by_title(self, client):
        client.post(
            "/api/books",
            json={
                "title": "Kobzar",
                "genre": "poetry",
                "created_by": CREATED_BY,
            },
        )

        response = client.get("/api/books?q=kobzar")
        data = response.get_json()

        assert len(data) == 1
        assert data[0]["title"] == "Kobzar"

    def test_filter_no_results(self, client):
        client.post(
            "/api/books",
            json={
                "title": "Щось",
                "genre": "novel",
                "created_by": CREATED_BY,
            },
        )

        response = client.get("/api/books?genre=nonexistent_genre_xyz")

        assert response.status_code == 200
        assert response.get_json() == []
