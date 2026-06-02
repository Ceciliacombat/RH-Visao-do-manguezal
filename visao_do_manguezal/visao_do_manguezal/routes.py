from flask import Blueprint, render_template, request, redirect, url_for, session, send_from_directory, flash, make_response
from .models import Usuario, Funcionario, Documento
from .extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import os
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

main = Blueprint("main", __name__)

# 📁 CAMINHO DA PASTA DE UPLOAD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# 🔐 HELPERS
def usuario_logado():
    return "user_id" in session

def admin_logado():
    return "user_id" in session and session.get("tipo") == "admin"


# 🔐 LOGIN
@main.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        senha = request.form["senha"]

        user = Usuario.query.filter_by(username=username).first()

        if user and check_password_hash(user.senha, senha):

            session["user_id"] = user.id
            session["tipo"] = user.tipo

            return redirect(url_for("main.dashboard"))

        else:
            return render_template(
                "login.html",
                erro="Usuário ou senha inválidos"
            )

    return render_template("login.html")


# 📊 DASHBOARD
@main.route("/dashboard")
def dashboard():

    if not usuario_logado():
        return redirect(url_for("main.login"))

    funcionarios = Funcionario.query.all()

    hoje = datetime.now().date()

    exames_alerta = []
    ferias_alerta = []

    # =========================
    # ANALISAR FUNCIONÁRIOS
    # =========================

    for f in funcionarios:

        if not f.data_admissao:
            continue

        data_admissao = f.data_admissao

        # =========================
        # PRÓXIMO EXAME
        # =========================

        proximo_exame = data_admissao.replace(
            year=hoje.year
        )

        if proximo_exame < hoje:
            proximo_exame = proximo_exame.replace(
                year=hoje.year + 1
            )

        dias_exame = (proximo_exame - hoje).days

        if dias_exame <= 30:

            exames_alerta.append({
                "nome": f.nome,
                "data": proximo_exame,
                "dias": dias_exame
            })

        # =========================
        # FÉRIAS
        # =========================

        proxima_ferias = data_admissao.replace(
            year=data_admissao.year + 1
        )

        while proxima_ferias < hoje:
            proxima_ferias = proxima_ferias.replace(
                year=proxima_ferias.year + 1
            )

        dias_ferias = (proxima_ferias - hoje).days

        if dias_ferias <= 60:

            ferias_alerta.append({
                "nome": f.nome,
                "data": proxima_ferias,
                "dias": dias_ferias
            })

    # =========================
    # RESUMO
    # =========================

    total_funcionarios = len(funcionarios)

    total_exames = len(exames_alerta)
    total_ferias = len(ferias_alerta)

    total_alertas = total_exames + total_ferias

    return render_template(
        "dashboard.html",
        funcionarios=funcionarios,
        exames_alerta=exames_alerta,
        ferias_alerta=ferias_alerta,
        total_funcionarios=total_funcionarios,
        total_exames=total_exames,
        total_ferias=total_ferias,
        total_alertas=total_alertas,
        usuario=session.get("tipo"),
        nome_usuario=session.get("username")
    )


# 👥 FUNCIONÁRIOS
@main.route("/funcionarios")
def funcionarios():

    if not usuario_logado():
        return redirect(url_for("main.login"))

    lista = Funcionario.query.all()

    return render_template(
        "funcionarios.html",
        funcionarios=lista
    )


# 👤 PERFIL DO FUNCIONÁRIO
@main.route("/funcionario/<int:id>")
def perfil_funcionario(id):

    if not usuario_logado():
        return redirect(url_for("main.login"))

    funcionario = Funcionario.query.get_or_404(id)

    # =========================
    # DATA DE ADMISSÃO
    # =========================

    data_admissao = funcionario.data_admissao

    if isinstance(data_admissao, datetime):
        data_admissao = data_admissao.date()

    hoje = datetime.now().date()

    # =========================
    # CALCULAR FÉRIAS
    # =========================

    proxima_ferias = None
    limite_ferias = None

    if data_admissao:

        # próxima férias = 1 ano após admissão
        proxima_ferias = data_admissao.replace(
            year=data_admissao.year + 1
        )

        # limite = +2 anos após admissão
        limite_ferias = data_admissao.replace(
            year=data_admissao.year + 2
        )

    # =========================
    # CALCULAR EXAME
    # =========================

    proximo_exame = None

    if data_admissao:

        # exame anual
        proximo_exame = data_admissao.replace(
            year=hoje.year
        )

        # se já passou esse ano
        if proximo_exame < hoje:

            proximo_exame = proximo_exame.replace(
                year=hoje.year + 1
            )

    # =========================
    # DOCUMENTOS
    # =========================

    documentos = Documento.query.filter_by(
        funcionario_id=funcionario.id
    ).all()

    return render_template(
        "perfil_funcionario.html",
        f=funcionario,
        proxima_ferias=proxima_ferias,
        limite_ferias=limite_ferias,
        proximo_exame=proximo_exame,
        documentos=documentos
    )

