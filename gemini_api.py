from flask import Flask, request, jsonify, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY") # To try out this code, get your API Key from google 

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

app = Flask(__name__)

limiter = Limiter(get_remote_address, app=app, default_limits=["5 per minute"])

@app.route("/analize-data", methods=["POST"])
#@limiter.limit("5 per minute") # Adjust in case you want this route specifically to have a different call rate per minute
def analize_data():
    try:
        payload = request.get_json()
        if not isinstance(payload, dict):
            raise ValueError("Precisa ser um JSON válido")
    except Exception as e:
        return jsonify({"error": "Payload inválido", "details": str(e)}), 400

    json_str = json.dumps(payload, indent=2)
    num_linhas = len(json_str.splitlines())

    if num_linhas > 70:
        json_str = '\n'.join(json_str.splitlines()[:50])

        print(f"Enviando seguinte json ao prompt {json_str}")

    prompt = f"""
    Você recebeu os seguintes dados de um webhook:

    {json_str}

    Sua tarefa é gerar um resumo objetivo explicando o que está presente nos dados recebidos. Identifique padrões, informações importantes ou alertas que possam ser úteis para o gestor.

    ⚠️ MUITO IMPORTANTE:

    Se os dados recebidos não forem um conjunto estruturado ou não representarem um compilado coerente de informações (ex: apenas uma frase solta, insultos, frases desconexas, ou algo fora de contexto), **responda apenas com a frase**:

    \"Não foi possível analisar os dados recebidos, pois não são compatíveis com um conjunto analítico estruturado.\"

    Não tente interpretar insultos, frases únicas ou dados aleatórios. Apenas valide se os dados parecem **coerentes e estruturados**.
    """


    try:
        response = model.generate_content(prompt)
        ai_result = response.text
    except Exception as e:
        return jsonify({"error": "Erro ao processar com IA", "details": str(e)}), 500
    
    log_entry = {
        "entrada": payload,
        "resumo_gerado": ai_result
    }
    print("[LOG] Entrada recebida:\n", json.dumps(log_entry, indent=2))

    return jsonify(log_entry)

@app.route("/generate-data", methods=["POST"])
def generate_data():
    prompt = f"""
    Gere um array de dados no formato JSON puro, sem usar aspas triplas, markdown ou ```json.

    A estrutura deve ser um array de objetos com o mesmo formato.

    Limite o conteúdo a no máximo 50 linhas totais.

    Use criatividade no conteúdo, mas mantenha uma estrutura consistente. Exemplo de temas: avaliações de alienígenas em pizzarias, fichas técnicas de dragões, dados de eventos em galáxias distantes, mas não use esses exemplos, seja criativo.
    """

    try:
        response = model.generate_content(prompt)
        ai_result = response.text
    except Exception as e:
        return jsonify({"error": "Erro ao processar com IA", "details": str(e)}), 500

    try:
        dados_json = json.loads(ai_result)  # Tenta transformar a string em objeto
    except json.JSONDecodeError:
        dados_json = ai_result  # Deixa como string, caso não seja possível

    return jsonify({"json_para_envio": dados_json})


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))  # Railway define PORT via env
    app.run(host='0.0.0.0', port=port)
