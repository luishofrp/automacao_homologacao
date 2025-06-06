import requests
import base64
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv

load_dotenv()

AZURE_ORGANIZATION = "iaratech"
AZURE_PROJECT = "Iara"
AZURE_PAT = os.getenv("AZURE_PAT")
WEBHOOK_URL = os.getenv("HOMOLOGACAO_WEBHOOK_URL")
LOG_PATH = "pendentes.json"

encoded_pat = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_pat}"
}

def carregar_pendentes():
    if not os.path.exists(LOG_PATH):
        return {}
    with open(LOG_PATH, "r") as f:
        return json.load(f)

def salvar_pendentes(data):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)

def formatar_data_iso_utc_br(data_iso):
    try:
        dt_utc = datetime.strptime(data_iso, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt_br = dt_utc - timedelta(hours=3)
        return dt_br.strftime("%d/%m/%Y %H:%M")
    except Exception as e:
        print(f"⚠️ Erro ao formatar data: {e}")
        return data_iso

def get_current_iteration_path():
    url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/work/teamsettings/iterations?$timeframe=current&api-version=6.0"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if not data['value']:
        raise Exception("Nenhuma sprint atual encontrada.")
    return data['value'][0]['path']

def buscar_itens_homologation_sem_validado(iteration_path):
    wiql = {
        "query": f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.IterationPath] = '{iteration_path}'
          AND [System.State] = 'Homologation'
        """
    }
    url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/wiql?api-version=6.0"
    response = requests.post(url, headers=HEADERS, json=wiql)
    response.raise_for_status()
    return [item["id"] for item in response.json().get("workItems", [])]

def get_detalhes_item(wi_id):
    url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/_apis/wit/workitems/{wi_id}?api-version=6.0"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def deve_enviar_alerta(id_item, pendentes_log, horas=4):
    ultima = pendentes_log.get(str(id_item))
    if not ultima:
        return True
    ultima_data = datetime.strptime(ultima, "%Y-%m-%dT%H:%M:%S")
    return (datetime.now() - ultima_data) > timedelta(hours=horas)

def enviar_alerta_pendente(wi_id, titulo, dev, data_formatada):
    print(f"📅 Data formatada: {data_formatada}")
    adaptive_card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"🚨 Pendência de Validação",
                            "weight": "Bolder",
                            "size": "Medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": f"O item **#{wi_id} - {titulo}** do desenvolvedor **{dev}** entrou em **Homologação** em 📅 {data_formatada} e ainda não foi validado.",
                            "wrap": True
                        },
                        {
                            "type": "TextBlock",
                            "text": f"[🔗 Acessar item](https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_workitems/edit/{wi_id})",
                            "wrap": True
                        }
                    ]
                }
            }
        ]
    }

    response = requests.post(WEBHOOK_URL, json=adaptive_card)
    print(f"📤 Alerta adaptativo enviado para #{wi_id} - Status: {response.status_code}")

def executar():
    print("🔍 Verificando sprint atual...")
    iteration_path = get_current_iteration_path()
    print(f"📅 Sprint atual: {iteration_path}")

    pendentes_log = carregar_pendentes()

    print("🔍 Buscando itens em Homologation sem tag Validado!...")
    ids = buscar_itens_homologation_sem_validado(iteration_path)
    if not ids:
        print("✅ Nenhum item em Homologation na sprint atual.")
        return

    for wi_id in ids:
        dados = get_detalhes_item(wi_id)
        tags = dados["fields"].get("System.Tags", "")
        if "Validado!" in tags:
            print(f"✅ Item #{wi_id} já validado.")
            continue

        if not deve_enviar_alerta(wi_id, pendentes_log):
            print(f"⏳ Alerta para #{wi_id} já enviado recentemente.")
            continue

        titulo = dados["fields"].get("System.Title", "Sem título")
        dev = dados["fields"].get("System.AssignedTo", {}).get("displayName", "Não atribuído")
        data_hom = dados["fields"].get("Custom.6f0ce6f1-3e48-4e7a-8c8c-b77e39256fe7", "Não informada")
        data_formatada = formatar_data_iso_utc_br(data_hom) if data_hom != "Não informada" else "Não informada"

        enviar_alerta_pendente(wi_id, titulo, dev, data_formatada)

        pendentes_log[str(wi_id)] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    salvar_pendentes(pendentes_log)

if __name__ == "__main__":
    executar()
