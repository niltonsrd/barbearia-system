from flask import Flask, flash, render_template, session, redirect, url_for, request
from db import close_db, get_db
from auth import auth
from admin import admin
from datetime import date, timedelta
import calendar


app = Flask(__name__)
app.config["SECRET_KEY"] = "barbearia-secret-key"

# Blueprints
app.register_blueprint(auth)
app.register_blueprint(admin)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def index():
    return render_template("public/index.html")


# -----------------------------
# PERFIL DO CLIENTE
# -----------------------------
@app.route("/perfil")
def perfil():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    cliente = db.execute(
        """
        SELECT nome, email
        FROM clientes
        WHERE id = ?
        """,
        (session["cliente_id"],),
    ).fetchone()

    return render_template(
        "public/perfil.html",
        cliente=cliente,
    )


# -----------------------------
# AGENDAMENTO (CLIENTE)
# -----------------------------
@app.route("/agendar/servico", methods=["GET", "POST"])
def agendar_servico():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    if request.method == "POST":
        servico_id = request.form["servico_id"]
        session["agendamento"] = {"servico_id": servico_id}
        return redirect(url_for("agendar_barbeiro"))

    servicos = db.execute(
        """
        SELECT id, nome, preco, descricao, imagem
        FROM servicos
        WHERE ativo = 1
        ORDER BY nome
    """
    ).fetchall()

    return render_template(
        "public/agendar_servico.html", servicos=servicos, voltar_url=url_for("index")
    )


@app.route("/agendar/barbeiro", methods=["GET", "POST"])
def agendar_barbeiro():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    if request.method == "POST":
        barbeiro_id = request.form.get("barbeiro_id")

        # 🔒 proteção contra envio vazio
        if not barbeiro_id:
            return redirect(url_for("agendar_barbeiro"))

        if "agendamento" not in session:
            session["agendamento"] = {}

        session["agendamento"]["barbeiro_id"] = barbeiro_id
        session.modified = True

        return redirect(url_for("agendar_data"))

    barbeiros = db.execute(
        "SELECT id, nome, foto FROM barbeiros WHERE ativo = 1 ORDER BY nome"
    ).fetchall()

    return render_template(
        "public/agendar_barbeiro.html",
        barbeiros=barbeiros,
        voltar_url=url_for("agendar_servico"),
    )


from datetime import datetime


@app.route("/agendar/data", methods=["GET", "POST"])
def agendar_data():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    if "agendamento" not in session or "barbeiro_id" not in session["agendamento"]:
        return redirect(url_for("agendar_servico"))

    db = get_db()

    barbeiro_id = session["agendamento"]["barbeiro_id"]

    # dias da semana que o barbeiro atende
    dias = db.execute(
        """
        SELECT DISTINCT dia_semana
        FROM horarios
        WHERE barbeiro_id = ? AND ativo = 1
        ORDER BY dia_semana
        """,
        (barbeiro_id,),
    ).fetchall()

    dias_semana = [d["dia_semana"] for d in dias]

    if request.method == "POST":
        data = request.form.get("data")
        hora = request.form.get("hora")

        if not data or not hora:
            return redirect(url_for("agendar_data"))

        session["agendamento"]["data"] = data
        session["agendamento"]["hora"] = hora
        session.modified = True

        return redirect(url_for("agendar_revisao"))

    return render_template(
        "public/agendar_data.html",
        barbeiro_id=barbeiro_id,
        dias=dias_semana,
        voltar_url=url_for("agendar_barbeiro"),
    )


