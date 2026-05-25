def test_index_returns_200(client):
    """
    Testa se a rota principal ('/') do blueprint 'main' está ativa,
    retornando o status HTTP 200 OK.
    """
    response = client.get("/")
    assert response.status_code == 200
