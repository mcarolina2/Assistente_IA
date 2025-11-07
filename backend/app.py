from flask import Flask, request, jsonify, render_template
import requests, os, json, pandas as pd, time
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from guardrails import Guard



app = Flask(__name__)

load_dotenv()
client = Groq(api_key=os.getenv("XAI_API_KEY"))

try:
    guard = Guard.from_rail("guardrails.yaml")
except FileNotFoundError:
    print("⚠️ Arquivo 'guardrails.yaml' não encontrado. Usando guard padrão.")
    guard = Guard()


def chamar_groq(perguntas):
    try:
        # Faz a chamada ao modelo da Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é a Sally, uma assistente amigável e didática."},
                {"role": "user", "content": "\n".join(perguntas)}
            ],
            temperature=0.5,
            max_completion_tokens=512,
        )

        resposta_bruta = completion.choices[0].message.content

        # 🧩 Aplica o guardrail definido no YAML
        validated_response = guard.validate(resposta_bruta)

        # Se o output for um dicionário, pega o campo 'resposta'
        if isinstance(validated_response.validated_output, dict):
            return validated_response.validated_output.get("resposta", resposta_bruta)
        # Se for texto puro, retorna diretamente
        elif isinstance(validated_response.validated_output, str):
            return validated_response.validated_output
        # Se nada disso, retorna o texto bruto
        else:
            return resposta_bruta


    except Exception as e:
        print(f"Erro ao chamar o modelo da Groq: {e}")
        return f"⚠️ Ocorreu um erro ao processar sua mensagem: {e}"


# 🔹 Carrega perguntas iniciais
with open("perguntas.json", "r", encoding="utf-8") as f:
    perguntas_data = json.load(f)
perguntas = perguntas_data["perguntas_iniciais"]

usuarios = {}

@app.route("/")
def home():
    return render_template("index.html")

# 🔹 Função para validar respostas por tipo
def resposta_valida_por_tipo(resposta, tipo):
    resposta = resposta.strip()
    if tipo == "sim_nao":
        return resposta.lower() in ["sim", "não", "nao"]
    elif tipo == "telefone":
        numeros = "".join(filter(str.isdigit, resposta))
        return len(numeros) >= 8
    elif tipo == "texto":
        return bool(resposta)
    elif tipo == "formacao":
        opcoes = [
            "Ensino Fundamental Completo", "Ensino Médio Completo",
            "Ensino Superior Completo", "Pós-Graduando", "Pós-Graduado"
        ]
        return any(op.lower() in resposta.lower() for op in opcoes)
    elif tipo == "opcao_multipla":
        return bool(resposta)
    else:
        return bool(resposta)

# 🔹 Função para salvar histórico em Excel
def salvar_excel(user_id, historico):
    df = pd.DataFrame(historico)
    caminho_pasta = "conversas"
    os.makedirs(caminho_pasta, exist_ok=True)
    caminho_arquivo = os.path.join(caminho_pasta, f"conversa_{user_id}.xlsx")
    for tentativa in range(3):
        try:
            df.to_excel(caminho_arquivo, index=False)
            break
        except PermissionError:
            print("⚠️ Arquivo está em uso. Feche o Excel e tente novamente...")
            time.sleep(2)
    return caminho_arquivo

# 🔹 Carrega perguntas iniciais
with open("perguntas.json", "r", encoding="utf-8") as f:
    perguntas_data = json.load(f)
perguntas = perguntas_data["perguntas_iniciais"]

usuarios = {}

#Guardrail - detectar temas sensíveis
def verificar_assunto_sensivel(mensagem):
    mensagem = mensagem.lower()

    # Palavras-chave relacionadas a finanças pessoais e investimentos
    termos_sensiveis = [
        "quanto investir", "onde investir", "investir meu dinheiro",
        "melhor investimento", "lucro rápido", "ganhar dinheiro",
        "quanto devo investir", "retorno garantido", "rendimento mensal","quero investir"
    ]

    # Retorna True se encontrar qualquer termo sensível
    return any(termo in mensagem for termo in termos_sensiveis)


# 🔹 Chat endpoint
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

    # 🔹 Guarda histórico do usuário
    usuario["historico"].append({
        "quem": "Usuário",
        "mensagem": mensagem,
        "hora": datetime.now().strftime("%H:%M:%S")
    })
    if verificar_assunto_sensivel(mensagem):
        resposta_usuario = (
            "Esse assunto é tratado diretamente com nossa equipe especializada. "
            "Por favor, fale com um humano pelo WhatsApp 👇\n\n"
            "<a href='https://api.whatsapp.com/send?phone=5583987168376' target='_blank'>"
    "Falar com a Sally no WhatsApp</a>"
        )
        usuario["historico"].append({
            "quem": "Sally",
            "mensagem": resposta_usuario,
            "hora": datetime.now().strftime("%H:%M:%S")
        })
        salvar_excel(user_id, usuario["historico"])
        return jsonify({"response": resposta_usuario})


    # 🔹 Se o usuário fizer uma pergunta fora do roteiro
    if "?" in mensagem:
        resposta_usuario = chamar_groq([mensagem])

        usuario["historico"].append({
            "quem": "Sally",
            "mensagem": resposta_usuario,
            "hora": datetime.now().strftime("%H:%M:%S")
        })
        salvar_excel(user_id, usuario["historico"])

        # Se houver pergunta pendente, lembra o usuário
        if usuario["pergunta_atual"]:
            pergunta_pendente = usuario["pergunta_atual"]["texto"]
            resposta_usuario += f"\n\nPor favor, responda corretamente: {pergunta_pendente}"

        return jsonify({"response": resposta_usuario})

    # 🔹 Se houver pergunta obrigatória pendente
    if usuario["pergunta_atual"]:
        tipo_resposta = usuario["pergunta_atual"].get("tipo", "texto")
        if resposta_valida_por_tipo(mensagem, tipo_resposta):
            usuario["respostas"].append(mensagem)
            usuario["pergunta_atual"] = None
        else:
            pergunta_pendente = usuario["pergunta_atual"]["texto"]
            return jsonify({
                "response": f"Por favor, responda corretamente: {pergunta_pendente}"
            })

    # 🔹 Próxima pergunta do roteiro
    if usuario["indice"] < len(perguntas):
        proxima_pergunta = perguntas[usuario["indice"]]
        usuario["indice"] += 1

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