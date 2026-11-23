def test_users_index(client):
    response = client.get("/users/")
    assert response.status_code == 200