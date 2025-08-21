from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import pandas as pd
import os
from datetime import datetime

# ==================== CRIAR PASTAS NECESSÁRIAS ====================
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ==================== CONFIGURAÇÃO ====================
DB_NAME = "data/pedidos.db"

app = Flask(__name__)
app.secret_key = "uma_chave_super_secreta_aqui"

# ==================== USUÁRIOS ====================
USUARIOS = {
    "loja2": "loja22",
    "loja3": "loja33",
    "loja4": "loja44",
    "loja5": "loja55",
    "loja6": "loja66",
    "loja7": "loja77",
    "logistica": "log123"
}

# ==================== LOGIN ====================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        senha = request.form.get("password")
        if user in USUARIOS and USUARIOS[user] == senha:
            session["user"] = user
            if user == "logistica":
                return redirect(url_for("logistica"))
            else:
                return redirect(url_for("painel_requisitante"))
        else:
            return render_template("login.html", erro="Usuário ou senha incorretos")
    else:
        if "user" in session:
            if session["user"] == "logistica":
                return redirect(url_for("logistica"))
            else:
                return redirect(url_for("painel_requisitante"))
        return render_template("login.html")

# ==================== LOGOUT ====================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ==================== PAINEL REQUISITANTE ====================
@app.route("/painel_requisitante")
def painel_requisitante():
    if "user" not in session or session["user"] == "logistica":
        return redirect(url_for("login"))

    usuario = session["user"]
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM pedidos WHERE loja = ?", (usuario,))
        pedidos = c.fetchall()

    return render_template("painel_requisitante.html", pedidos=pedidos, usuario=usuario)

# ==================== NOVO PEDIDO ====================
@app.route("/novo_pedido", methods=["GET", "POST"])
def novo_pedido():
    if "user" not in session or session["user"] == "logistica":
        return redirect(url_for("login"))

    if request.method == "POST":
        vendedor = request.form.get("vendedor")
        loja = session["user"]
        cliente = request.form.get("cliente")
        endereco = request.form.get("endereco")
        numero_pedido = request.form.get("numero_pedido")
        numero_requisicao = request.form.get("numero_requisicao")
        volume_aprox = request.form.get("volume_aprox")
        periodo = request.form.get("periodo")
        data_entrega = request.form.get("data_entrega")
        arquivo = request.files.get("arquivo")
        obs_requisitante = request.form.get("obs_requisitante")

        arquivo_nome = None
        if arquivo and arquivo.filename != "":
            arquivo_nome = f"uploads/{arquivo.filename}"
            arquivo.save(f"static/{arquivo_nome}")

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO pedidos (
                    vendedor, loja, cliente, endereco,
                    numero_pedido, numero_requisicao, volume_aprox,
                    periodo, data_entrega, status, motorista,
                    caminhao, arquivo, obs_requisitante, obs_logistica,
                    data_criacao
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                vendedor, loja, cliente, endereco,
                numero_pedido, numero_requisicao, volume_aprox,
                periodo, data_entrega, "Pendente", "", "",
                arquivo_nome, obs_requisitante, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
        return redirect(url_for("painel_requisitante"))

    return render_template("novo_pedido.html")

# ==================== LOGISTICA ====================
@app.route("/logistica", methods=["GET", "POST"])
def logistica():
    if "user" not in session or session["user"] != "logistica":
        return redirect(url_for("login"))

    motoristas = ["Eraldo", "Marcílio", "Marquinho", "Nathan", "Humberto", "Marcos", "Claudinei"]
    caminhoes = [
        "HR HYUNDAI QAJ-3439 1600KG", "HR HYUNDAI QAR-7133 1600KG", "HR HYUNDAI QAX2J96 1600KG",
        "CARGO TOCO 11000KG FORD HTA-9094", "CARGO 15000KG FORD NRJ-6820", "CARGO 18000KG FORD TRUCK NRU-9420",
        "F-4000 FORD HSF-6714", "F-400 FORD HTI-3098"
    ]
    status_list = ["Pendente", "Em Rota", "Entregue", "Atrasado", "Correção", "Cancelado"]

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if request.method == "POST":
            pedido_id = request.form.get("pedido_id")
            status = request.form.get("status")
            obs_logistica = request.form.get("obs_logistica", "")
            motorista = request.form.get("motorista", "")
            caminhao = request.form.get("caminhao", "")

            c.execute("""
                UPDATE pedidos
                SET status = ?, obs_logistica = ?, motorista = ?, caminhao = ?
                WHERE id = ?
            """, (status, obs_logistica, motorista, caminhao, pedido_id))
            conn.commit()

        # filtros GET
        filtros = []
        parametros = []
        loja_f = request.args.get("loja")
        if loja_f:
            filtros.append("loja=?")
            parametros.append(loja_f)
        status_f = request.args.get("status")
        if status_f:
            filtros.append("status=?")
            parametros.append(status_f)
        cliente_f = request.args.get("cliente")
        if cliente_f:
            filtros.append("cliente LIKE ?")
            parametros.append(f"%{cliente_f}%")
        data_f = request.args.get("data")
        if data_f:
            filtros.append("data_entrega=?")
            parametros.append(data_f)

        query = "SELECT * FROM pedidos"
        if filtros:
            query += " WHERE " + " AND ".join(filtros)
        c.execute(query, tuple(parametros))
        pedidos = c.fetchall()

    return render_template("painel_logistica.html", pedidos=pedidos, motoristas=motoristas, caminhoes=caminhoes, status_list=status_list)

# ==================== EXPORTAR EXCEL ====================
@app.route("/exportar")
def exportar():
    if "user" not in session or session["user"] != "logistica":
        return redirect(url_for("login"))

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM pedidos", conn)

    file_path = "pedidos.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

# ==================== RODAR APP LOCAL ====================
if __name__ == "__main__":
    app.run(debug=True)
