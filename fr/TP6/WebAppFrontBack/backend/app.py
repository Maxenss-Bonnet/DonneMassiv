# app.py
from flask import Flask, jsonify
from flask_cors import CORS  # Importer CORS

# Créer une instance de Flask
app = Flask(__name__)

# Appliquer CORS à l'application
CORS(app, origins=["http://localhost:3000"])

# Définir une route
@app.route("/message")
def message():
    return jsonify({"text": "Bonjour!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
