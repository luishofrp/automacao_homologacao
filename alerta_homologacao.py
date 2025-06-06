import os
import json
import base64
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

AZURE_ORGANIZATION = "iaratech"
AZURE_PROJECT = "Iara"
AZURE_PAT = os.getenv("AZURE_PAT")
WEBHOOK_HOMOLOGACAO = os.getenv("HOMOLOGACAO_WEBHOOK_URL")
LOG_PATH = "homologados.json"

encoded_pat = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_pat}"
}

def carregar_ids_alertados():
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH, "r") as f:
        return set(json.load(f))

def salvar_ids_alertados(ids):
    with open(LOG_PATH, "w") as f:
        json.dump(sorted(list(ids)), f)

def get_current_iteration_path():
    url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/work/teamsettings/iterations?$timeframe=current&api-version=6.0"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if not data['value']:
        raise Exception("Nenhuma sprint atual encontrada.")
    return data['value'][0]['path']

def buscar_work_items_em_homologacao(iteration_path):
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

def formatar_data(data_iso):
    try:
        return datetime.strptime(data_iso, "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y %H:%M")
    except:
        return "Data inválida"

def enviar_alerta(wi_id, titulo, dev_nome, data_formatada):
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
                            "text": f"🛠️ A atividade **#{wi_id} - {titulo}** entrou em **Homologação**.",
                            "wrap": True
                        },
                        {
                            "type": "TextBlock",
                            "text": f"👤 Desenvolvedor: {dev_nome}",
                            "wrap": True
                        },
                        {
                            "type": "TextBlock",
                            "text": f"📅 Data de Homologação: {data_formatada}",
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
    response = requests.post(WEBHOOK_HOMOLOGACAO, json=adaptive_card)
    print(f"✅ Alerta enviado para #{wi_id} - Status: {response.status_code}")

def executar_alerta_homologacao():
    print("🔍 Verificando sprint atual...")
    iteration_path = get_current_iteration_path()
    print(f"📅 Sprint atual: {iteration_path}")

    print("🔍 Buscando itens em Homologation...")
    ids = buscar_work_items_em_homologacao(iteration_path)
    if not ids:
        print("✅ Nenhum item em Homologation.")
        return

    ids_alertados = carregar_ids_alertados()
    novos_alertados = set()

    for wi_id in ids:
        if wi_id in ids_alertados:
            print(f"🔁 Item #{wi_id} já alertado. Ignorando.")
            continue

        dados = get_detalhes_item(wi_id)
        titulo = dados["fields"].get("System.Title", "Sem título")
        dev_nome = dados["fields"].get("System.AssignedTo", {}).get("displayName", "Não atribuído")
        data_homologacao = dados["fields"].get("Custom.6f0ce6f1-3e48-4e7a-8c8c-b77e39256fe7", None)
        print(f"🕵️ Valor bruto da Data de Homologação do item #{wi_id}: {data_homologacao}")
        from datetime import timezone

        def formatar_data_iso_utc_br(data_iso):
            try:
                dt_utc = datetime.strptime(data_iso, "%Y-%m-%dT%H:%M:%S.%fZ")
                dt_br = dt_utc - timedelta(hours=3)
                return dt_br.strftime("%d/%m/%Y %H:%M")
            except Exception as e:
                print(f"⚠️ Erro ao formatar data: {e}")
                return data_iso

        data_formatada = formatar_data_iso_utc_br(data_homologacao) if data_homologacao else "Não informada"
        


        enviar_alerta(wi_id, titulo, dev_nome, data_formatada)
        novos_alertados.add(wi_id)

    if novos_alertados:
        salvar_ids_alertados(ids_alertados.union(novos_alertados))
        print(f"💾 {len(novos_alertados)} novos alertas registrados.")

if __name__ == "__main__":
    executar_alerta_homologacao()
