import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# CLIENTES
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    telefone TEXT,
    senha_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# BARBEIROS
cursor.execute("""
CREATE TABLE IF NOT EXISTS barbeiros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    ativo INTEGER DEFAULT 1
)
""")

# SERVIÇOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    duracao_min INTEGER NOT NULL,
    preco REAL NOT NULL,
    ativo INTEGER DEFAULT 1
)
""")

# AGENDAMENTOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    barbeiro_id INTEGER,
    servico_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    hora TEXT NOT NULL,
    status TEXT DEFAULT 'pendente',
    observacao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (barbeiro_id) REFERENCES barbeiros(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id)
)
""")

conn.commit()
conn.close()

print("Banco de dados criado com sucesso!")
