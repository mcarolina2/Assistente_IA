
# Assistente_IA 🤖 , Assistente Virtual Multicanal com DeepSeek

Este projeto é um **assistente virtual inteligente** integrado aos principais canais de mensagens (**WhatsApp**, **Telegram** e **Instagram**), processando conversas com a **API da DeepSeek** e oferecendo uma **interface gráfica no Streamlit** para monitoramento, configuração e análise.

---

## 🚀 Funcionalidades

- 📩 **Recebe mensagens** via Webhook dos canais (WhatsApp, Telegram, Instagram)
- 🧠 **Processa e responde** usando a API de IA da DeepSeek
- 🔄 **Normaliza payloads** de diferentes plataformas para um formato padrão
- 🗂 **Mantém histórico** e contexto de conversas no banco de dados
- 📊 **Dashboard em Streamlit** para:
  - Visualizar conversas em tempo real
  - Configurar parâmetros do assistente
  - Exibir estatísticas de uso

---

## 📂 Estrutura do Projeto

- Assistente_IA/
│
├── backend/ # Backend com FastAPI
│ ├── main.py # Ponto de entrada da API
│ ├── routes/ # Rotas para webhooks
│ ├── services/ # Lógica de negócio e integração com IA
│ ├── database/ # Conexão e modelos do banco
│
├── streamlit_app/ # Interface gráfica
│ ├── dashboard.py
│ ├── pages/
│
├── tests/ # Testes automatizados
├── requirements.txt # Dependências
├── .env # Variáveis de ambiente (API keys)
└── README.md