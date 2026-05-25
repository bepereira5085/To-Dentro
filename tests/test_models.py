from datetime import date
from to_dentro.models.user import User, UserType

def test_user_creation_and_persistence(db):
    """
    Testa a criação e a persistência (gravação e leitura) de uma entidade 'User'
    no banco de dados SQLite em memória utilizando a fixture 'db' para provar
    que o isolamento e a configuração dos modelos estão funcionando.
    """
    novo_usuario = User(
        name="João da Silva",
        email="joao@example.com",
        phone="27999998888",
        birth_date=date(1995, 5, 15),
        type=UserType.REGULAR,
    )
    novo_usuario.set_password("senha123_segura")

    db.session.add(novo_usuario)
    db.session.commit()

    usuario_recuperado = User.query.filter_by(email="joao@example.com").first()
    assert usuario_recuperado is not None
    assert usuario_recuperado.id is not None
    assert usuario_recuperado.name == "João da Silva"
    assert usuario_recuperado.phone == "27999998888"
    assert usuario_recuperado.birth_date == date(1995, 5, 15)
    assert usuario_recuperado.type == UserType.REGULAR
    
    assert usuario_recuperado.check_password("senha123_segura") is True
    assert usuario_recuperado.check_password("senha_incorreta") is False