# ✏️ EDITAR FUNCIONÁRIO
@main.route("/editar_funcionario/<int:id>", methods=["GET", "POST"])
def editar_funcionario(id):

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    funcionario = Funcionario.query.get_or_404(id)

    if request.method == "POST":

        funcionario.nome = request.form["nome"]
        funcionario.telefone = request.form["telefone"]
        funcionario.cpf = request.form["cpf"]
        funcionario.email = request.form["email"]

        funcionario.status = request.form["status"]

        funcionario.faltas = int(request.form["faltas"])

        data = request.form["data_entrada"]

        if data:
            funcionario.data_admissao = datetime.strptime(
                data,
                "%Y-%m-%d"
            ).date()

        # NOVO DOCUMENTO
        arquivos = request.files.getlist("documentos")

        for arquivo in arquivos:

            if arquivo and arquivo.filename != "":

                extensao = os.path.splitext(
                    arquivo.filename
                )[1]

                nome_unico = f"{uuid.uuid4().hex}{extensao}"

                os.makedirs(
                    UPLOAD_FOLDER,
                    exist_ok=True
                )

                caminho = os.path.join(
                    UPLOAD_FOLDER,
                    nome_unico
                )

                arquivo.save(caminho)

                doc = Documento(
                    nome_arquivo=nome_unico,
                    funcionario_id=funcionario.id
                )

                db.session.add(doc)

        db.session.commit()

        flash("Funcionário atualizado com sucesso.", "success")

        return redirect(
            url_for(
                "main.perfil_funcionario",
                id=funcionario.id
            )
        )

    return render_template(
        "editar_funcionario.html",
        f=funcionario
    )


# 🗑️ EXCLUIR FUNCIONÁRIO
@main.route("/excluir_funcionario/<int:id>", methods=["POST"])
def excluir_funcionario(id):

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    funcionario = Funcionario.query.get_or_404(id)

    # APAGAR DOCUMENTOS
    documentos = Documento.query.filter_by(
        funcionario_id=funcionario.id
    ).all()

    for doc in documentos:

        caminho = os.path.join(
            UPLOAD_FOLDER,
            doc.nome_arquivo
        )

        if os.path.exists(caminho):
            os.remove(caminho)

        db.session.delete(doc)

    db.session.delete(funcionario)
    db.session.commit()

    flash("Funcionário excluído com sucesso.", "success")

    return redirect(url_for("main.funcionarios"))


# 📄 NOVO FUNCIONÁRIO
@main.route("/novo_funcionario", methods=["GET", "POST"])
def novo_funcionario():

    

    if request.method == "POST":

        nome = request.form["nome"]
        data_entrada = request.form["data_entrada"]
        telefone = request.form["telefone"]
        cpf = request.form["cpf"]
        email = request.form["email"]

        status = request.form.get("status")
        faltas = request.form.get("faltas", 0)

        # DATA ADMISSÃO
        data_admissao = datetime.strptime(
            data_entrada,
            "%Y-%m-%d"
        ).date()

        # CRIAR FUNCIONÁRIO
        funcionario = Funcionario(
            nome=nome,
            data_admissao=data_admissao,

            telefone=telefone,
            cpf=cpf,
            email=email,

            status=status,
            faltas=int(faltas)
        )

        db.session.add(funcionario)
        db.session.commit()

        # 📂 DOCUMENTOS
        arquivos = request.files.getlist("documentos")

        for arquivo in arquivos:

            if arquivo and arquivo.filename != "":

                extensao = os.path.splitext(
                    arquivo.filename
                )[1]

                nome_unico = f"{uuid.uuid4().hex}{extensao}"

                os.makedirs(
                    UPLOAD_FOLDER,
                    exist_ok=True
                )

                caminho = os.path.join(
                    UPLOAD_FOLDER,
                    nome_unico
                )

                arquivo.save(caminho)

                novo_documento = Documento(
                    nome_arquivo=nome_unico,
                    funcionario_id=funcionario.id
                )

                db.session.add(novo_documento)

        db.session.commit()

        flash(
            "Funcionário cadastrado com sucesso.",
            "success"
        )

        return redirect(url_for("main.funcionarios"))

    return render_template("novo_funcionario.html")


