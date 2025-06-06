# 📢 Alerta de Homologação - Azure DevOps + GitHub Actions

Automação que envia alertas para o Teams (via Webhook/Logic App) sempre que uma atividade entra no estado **Homologation** no Azure DevOps.

---

## 📌 Funcionalidades

✅ Alerta único quando uma atividade entra em **Homologation**  
✅ Evita alertas duplicados com controle em `homologados.json`  
✅ Executa a cada 15 minutos em dias úteis no horário comercial  
✅ Usa campo customizado: `Custom.DataDeHomologacao`

---

## 🧠 Estrutura do Projeto

```bash
📁 alerta-techlead/
├── alerta_homologacao.py
├── homologados.json
├── requirements.txt
├── .env.example
└── .github/
    └── workflows/
        └── alerta_homologacao.yml
```

---

## ⚙️ Variáveis de Ambiente

Crie um arquivo `.env` com base no exemplo abaixo:

```env
AZURE_PAT=seu_pat_do_azure
HOMOLOGACAO_WEBHOOK_URL=https://url-do-seu-logic-app-ou-webhook
```

> Use o `.env.example` como base

---

## 🧪 Executar Localmente

```bash
pip install -r requirements.txt
python alerta_homologacao.py
```

---

## ☁️ GitHub Actions

O workflow `alerta_homologacao.yml`:
- Roda a cada 15 minutos entre 08h e 18h em dias úteis (BRT)
- Requer 2 secrets configurados:
  - `AZURE_PAT`
  - `HOMOLOGACAO_WEBHOOK_URL`

Configure os secrets no repositório pelo menu:
```
Settings > Secrets > Actions
```

---

## 🛡️ Controle de Duplicidade

O arquivo `homologados.json` mantém o histórico de alertas enviados para evitar duplicidade. Este arquivo pode ser limpo manualmente no início de cada nova sprint, se desejar.

---

## 📬 Exemplo de Alerta

> 🔔 Atividade entrou em Homologação  
> O item **#1234 - Corrigir erro X**, do desenvolvedor **João Silva** entrou para **Homologação** em **📅 06/06/2025 10:45**. Favor homologar essa atividade.

---

Desenvolvido com ❤️ para automação da Sprint Review 🚀