@app.route("/agendar/revisao", methods=["GET", "POST"])
def agendar_revisao():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    agendamento = session.get("agendamento")

    # blindagem total
    if not agendamento or not all(
        k in agendamento for k in ("servico_id", "barbeiro_id", "data", "hora")
    ):
        return redirect(url_for("agendar_servico"))

    db = get_db()

    servico = db.execute(
        "SELECT nome, preco FROM servicos WHERE id = ?",
        (agendamento["servico_id"],),
    ).fetchone()

    barbeiro = db.execute(
        "SELECT nome FROM barbeiros WHERE id = ?",
        (agendamento["barbeiro_id"],),
    ).fetchone()

    data_iso = agendamento["data"]

    data_formatada = datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    hora = agendamento["hora"]

    if request.method == "POST":
        db.execute(
            """
            INSERT INTO agendamentos
            (cliente_id, barbeiro_id, servico_id, data, hora, status)
            VALUES (?, ?, ?, ?, ?, 'pendente')
            """,
            (
                session["cliente_id"],
                agendamento["barbeiro_id"],
                agendamento["servico_id"],
                data_iso,
                hora,
            ),
        )
        db.commit()

        session["agendamento_sucesso"] = {
            "servico": servico["nome"],
            "preco": servico["preco"],
            "barbeiro": barbeiro["nome"],
            "data": data_formatada,
            "hora": hora,
        }

        session.pop("agendamento", None)

        return redirect(url_for("agendar_sucesso"))

    return render_template(
        "public/agendar_revisao.html",
        servico=servico,
        barbeiro=barbeiro,
        data=data_formatada,
        hora=hora,
        voltar_url=url_for("agendar_data"),
    )


@app.route("/agendar/sucesso")
def agendar_sucesso():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    dados = session.get("agendamento_sucesso")

    if not dados:
        return redirect(url_for("meus_agendamentos"))

    return render_template("public/agendar_sucesso.html", **dados)


# -----------------------------
# MEUS AGENDAMENTOS
# -----------------------------
@app.route("/meus-agendamentos")
def meus_agendamentos():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    agendamentos = db.execute(
        """
        SELECT 
            a.id,
            a.data,
            a.hora,
            a.status,
            s.nome AS servico,
            b.nome AS barbeiro
        FROM agendamentos a
        JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN barbeiros b ON b.id = a.barbeiro_id
        WHERE a.cliente_id = ?
        ORDER BY a.data DESC, a.hora DESC
    """,
        (session["cliente_id"],),
    ).fetchall()

    return render_template("public/meus_agendamentos.html", agendamentos=agendamentos)


