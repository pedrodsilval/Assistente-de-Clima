import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
HISTORICO_JSON = "historico.json"
HISTORICO_TXT = "historico.txt"

def validar_data(data_str: str, hora_str: str) -> Optional[datetime]:
    """
    Valida a string de data e hora fornecida pelo usuário.
    Garante que a data não está no passado e não ultrapassa o limite de 5 dias da API.
    """
    try:
        dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
        agora = datetime.now()
        limite = agora + timedelta(days=5)
        
        if dt < agora:
            print("❌ Ops! Essa data/hora já passou. Só consigo prever o futuro.")
            return None
        if dt > limite:
            print("❌ Data muito distante! A API gratuita limita a previsão a 5 dias no futuro.")
            return None
            
        return dt
    except ValueError:
        print("❌ Formato inválido! Certifique-se de usar DD/MM/AAAA e HH:MM.")
        return None

def buscar_previsao(cidade: str, dt: datetime) -> Optional[Tuple[Dict[str, Any], str, str]]:
    """
    Consome a API do OpenWeatherMap para buscar a previsão do tempo.
    Retorna o bloco de previsão mais próximo do horário solicitado, o nome da cidade e o país.
    """
    if not API_KEY:
        print("❌ Erro interno: OPENWEATHER_API_KEY não configurada no arquivo .env!")
        return None
        
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&units=metric&lang=pt_br"
    
    # Tratamento de erro de rede (Try/Except)
    try:
        resp = requests.get(url)
        
        # Se a cidade não for encontrada ou a chave for inválida
        if resp.status_code == 404:
            print(f"❌ Cidade '{cidade}' não encontrada. Verifique a grafia.")
            return None
        elif resp.status_code == 401:
            print("❌ Erro de Autenticação: Sua API Key é inválida.")
            return None
            
        resp.raise_for_status() # Garante que outros erros HTTP sejam capturados
        
    except requests.exceptions.RequestException as e:
        print(f"📡 ❌ Sem conexão com a internet ou erro na API: {e}")
        return None
        
    dados = resp.json()
    melhor = None
    menor_diff = float("inf")
    
    for item in dados["list"]:
        dt_item = datetime.fromtimestamp(item["dt"])
        diff = abs((dt_item - dt).total_seconds())
        if diff < menor_diff:
            menor_diff = diff
            melhor = item
            
    return melhor, dados["city"]["name"], dados["city"]["country"]

def classificar_clima(temp: float) -> str:
    """
    Classifica o clima de forma amigável com base na temperatura em graus Celsius.
    """
    if temp <= 10:
        return "🥶 Muito frio"
    elif temp <= 18:
        return "🧥 Frio"
    elif temp <= 25:
        return "😊 Agradável"
    elif temp <= 32:
        return "☀️ Quente"
    else:
        return "🔥 Muito quente"

