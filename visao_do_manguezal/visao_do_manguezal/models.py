from .extensions import db


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)


class Funcionario(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(100))
    cpf = db.Column(db.String(14))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))

    data_admissao = db.Column(db.Date)

    status = db.Column(db.String(20))
    faltas = db.Column(db.Integer, default=0)

    documentos = db.relationship(
        "Documento",
        backref="funcionario",
        lazy=True,
        cascade="all, delete-orphan"
    )

class Documento(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    nome_arquivo = db.Column(
        db.String(200),
        nullable=False
    )

    funcionario_id = db.Column(
        db.Integer,
        db.ForeignKey("funcionario.id"),
        nullable=False
    )