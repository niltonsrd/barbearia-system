import os
from werkzeug.utils import secure_filename
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    g,
    current_app,
)
from db import get_db
from functools import wraps

admin = Blueprint("admin", __name__, url_prefix="/admin")
UPLOAD_FOLDER = "static/uploads/barbeiros"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def login_required_admin():
    return session.get("is_admin") is True


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "cliente_id" not in session or session.get("role") != "admin":
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated


from uuid import uuid4
import os
from PIL import Image


def salvar_imagem(file, pasta):
    if not file or not file.filename:
        return None

    ext = file.filename.rsplit(".", 1)[1].lower()

    upload_dir = os.path.join(current_app.root_path, "static", "uploads", pasta)
    os.makedirs(upload_dir, exist_ok=True)

    nome_arquivo = f"{uuid4().hex}.jpg"
    caminho_final = os.path.join(upload_dir, nome_arquivo)

    # Converte WEBP → JPG
    img = Image.open(file)
    img = img.convert("RGB")
    img.save(caminho_final, "JPEG", quality=85)

    print("✅ Imagem salva em:", caminho_final)

    return nome_arquivo


@admin.route("/")
@admin_required
def dashboard():
    db = get_db()
    print("📦 DB EM USO:", db.execute("PRAGMA database_list").fetchall())
    print("🧾 SERVICOS:", db.execute("SELECT id, nome, ativo FROM servicos").fetchall())


    def count_safe(query):
        try:
            return db.execute(query).fetchone()[0]
        except Exception:
            return 0

    total_clientes = count_safe("SELECT COUNT(*) FROM clientes")
    total_agendamentos = count_safe("SELECT COUNT(*) FROM agendamentos")
    total_pendentes = count_safe(
        "SELECT COUNT(*) FROM agendamentos WHERE status = 'pendente'"
    )
    total_servicos = count_safe("SELECT COUNT(*) FROM servicos WHERE ativo = 1")

    return render_template(
        "admin/dashboard.html",
        total_clientes=total_clientes,
        total_agendamentos=total_agendamentos,
        total_pendentes=total_pendentes,
        total_servicos=total_servicos,
        agendamentos_hoje=None,
    )