@app.route("/admin/agendamentos/confirmar/<int:id>")
def confirmar_agendamento(id):
    db = get_db()
    db.execute("UPDATE agendamentos SET status = 'confirmado' WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("admin.agendamentos"))


# -----------------------------
# CANCELAR AGENDAMENTO (CLIENTE)
# -----------------------------
@app.route("/cancelar-agendamento/<int:id>")
def cancelar_agendamento(id):
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()

    agendamento = db.execute(
        """
        SELECT id, status FROM agendamentos
        WHERE id = ? AND cliente_id = ?
        """,
        (id, session["cliente_id"]),
    ).fetchone()

    if not agendamento:
        return redirect(url_for("meus_agendamentos"))

    # bloqueia cancelamento indevido
    if agendamento["status"] in ("cancelado", "concluido"):
        return redirect(
            url_for(
                "meus_agendamentos",
                toast="error",
                msg="Este agendamento não pode ser cancelado",
            )
        )

    db.execute(
        "UPDATE agendamentos SET status = 'cancelado' WHERE id = ?",
        (id,),
    )
    db.commit()

    return redirect(
        url_for("meus_agendamentos", toast="success", msg="Agendamento cancelado")
    )


from datetime import datetime


@app.route("/api/horarios")
def api_horarios():
    if "cliente_id" not in session:
        return []

    agendamento = session.get("agendamento")
    if not agendamento or "barbeiro_id" not in agendamento:
        return []

    barbeiro_id = agendamento["barbeiro_id"]
    data = request.args.get("data")

    if not data:
        return []

    db = get_db()

    # dia da semana (0=domingo)
    from datetime import datetime

    dia_semana = datetime.strptime(data, "%Y-%m-%d").weekday()
    dia_semana = (dia_semana + 1) % 7  # ajuste para padrão SQLite (domingo=0)

    # horários cadastrados do barbeiro
    horarios = db.execute(
        """
        SELECT hora
        FROM horarios
        WHERE barbeiro_id = ?
          AND dia_semana = ?
          AND ativo = 1
        ORDER BY hora
        """,
        (barbeiro_id, dia_semana),
    ).fetchall()

    # horários já ocupados
    ocupados = db.execute(
        """
        SELECT hora
        FROM agendamentos
        WHERE barbeiro_id = ?
          AND data = ?
          AND status IN ('pendente', 'confirmado')
        """,
        (barbeiro_id, data),
    ).fetchall()

    horas_ocupadas = {o["hora"] for o in ocupados}

    resposta = []
    for h in horarios:
        resposta.append(
            {"hora": h["hora"], "disponivel": h["hora"] not in horas_ocupadas}
        )

    return resposta


@app.route("/api/agenda/<int:barbeiro_id>")
def api_agenda(barbeiro_id):
    if "cliente_id" not in session:
        return {"error": "unauthorized"}, 401

    dias = int(request.args.get("dias", 7))
    hoje = date.today()
    fim = hoje + timedelta(days=dias)

    db = get_db()

    # horários fixos do barbeiro
    horarios_base = db.execute(
        """
        SELECT dia_semana, hora
        FROM horarios
        WHERE barbeiro_id = ?
          AND ativo = 1
    """,
        (barbeiro_id,),
    ).fetchall()

    if not horarios_base:
        return []

    agenda = []

    for i in range(dias):
        data_atual = hoje + timedelta(days=i)
        dia_semana = (data_atual.weekday() + 1) % 7  # 0=Segunda

        horarios_dia = [
            h["hora"] for h in horarios_base if h["dia_semana"] == dia_semana
        ]

        if not horarios_dia:
            continue

        slots = []

        for hora in horarios_dia:
            ocupado = db.execute(
                """
                SELECT 1 FROM agendamentos
                WHERE barbeiro_id = ?
                  AND data = ?
                  AND hora = ?
                  AND status IN ('pendente', 'confirmado')
            """,
                (barbeiro_id, data_atual.isoformat(), hora),
            ).fetchone()

            slots.append({"hora": hora, "disponivel": not bool(ocupado)})

        DIAS_PT = [
            "Segunda",
            "Terça",
            "Quarta",
            "Quinta",
            "Sexta",
            "Sábado",
            "Domingo",
        ]

        agenda.append(
            {
                "data": data_atual.isoformat(),
                "dia": DIAS_PT[data_atual.weekday()],
                "slots": slots,
            }
        )

    return agenda

from werkzeug.security import check_password_hash, generate_password_hash


@app.route("/alterar-senha", methods=["GET", "POST"])
def alterar_senha():
    if "cliente_id" not in session:
        return redirect(url_for("auth.login"))

    # 👉 Se alguém tentar acessar via GET, apenas volta para o perfil
    if request.method == "GET":
        return redirect(url_for("perfil"))

    # 👉 POST (alteração de senha)
    senha_atual = request.form.get("senha_atual")
    nova_senha = request.form.get("nova_senha")
    confirmar_senha = request.form.get("confirmar_senha")

    if not senha_atual or not nova_senha or not confirmar_senha:
        flash("Preencha todos os campos", "error")
        return redirect(url_for("perfil"))

    if nova_senha != confirmar_senha:
        flash("As senhas não coincidem", "error")
        return redirect(url_for("perfil"))

    db = get_db()

    usuario = db.execute(
        "SELECT senha_hash FROM clientes WHERE id = ?", (session["cliente_id"],)
    ).fetchone()

    if not usuario or not check_password_hash(usuario["senha_hash"], senha_atual):
        flash("Senha atual incorreta", "error")
        return redirect(url_for("perfil"))

    nova_hash = generate_password_hash(nova_senha)

    db.execute(
        "UPDATE clientes SET senha_hash = ? WHERE id = ?",
        (nova_hash, session["cliente_id"]),
    )
    db.commit()

    flash("Senha alterada com sucesso", "success")
    return redirect(url_for("perfil"))


# -----------------------------
# FECHAR DB
# -----------------------------
@app.teardown_appcontext
def teardown_db(exception):
    close_db()


@app.route("/debug-agendar-data")
def debug_agendar_data():
    return "ROTA AGENDAR DATA OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
