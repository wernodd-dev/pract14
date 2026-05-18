CREATED_BY = "Павло Хруустовський"


class TestAuthors:
    def test_get_authors_empty(self, client):
        response = client.get("/api/authors")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_create_author(self, client):
        response = client.post(
            "/api/authors",
            json={
                "name": "Тарас Шевченко",
                "birth_year": 1814,
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Тарас Шевченко"
        assert data["birth_year"] == 1814
        assert "id" in data

    def test_create_author_without_name(self, client):
        response = client.post("/api/authors", json={"birth_year": 1900})

        assert response.status_code == 400

    def test_get_author_by_id(self, client):
        created = client.post(
            "/api/authors",
            json={"name": "Леся Українка", "birth_year": 1871},
        ).get_json()

        response = client.get(f"/api/authors/{created['id']}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Леся Українка"
        assert data["birth_year"] == 1871

    def test_get_author_not_found(self, client):
        response = client.get("/api/authors/99999")

        assert response.status_code == 404

    def test_delete_author(self, client):
        created = client.post(
            "/api/authors",
            json={"name": "Видалити мене", "birth_year": 2000},
        ).get_json()

        response = client.delete(f"/api/authors/{created['id']}")

        assert response.status_code == 204

        response = client.get(f"/api/authors/{created['id']}")
        assert response.status_code == 404

    def test_delete_author_not_found(self, client):
        response = client.delete("/api/authors/99999")

        assert response.status_code == 404

    def test_delete_author_keeps_books(self, client):
        author = client.post(
            "/api/authors",
            json={"name": "Іван Франко"},
        ).get_json()

        book = client.post(
            "/api/books",
            json={
                "title": "Zakhar Berkut",
                "author_id": author["id"],
                "created_by": CREATED_BY,
            },
        ).get_json()

        client.delete(f"/api/authors/{author['id']}")

        response = client.get(f"/api/books/{book['id']}")
        assert response.status_code == 200
        assert response.get_json()["author_id"] is None


class TestAuthorBooks:
    def test_get_author_books(self, client):
        author = client.post(
            "/api/authors",
            json={"name": "Леся Українка", "birth_year": 1871},
        ).get_json()

        client.post(
            "/api/books",
            json={
                "title": "Lisova Pisnia",
                "genre": "drama",
                "year_published": 1911,
                "author_id": author["id"],
                "created_by": CREATED_BY,
            },
        )

        response = client.get(f"/api/authors/{author['id']}/books")
        data = response.get_json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["title"] == "Lisova Pisnia"

    def test_get_author_books_empty(self, client):
        author = client.post(
            "/api/authors",
            json={"name": "Без книг"},
        ).get_json()

        response = client.get(f"/api/authors/{author['id']}/books")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_get_author_books_not_found(self, client):
        response = client.get("/api/authors/99999/books")

        assert response.status_code == 404
