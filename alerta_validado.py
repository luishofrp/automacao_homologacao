import requests
import base64
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

AZURE_ORGANIZATION = "iaratech"
AZURE_PROJECT = "Iara"
AZURE_PAT = os.getenv("AZURE_PAT")
WEBHOOK_URL = os.getenv("HOMOLOGACAO_WEBHOOK_URL")
LOG_PATH = "validados.json"

encoded_pat = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_pat}"
}


def carregar_validados():
    if not os.path.exists(LOG_PATH):
        return set()
    with open(LOG_PATH, "r") as f:
        return set(json.load(f))


def salvar_validados(ids):
    with open(LOG_PATH, "w") as f:
        json.dump(sorted(list(ids)), f)


def buscar_itens_homologation():
    wiql = {
        "query": f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.State] = 'Homologation'
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


def enviar_alerta_validado(wi_id, titulo, dev, data_homologacao):

    payload = {
        "title": "✅ Atividade Validada",
        "mensagem": f"O item **#{wi_id} - {titulo}**, do desenvolvedor **{dev}**, foi **validado com sucesso!**\n\n📅 Data de Homologação: **{data_homologacao}**",
        "url": f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_workitems/edit/{wi_id}"
    }
    requests.post(WEBHOOK_URL, json=payload)
    print(f"🎉 Alerta de validado enviado para #{wi_id}")


def executar():
    print("🔍 Verificando itens validados...")
    ids = buscar_itens_homologation()
    validados = carregar_validados()
    novos = set()

    for wi_id in ids:
        if wi_id in validados:
            continue

        dados = get_detalhes_item(wi_id)
        tags = dados["fields"].get("System.Tags", "")

        if "Validado!" in tags:
            titulo = dados["fields"].get("System.Title", "Sem título")
            dev = dados["fields"].get("System.AssignedTo", {}).get("displayName", "Não atribuído")
            data_hom = dados["fields"].get("Custom.DataDeHomologacao", "Não informada")
            enviar_alerta_validado(wi_id, titulo, dev, data_hom)
            novos.add(wi_id)

    if novos:
        salvar_validados(validados.union(novos))


if __name__ == "__main__":
    executar()