# -----------------------------
# SERVIÇOS (COM IMAGEM)
# -----------------------------
@admin.route("/servicos", methods=["GET", "POST"])
@admin_required
def servicos():
    db = get_db()

    if request.method == "POST":
        print("🔥 POST /servicos recebido")
        print("📦 request.form:", request.form)
        print("📁 request.files:", request.files)

        nome = request.form.get("nome")
        descricao = request.form.get("descricao")
        preco = request.form.get("preco")
        duracao = request.form.get("duracao")

        imagem_file = request.files.get("imagem")
        print("📸 imagem_file:", imagem_file)

        imagem_nome = salvar_imagem(imagem_file, "servicos")

        db.execute(
            """
            INSERT INTO servicos
            (nome, descricao, preco, duracao_min, imagem, ativo)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (nome, descricao, preco, duracao, imagem_nome),
        )
        db.commit()

        return redirect(url_for("admin.servicos"))

    # 👇👇👇 ISSO É O QUE ESTAVA FALTANDO 👇👇👇
    servicos = db.execute("SELECT * FROM servicos ORDER BY nome").fetchall()

    return render_template("admin/servicos.html", servicos=servicos)


@admin.route("/servicos/excluir/<int:id>")
@admin_required
def excluir_servico(id):
    db = get_db()

    servico = db.execute("SELECT imagem FROM servicos WHERE id = ?", (id,)).fetchone()

    if servico:
        if servico["imagem"]:
            caminho = os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                "servicos",
                servico["imagem"],
            )
            if os.path.exists(caminho):
                os.remove(caminho)

        db.execute("DELETE FROM servicos WHERE id = ?", (id,))
        db.commit()

    return redirect(url_for("admin.servicos"))


@admin.route("/servicos/toggle/<int:id>")
def toggle_servico(id):

    db = get_db()

    servico = db.execute("SELECT ativo FROM servicos WHERE id = ?", (id,)).fetchone()

    if servico:
        novo_status = 0 if servico["ativo"] == 1 else 1
        db.execute(
            "UPDATE servicos SET ativo = ? WHERE id = ?",
            (novo_status, id),
        )
        db.commit()

    return redirect(url_for("admin.servicos"))


# -----------------------------
# BARBEIROS
# -----------------------------
@admin.route("/barbeiros", methods=["GET", "POST"])
@admin_required
def barbeiros():

    db = get_db()

    if request.method == "POST":
        nome = request.form["nome"]
        bio = request.form.get("bio")

        foto_file = request.files.get("foto")
        foto_nome = salvar_imagem(foto_file, "barbeiros")
        db.execute(
            """
            INSERT INTO barbeiros (nome, foto, bio, ativo)
            VALUES (?, ?, ?, 1)
            """,
            (nome, foto_nome, bio),
        )
        db.commit()

        return redirect(url_for("admin.barbeiros"))

    barbeiros = db.execute("SELECT * FROM barbeiros ORDER BY nome").fetchall()

    return render_template("admin/barbeiros.html", barbeiros=barbeiros)


@admin.route("/barbeiros/toggle/<int:id>")
@admin_required
def toggle_barbeiro(id):

    db = get_db()
    b = db.execute("SELECT ativo FROM barbeiros WHERE id = ?", (id,)).fetchone()

    if b:
        db.execute(
            "UPDATE barbeiros SET ativo = ? WHERE id = ?",
            (0 if b["ativo"] else 1, id),
        )
        db.commit()

    return redirect(url_for("admin.barbeiros"))


# -----------------------------
# AGENDAMENTOS
# -----------------------------
@admin.route("/agendamentos")
@admin_required
def agendamentos():
    db = get_db()

    # Hoje
    hoje = db.execute(
        """
        SELECT a.id, a.data, a.hora, a.status,
               c.nome AS cliente,
               s.nome AS servico,
               b.nome AS barbeiro
        FROM agendamentos a
        JOIN clientes c ON c.id = a.cliente_id
        JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN barbeiros b ON b.id = a.barbeiro_id
        WHERE a.data = DATE('now')
          AND a.status IN ('pendente','confirmado')
        ORDER BY a.hora
    """
    ).fetchall()

    # Pendentes (futuros)
    pendentes = db.execute(
        """
        SELECT a.id, a.data, a.hora, a.status,
               c.nome AS cliente,
               s.nome AS servico,
               b.nome AS barbeiro
        FROM agendamentos a
        JOIN clientes c ON c.id = a.cliente_id
        JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN barbeiros b ON b.id = a.barbeiro_id
        WHERE a.status = 'pendente'
          AND a.data >= DATE('now')
        ORDER BY a.data, a.hora
    """
    ).fetchall()

    # Histórico
    historico = db.execute(
        """
        SELECT a.id, a.data, a.hora, a.status,
               c.nome AS cliente,
               s.nome AS servico,
               b.nome AS barbeiro
        FROM agendamentos a
        JOIN clientes c ON c.id = a.cliente_id
        JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN barbeiros b ON b.id = a.barbeiro_id
        WHERE a.status IN ('cancelado','finalizado')
           OR a.data < DATE('now')
        ORDER BY a.data DESC, a.hora DESC
    """
    ).fetchall()

    return render_template(
        "admin/agendamentos.html", hoje=hoje, pendentes=pendentes, historico=historico
    )


@admin.route("/agendamentos/status/<int:id>/<status>")
@admin_required
def alterar_status_agendamento(id, status):

    if status not in ["pendente", "confirmado", "cancelado", "finalizado"]:
        return redirect(url_for("admin.agendamentos"))

    db = get_db()
    db.execute(
        "UPDATE agendamentos SET status = ? WHERE id = ?",
        (status, id),
    )
    db.commit()

    return redirect(url_for("admin.agendamentos"))


# -----------------------------
# HORÁRIOS (ADMIN)
# -----------------------------
@admin.route("/horarios")
@admin_required
def horarios():
    db = get_db()

    dia_filtro = request.args.get("dia")

    query = """
        SELECT h.id, h.dia_semana, h.hora, h.ativo,
               b.nome AS barbeiro
        FROM horarios h
        JOIN barbeiros b ON b.id = h.barbeiro_id
    """

    params = []

    if dia_filtro is not None and dia_filtro != "":
        query += " WHERE h.dia_semana = ?"
        params.append(dia_filtro)

    query += " ORDER BY h.dia_semana, h.hora"

    horarios = db.execute(query, params).fetchall()

    barbeiros = db.execute(
        "SELECT id, nome FROM barbeiros WHERE ativo = 1 ORDER BY nome"
    ).fetchall()

    return render_template(
        "admin/horarios.html",
        horarios=horarios,
        barbeiros=barbeiros,
        dia_filtro=dia_filtro,
    )


@admin.route("/horarios/gerar", methods=["POST"])
@admin_required
def gerar_horarios():
    from datetime import datetime, timedelta

    barbeiro_id = request.form["barbeiro_id"]
    dia_semana = request.form["dia_semana"]
    hora_inicio = request.form["hora_inicio"]
    hora_fim = request.form["hora_fim"]
    duracao = int(request.form["duracao"])

    db = get_db()

    inicio = datetime.strptime(hora_inicio, "%H:%M")
    fim = datetime.strptime(hora_fim, "%H:%M")

    atual = inicio
    while atual <= fim:
        hora = atual.strftime("%H:%M")

        existe = db.execute(
            """
            SELECT 1 FROM horarios
            WHERE barbeiro_id = ?
              AND dia_semana = ?
              AND hora = ?
            """,
            (barbeiro_id, dia_semana, hora),
        ).fetchone()

        if not existe:
            db.execute(
                """
                INSERT INTO horarios (barbeiro_id, dia_semana, hora, ativo)
                VALUES (?, ?, ?, 1)
                """,
                (barbeiro_id, dia_semana, hora),
            )

        atual += timedelta(minutes=duracao)

    db.commit()
    return redirect(url_for("admin.horarios"))


@admin.route("/horarios/excluir/<int:id>")
@admin_required
def excluir_horario(id):

    db = get_db()
    db.execute("DELETE FROM horarios WHERE id = ?", (id,))
    db.commit()

    return redirect(request.referrer or url_for("admin.horarios"))


@admin.route("/horarios/add", methods=["POST"])
@admin_required
def add_horario():
    barbeiro_id = request.form["barbeiro_id"]
    dia_semana = request.form["dia_semana"]
    hora = request.form["hora"]

    db = get_db()

    existe = db.execute(
        """
        SELECT 1 FROM horarios
        WHERE barbeiro_id = ?
          AND dia_semana = ?
          AND hora = ?
        """,
        (barbeiro_id, dia_semana, hora),
    ).fetchone()

    if not existe:
        db.execute(
            """
            INSERT INTO horarios (barbeiro_id, dia_semana, hora, ativo)
            VALUES (?, ?, ?, 1)
            """,
            (barbeiro_id, dia_semana, hora),
        )
        db.commit()

    return redirect(url_for("admin.horarios", barbeiro_id=barbeiro_id))


@admin.route("/horarios/status/<int:id>/<acao>")
@admin_required
def status_horario(id, acao):
    db = get_db()

    novo_status = 1 if acao == "ativar" else 0

    db.execute(
        "UPDATE horarios SET ativo = ? WHERE id = ?",
        (novo_status, id),
    )
    db.commit()

    return redirect(url_for("admin.horarios"))
