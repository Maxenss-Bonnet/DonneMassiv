from flask import Flask
import psycopg2

app = Flask(__name__)

@app.route("/")
def index():
    conn = psycopg2.connect(
        host="bd",  # ← le nom du service dans Docker
        database="livres",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
    cur.execute("SELECT titre FROM livres")
    livres = cur.fetchall()
    cur.close()
    conn.close()
    return "<br>".join(title for (title,) in livres)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
