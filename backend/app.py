from flask import Flask, request, jsonify, render_template
import requests, os, json, pandas as pd, time
from datetime import datetime

app = Flask(__name__)

# 🔑 chave do Grok (defina no .env)
API_KEY = os.getenv("XAI_API_KEY")

# 🧠 Função para chamar o Grok (modelo IA)
def chamar_grok(perguntas):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": "\n".join(perguntas)}]
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
    except Exception as e:
        return f"Erro na requisição: {e}"

    if resp.status_code != 200:
        return f"Erro na API: {resp.status_code} - {resp.text}"

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return "Desculpe, houve um problema ao gerar a resposta."

# 🔹 Carrega perguntas iniciais
with open("perguntas.json", "r", encoding="utf-8") as f:
    perguntas_data = json.load(f)
perguntas = perguntas_data["perguntas_iniciais"]

usuarios = {}  # dados das conversas

# 🔹 Página inicial
@app.route("/")
def home():
    return render_template("index.html")


# 🔹 Função para validar respostas obrigatórias
def resposta_valida(resposta):
    # Exemplo simples: não vazia
    return bool(resposta.strip())


# 🔹 Função opcional para responder perguntas fora do fluxo
def responder_pergunta_geral(pergunta):
    return chamar_grok([pergunta])


# 🔹 Função para salvar histórico em Excel
def salvar_excel(user_id, historico):
    df = pd.DataFrame(historico)
    caminho_pasta = "conversas"
    os.makedirs(caminho_pasta, exist_ok=True)
    caminho_arquivo = os.path.join(caminho_pasta, f"conversa_{user_id}.xlsx")
    
    for tentativa in range(3):
        try:
            df.to_excel(caminho_arquivo, index=False)
            print(f"✅ Arquivo salvo em {caminho_arquivo}")
            break
        except PermissionError:
            print("⚠️ Arquivo está em uso. Feche o Excel e tente novamente...")
            time.sleep(2)
    return caminho_arquivo
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = data.get("userId", "default")
    mensagem = data.get("message", "").strip()

    if user_id not in usuarios:
        usuarios[user_id] = {
            "indice": 0,
            "respostas": [],
            "historico": [],
            "pergunta_atual": None
        }

    usuario = usuarios[user_id]

    # Salva a fala do usuário
    usuario["historico"].append({
        "quem": "Usuário",
        "mensagem": mensagem,
        "hora": datetime.now().strftime("%H:%M:%S")
    })

    # 🔹 Se houver pergunta obrigatória pendente
    # 🔹 Verifica se há pergunta obrigatória pendente
    if usuario["pergunta_atual"]:
        # Se o usuário enviou uma pergunta fora do roteiro
        if "?" in mensagem:
            resposta_grok = chamar_grok([mensagem])
            usuario["historico"].append({
                "quem": "Sally",
                "mensagem": resposta_grok,
                "hora": datetime.now().strftime("%H:%M:%S")
            })
            salvar_excel(user_id, usuario["historico"])
            # Retorna resposta do Grok e repete a pergunta obrigatória
            return jsonify({
                "response": f"{resposta_grok}\n\nPor favor, responda: {usuario['pergunta_atual']['texto']}"
            })

        # Se não for pergunta, valida a resposta
        if resposta_valida(mensagem):
            usuario["respostas"].append(mensagem)
            usuario["pergunta_atual"] = None
        else:
            # Repete a pergunta obrigatória
            return jsonify({
                "response": f"Por favor, responda: {usuario['pergunta_atual']['texto']}"
            })

        salvar_excel(user_id, usuario["historico"])
        return jsonify({"response": resposta_grok})

    # 🔹 Segue fluxo do roteiro de perguntas
    if usuario["indice"] < len(perguntas):
        proxima_pergunta = perguntas[usuario["indice"]]
        usuario["indice"] += 1

        # Se a próxima pergunta for obrigatória
        if proxima_pergunta.get("obrigatoria", False):
            usuario["pergunta_atual"] = proxima_pergunta

        usuario["historico"].append({
            "quem": "Sally",
            "mensagem": proxima_pergunta["texto"],
            "hora": datetime.now().strftime("%H:%M:%S")
        })
        salvar_excel(user_id, usuario["historico"])
        return jsonify({"response": proxima_pergunta["texto"]})

    # 🔹 Quando termina o roteiro
    resposta_final = (
        "Foi ótimo conversar com você! 😊 "
        "Se quiser continuar, clique no botão abaixo e fale com um humano pelo WhatsApp 👇"
        "\n\n👉 [Falar com a Sally no WhatsApp](https://api.whatsapp.com/send?phone=5583987168376)"
    )
    usuario["historico"].append({
        "quem": "Sally",
        "mensagem": resposta_final,
        "hora": datetime.now().strftime("%H:%M:%S")
    })
    salvar_excel(user_id, usuario["historico"])
    return jsonify({"response": resposta_final})
if __name__ == "__main__":
    app.run(debug=True)