def salvar_historico(consulta: Dict[str, Any]) -> None:
    """
    Salva os dados da consulta de forma persistente em arquivos JSON e TXT.
    """
    historico = []
    if os.path.exists(HISTORICO_JSON):
        with open(HISTORICO_JSON, "r", encoding="utf-8") as f:
            historico = json.load(f)
            
    historico.append(consulta)
    with open(HISTORICO_JSON, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
        
    with open(HISTORICO_TXT, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*40}\n")
        f.write(f"Cidade: {consulta['cidade']}\n")
        f.write(f"Horário solicitado: {consulta['horario_solicitado']}\n")
        f.write(f"Horário na API: {consulta['horario_api']}\n")
        f.write(f"Temperatura: {consulta['temperatura']}°C\n")
        f.write(f"Sensação: {consulta['sensacao_termica']}°C\n")
        f.write(f"Clima: {consulta['descricao']}\n")
        f.write(f"Classificação: {consulta['classificacao']}\n")
        f.write(f"Umidade: {consulta['umidade']}%\n")
        f.write(f"Vento: {consulta['vento']} m/s\n")
        f.write(f"Consulta feita em: {consulta['consultado_em']}\n")

def exibir_resultado(resultado: Dict[str, Any], cidade: str, pais: str, dt: datetime) -> Dict[str, Any]:
    """
    Exibe os resultados formatados no terminal e monta o dicionário de dados da consulta.
    """
    temp = resultado["main"]["temp"]
    sensacao = resultado["main"]["feels_like"]
    umidade = resultado["main"]["humidity"]
    descricao = resultado["weather"][0]["description"]
    vento = resultado["wind"]["speed"]
    classificacao = classificar_clima(temp)
    dt_item = datetime.fromtimestamp(resultado["dt"])

    print(f"\n{'='*40}")
    print(f"📍 {cidade}, {pais}")
    print(f"📅 Horário solicitado: {dt.strftime('%d/%m/%Y %H:%M')}")
    print(f"⏰ Horário mais próximo na API: {dt_item.strftime('%d/%m/%Y %H:%M')}")
    print(f"🌡️  Temperatura: {temp}°C")
    print(f"🤔 Sensação térmica: {sensacao}°C")
    print(f"🌤️  Clima: {descricao.capitalize()}") # Capitalize para ficar mais bonito
    print(f"📊 Classificação: {classificacao}")
    print(f"💧 Umidade: {umidade}%")
    print(f"💨 Vento: {vento} m/s")
    print(f"{'='*40}\n")

    consulta = {
        "cidade": f"{cidade}, {pais}",
        "horario_solicitado": dt.strftime("%d/%m/%Y %H:%M"),
        "horario_api": dt_item.strftime("%d/%m/%Y %H:%M"),
        "temperatura": temp,
        "sensacao_termica": sensacao,
        "descricao": descricao,
        "classificacao": classificacao,
        "umidade": umidade,
        "vento": vento,
        "consultado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    salvar_historico(consulta)
    return consulta

def enviar_webhook(consulta: Dict[str, Any]) -> None:
    """
    Envia os dados estruturados para o Webhook do n8n e aguarda a resposta da Inteligência Artificial.
    """
    if not WEBHOOK_URL:
        print("⚠️  Aviso: Webhook do n8n não configurado no .env. (IA não acionada)")
        return
        
    print("🔄 Enviando dados para a IA no n8n...")
    try:
        r = requests.post(WEBHOOK_URL, json=consulta, timeout=10) # Timeout para não travar para sempre
        if r.status_code == 200:
            print("✅ Dados processados pelo n8n!")
            if r.text:
                print(f"\n🤖 DICA DA IA: {r.text}\n")
        else:
            print(f"⚠️  Erro ao comunicar com n8n: Código {r.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Erro de conexão com n8n: {e}")

def main() -> None:
    """
    Função principal que gerencia o loop de interação com o usuário.
    """
    print("🌤️  ASSISTENTE INTELIGENTE DE CLIMA")
    print("="*40)

    while True:
        print("\n⏳ DICA: Preferencialmente digite a cidade e o país (ex: 'Sao Paulo, BR') para melhores resultados.")
        cidade = input("Digite a cidade (ou 'sair' para encerrar): ").strip()
        if cidade.lower() == "sair":
            print("\n👋 Encerrando o assistente. Até logo!")
            break
        if not cidade:
            print("❌ A cidade não pode ser vazia!")
            continue

        print("\n⏳ DICA: A API prevê o clima apenas para o FUTURO (limite de 5 dias).")
        data_str = input("Digite a data (DD/MM/AAAA), 'hoje' ou 'amanhã': ").strip().lower()
        
        # Lógica inteligente para as datas
        if data_str == 'hoje':
            data_str = datetime.now().strftime("%d/%m/%Y")
        elif data_str in ['amanhã', 'amanha']:
            data_str = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
            
        hora_str = input("Digite o horário (HH:MM): ").strip()

        dt = validar_data(data_str, hora_str)
        if not dt:
            continue

        print("\n🔍 Buscando previsão...")
        resultado = buscar_previsao(cidade, dt)
        if not resultado:
            continue

        item, nome_cidade, pais = resultado
        consulta = exibir_resultado(item, nome_cidade, pais, dt)
        enviar_webhook(consulta)

        continuar = input("Deseja fazer outra consulta? (s/n): ").strip().lower()
        if continuar != "s":
            print("\n👋 Encerrando o assistente. Até logo!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Execução interrompida pelo usuário. Até logo!")