# 👥 USUÁRIOS
@main.route("/usuarios")
def usuarios():

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    lista = Usuario.query.all()

    return render_template(
        "usuarios.html",
        usuarios=lista
    )


# ➕ NOVO USUÁRIO
@main.route("/novo_usuario", methods=["GET", "POST"])
def novo_usuario():

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        username = request.form["username"].strip()
        senha = request.form["senha"]
        tipo = request.form["tipo"]

        usuario_existente = Usuario.query.filter_by(
            username=username
        ).first()

        if usuario_existente:

            return render_template(
                "novo_usuario.html",
                erro="Esse usuário já existe."
            )

        novo = Usuario(
            username=username,
            senha=generate_password_hash(senha),
            tipo=tipo
        )

        db.session.add(novo)
        db.session.commit()

        flash("Usuário criado com sucesso.", "success")

        return redirect(url_for("main.usuarios"))

    return render_template("novo_usuario.html")


# 🔑 ALTERAR SENHA
@main.route("/alterar_senha/<int:id>", methods=["GET", "POST"])
def alterar_senha(id):

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    usuario = Usuario.query.get_or_404(id)

    if request.method == "POST":

        nova_senha = request.form["senha"]

        if not nova_senha:

            return render_template(
                "alterar_senha.html",
                usuario=usuario,
                erro="Digite uma nova senha."
            )

        usuario.senha = generate_password_hash(nova_senha)

        db.session.commit()

        flash("Senha alterada com sucesso.", "success")

        return redirect(url_for("main.usuarios"))

    return render_template(
        "alterar_senha.html",
        usuario=usuario
    )


# 🗑️ EXCLUIR USUÁRIO
@main.route("/excluir_usuario/<int:id>", methods=["POST"])
def excluir_usuario(id):

    if not admin_logado():
        return redirect(url_for("main.dashboard"))

    usuario = Usuario.query.get_or_404(id)

    if session.get("user_id") == usuario.id:

        flash(
            "Você não pode excluir o usuário logado.",
            "danger"
        )

        return redirect(url_for("main.usuarios"))

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuário excluído com sucesso.", "success")

    return redirect(url_for("main.usuarios"))


# 📂 ABRIR ARQUIVOS
@main.route("/arquivo/<nome>")
def arquivo(nome):

    if not usuario_logado():
        return redirect(url_for("main.login"))

    return send_from_directory(
        UPLOAD_FOLDER,
        nome
    )

# 🖨️ IMPRIMIR DOCUMENTO
@main.route("/imprimir_documento/<nome>")
def imprimir_documento(nome):

    if not usuario_logado():
        return redirect(url_for("main.login"))

    return render_template(
        "imprimir_documento.html",
        nome=nome
    )


# 🚪 LOGOUT
@main.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.login"))

# PÁGINA DOCUMENTOS
@main.route("/documentos")
def documentos():

    if not usuario_logado():
        return redirect(url_for("main.login"))

    funcionarios = Funcionario.query.order_by(
        Funcionario.nome.asc()
    ).all()

    return render_template(
        "documentos.html",
        funcionarios=funcionarios
    )


# GERAR DOCUMENTO
@main.route("/gerar_documento", methods=["POST"])
def gerar_documento():

    if not usuario_logado():
        return redirect(url_for("main.login"))

    nome = request.form.get("nome")
    cpf = request.form.get("cpf")
    tipo = request.form.get("tipo")

    funcionario = {
        "nome": nome,
        "cpf": cpf
    }

    cidade = "Maragogipinho - BA"

    data_atual = datetime.now().strftime(
        "%d/%m/%Y"
    )

    # TEMPLATE

    if tipo == "contrato":

        template = "documentos/contrato.html"

    elif tipo == "lgpd":

        template = "documentos/lgpd.html"

    elif tipo == "advertencia":

        template = "documentos/advertencia.html"

    else:

        return "Documento inválido"

    return render_template(
        template,
        funcionario=funcionario,
        cidade=cidade,
        data_atual=data_atual
    )