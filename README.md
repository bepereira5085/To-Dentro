# Tô Dentro! 🎉

**Tô Dentro!** é uma plataforma focada na democratização do acesso e divulgação de eventos locais e comunitários. 
O objetivo do sistema é conectar organizadores de eventos culturais, feiras, shows e workshops ao público da região, promovendo engajamento social.

Os usuários podem explorar eventos próximos (baseado no CEP), demonstrar interesse clicando em "Tô dentro!", seguir amigos para ver em quais eventos eles estão participando, e receber notificações de recomendações ou interações na plataforma.

## 🚀 Tecnologias Utilizadas

**Backend & Core:**
- [Python 3.9+](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/) - Framework web (utilizando padrão Application Factory)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) - ORM para mapeamento das entidades do banco
- [Flask-Migrate](https://flask-migrate.readthedocs.io/) - Migrações de banco de dados via Alembic
- [Flask-Login](https://flask-login.readthedocs.io/) - Gerenciamento de sessão de usuários
- [Flask-WTF / WTForms](https://flask-wtf.readthedocs.io/) - Validação de formulários no lado do servidor

**Frontend & UI:**
- HTML5, CSS3 e JavaScript Vanilla
- [Bulma CSS](https://bulma.io/) - Framework CSS responsivo
- [Jinja2](https://jinja.palletsprojects.com/) - Motor de templates do Flask
- Google Material Symbols e Fonts (Inter)

**Serviços de Terceiros / APIs:**
- [Cloudinary](https://cloudinary.com/) - Gerenciamento e hospedagem das imagens de eventos
- [ViaCEP](https://viacep.com.br/) - Autopreenchimento de endereços
- OpenStreetMap Nominatim - Geocodificação para cálculo de distância

**Qualidade & Testes (Desenvolvimento):**
- [Pytest](https://pytest.org/) e pytest-cov - Testes automatizados
- Black, Flake8, Isort - Padronização de código

---

## 🛠️ Requisitos

- Python 3.9 ou superior
- Git (para versionamento e clonagem)

---

## ⚙️ Instalação e Execução

Siga os passos abaixo para preparar o ambiente de desenvolvimento na sua máquina local:

### 1. Clonar o repositório
```bash
git clone https://github.com/seu-usuario/to-dentro.git
cd to-dentro
```

### 2. Criar e ativar o ambiente virtual (Recomendado)
Para isolar as dependências do projeto:
```bash
# No Windows
python -m venv venv
venv\Scripts\activate

# No Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as dependências do projeto
Você pode instalar a aplicação no modo editável (`-e`), o que facilita o desenvolvimento local.
```bash
# Instala as dependências padrão (para rodar a aplicação)
pip install -e .

# OU para instalar também as ferramentas de desenvolvimento e testes (Pytest, Black, etc):
pip install -e ".[dev]"
```

### 4. Configurar as variáveis de ambiente
O projeto utiliza variáveis de ambiente geridas via `python-dotenv`.
Verifique se na raiz do projeto existe o arquivo `.env.dev`. Caso utilize um banco de dados de produção ou precise de chaves reais do Cloudinary, você poderá modificá-las lá ou criar um arquivo `.env` para substituir os valores locais.

### 5. Gerenciar o Banco de Dados
A aplicação possui comandos personalizados no CLI do Flask para facilitar o gerenciamento do banco de dados local (SQLite padrão). 

Para criar o banco de dados e as tabelas:
```bash
flask createdb
```

Caso precise apagar o banco de dados e limpá-lo completamente:
```bash
flask cleardb
```

### 6. Popular o Banco com Dados Iniciais (Opcional)
Para facilitar o desenvolvimento, você pode preencher o banco de dados com dados falsos (mock data) como categorias, usuários e eventos executando o comando de seed:
```bash
flask dbseed
```

### 7. Executar a Aplicação
Com tudo pronto, suba o servidor embutido do Flask:
```bash
flask run
```

O aplicativo estará rodando em: `http://127.0.0.1:5000/`.

## 🧪 Rodando os Testes
Se você instalou as dependências de desenvolvimento (`[dev]`), pode rodar os testes automatizados com o seguinte comando na raiz do projeto:
```bash
pytest
```
