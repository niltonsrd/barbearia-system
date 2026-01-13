from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth = Blueprint("auth", __name__)


# -----------------------------
# LOGIN CLIENTE
# -----------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        db = get_db()
        cliente = db.execute(
            "SELECT * FROM clientes WHERE email = ?", (email,)
        ).fetchone()

        if cliente and check_password_hash(cliente["senha_hash"], senha):
            session.clear()
            session["cliente_id"] = cliente["id"]
            session["cliente_nome"] = cliente["nome"]
            session["role"] = cliente["role"]

            # 🔥 FLAG ADMIN
            if cliente["role"] == "admin":
                session["is_admin"] = True

            return redirect(url_for("index"))

        flash("Email ou senha inválidos")

    return render_template("public/login.html")


# -----------------------------
# CADASTRO CLIENTE
# -----------------------------
@auth.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        telefone = request.form["telefone"]
        senha = request.form["senha"]

        senha_hash = generate_password_hash(senha)
        db = get_db()

        try:
            db.execute(
                "INSERT INTO clientes (nome, email, telefone, senha_hash) VALUES (?, ?, ?, ?)",
                (nome, email, telefone, senha_hash),
            )
            db.commit()
            return redirect(url_for("auth.login"))
        except:
            flash("Email já cadastrado")

    return render_template("public/cadastro.html")


# -----------------------------
# LOGOUT CLIENTE
# -----------------------------
@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
