import pytest
from datetime import date
from to_dentro import create_app
from to_dentro.ext.db import db as _db

@pytest.fixture(scope="session")
def app():
    """
    Fixture principal que inicializa a aplicação Flask usando o Application Factory.
    Configura a aplicação para o modo de testes:
    - TESTING: Habilita o comportamento de testes do Flask.
    - SQLALCHEMY_DATABASE_URI: Banco de dados SQLite em memória para garantir rapidez e isolamento.
    - WTF_CSRF_ENABLED: Desabilita a proteção CSRF nos formulários para simplificar os testes de envio de dados.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    
    return app

@pytest.fixture(scope="function")
def client(app):
    """
    Fixture que fornece o cliente de testes (test client) do Flask.
    Permite simular requisições HTTP (GET, POST, etc.) diretamente contra a aplicação.
    """
    return app.test_client()

@pytest.fixture(scope="function")
def db(app):
    """
    Fixture que gerencia a inicialização e limpeza do banco de dados em memória.
    A cada execução de teste:
    - Cria todas as tabelas (db.create_all())
    - Libera para o teste rodar (yield)
    - Limpa a sessão e apaga todas as tabelas (db.drop_all()) para garantir o isolamento perfeito.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()
