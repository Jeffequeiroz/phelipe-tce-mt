# app.py - Phelipe Online - Versão para Streamlit Cloud (sem OCR)
import streamlit as st
import google.generativeai as genai
import os
import io
import pandas as pd
import PyPDF2
import json
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Phelipe Online - TCE-MT", page_icon="🔍", layout="wide")
st.title("🔍 Phelipe: Assistente de Análise de PPCIs do TCE-MT")

# Configurar API do Gemini (usando Secrets do Streamlit)
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro")

# Prompt detalhado
prompt_sistema = """
Você é Phelipe, um agente especializado em análise de recomendações do TCE-MT, com dupla expertise:
1. Técnico de controle externo (TCE-MT)
2. Especialista em controle interno da SES-MT

OBJETIVO PRINCIPAL:
Verificar se a ação do gestor é compatível com a recomendação, com base apenas nos documentos do processo.

ETAPAS:
1. Analise o relatório, MPC, decisão e resposta.
2. Compare a ação com a recomendação.
3. Classifique: ✅ Compatível, ⚠️ Parcialmente, ❌ Incompatível, 🚫 Não Aplicável.
4. Justifique com base nos documentos.

ANÁLISE POR STATUS DA AÇÃO:

- Se a ação está "Em Implementação":
  → Avalie o potencial de eficácia: a ação descrita, se realizada conforme planejado, corrige o problema?
  → Verifique se o prazo informado é coerente, factível e razoável.

- Se a ação está "Implementada":
  → Verifique se há evidência documental da execução.
  → Avalie se a ação realmente implementou a recomendação.

SAÍDA:
Retorne apenas um JSON com:
{
  "relatorio_tecnico": "...",
  "analise_contextual": "...",
  "classificacao_final": "✅ Compatível",
  "insights_capacitacao": {},
  "observacoes_memoria": "..."
}
"""

# Função para extrair texto do PDF (sem OCR)
def extrair_texto_pdf(uploaded_file):
    try:
        uploaded_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"[Erro ao ler PDF: {uploaded_file.name}]"

# Interface
st.subheader("📥 Documentos do Processo")
uploaded_files = st.file_uploader("Envie todos os documentos (PDFs)", type=["pdf"], accept_multiple_files=True)

st.subheader("📝 Dados da Análise")
servidor_uniseci = st.text_input("🧑‍💼 Servidor da UNISECI/SES-MT")
data_analise = datetime.now().strftime("%d/%m/%Y")
num_decisao = st.text_input("🔢 Número da Decisão (ex: Acórdão 1234/2025)")
data_decisao = st.text_input("📅 Data da Decisão")
num_processo_tce = st.text_input("📋 Número do Processo no TCE")
num_ppci = st.text_input("📄 Número do PPCI")
num_recomendacao = st.text_input("🔖 Número da Recomendação")
cod_responsavel = st.text_input("🔐 Código do Responsável OU Procedimento")
orgao_decisao = st.text_input("🏛️ Órgão que emitiu a decisão", value="TCE-MT")
gestor = st.text_input("👨‍💼 Gestor")

recomendacao = st.text_area("📌 Recomendação", height=150)

status_acao = st.selectbox(
    "🔧 Status da Ação do Gestor",
    ["Selecione...", "Implementada", "Em Implementação"],
    help="Escolha se a ação já foi feita ou está em andamento/planejada."
)

data_implementacao_gestor = st.text_input(
    "📅 Data informada pelo gestor (de implementação ou previsão)",
    help="Ex: 15/03/2025 (para 'Em Implementação') ou 10/02/2025 (para 'Implementada')"
)

acao_gestor = st.text_area("📝 Ação do Gestor", height=150)

if st.button("🚀 Analisar com Phelipe") and uploaded_files and num_decisao and status_acao != "Selecione...":
    with st.spinner("Phelipe está analisando... ⏳"):
        try:
            # Extrai texto dos PDFs
            documentos_texto = ""
            for file in uploaded_files:
                text = extrair_texto_pdf(file)
                documentos_texto += f"\n[{file.name}]\n{text}\n"

            # Monta prompt completo
            prompt_completo = f"{prompt_sistema}\n\nNúmero da Decisão: {num_decisao}\nData da Decisão: {data_decisao}\nProcesso: {num_processo_tce}\nPPCI: {num_ppci}\nRecomendação: {recomendacao}\nStatus da Ação: {status_acao}\nData de Implementação (Gestor): {data_implementacao_gestor}\nAção do Gestor: {acao_gestor}\n\n{documentos_texto}"
            
            response = model.generate_content(prompt_completo)
            output = response.text

            try:
                # Extrai JSON
                json_str = None
                if "```json" in output:
                    json_start = output.find("```json") + 7
                    json_end = output.find("```", json_start)
                    if json_end != -1:
                        json_str = output[json_start:json_end].strip()
                elif output.strip().startswith("{"):
                    json_str = output.strip()

                if json_str:
                    data = json.loads(json_str)
                else:
                    data = {"relatorio_tecnico": "Erro: Não foi possível extrair o JSON da resposta do Gemini."}

                # Exibe resultados
                st.subheader("📄 Relatório Técnico")
                st.write(data.get("relatorio_tecnico", "Não disponível"))

                st.subheader("🏥 Análise Contextual (SES-MT)")
                st.write(data.get("analise_contextual", "Não disponível"))

                st.subheader("📊 Classificação Final")
                st.markdown(f"**{data.get('classificacao_final', 'Não classificado')}**")

                # Gera CSV com todos os campos
                relatorio = data.get("relatorio_tecnico", "Não disponível")
                analise_contextual = data.get("analise_contextual", "Não disponível")
                classificacao_final = data.get("classificacao_final", "Não classificado")

                df = pd.DataFrame([{
                    "data_analise": data_analise,
                    "servidor_uniseci": servidor_uniseci,
                    "num_decisao": num_decisao,
                    "data_decisao": data_decisao,
                    "num_processo_tce": num_processo_tce,
                    "num_ppci": num_ppci,
                    "num_recomendacao": num_recomendacao,
                    "cod_responsavel": cod_responsavel,
                    "orgao_decisao": orgao_decisao,
                    "gestor": gestor,
                    "recomendacao": recomendacao[:200],
                    "acao_gestor": acao_gestor[:200],
                    "status_conformidade": classificacao_final,
                    "status_acao": status_acao,
                    "data_implementacao_gestor": data_implementacao_gestor,
                    "relatorio_tecnico": relatorio,
                    "analise_contextual": analise_contextual,
                    "classificacao_final": classificacao_final
                }])
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "⬇️ Baixar CSV (completo)",
                    data=csv,
                    file_name=f"phelipe_completo_{num_decisao.replace('/', '-')}.csv",
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"Erro ao processar saída: {e}")
                st.text(output)

        except Exception as e:
            st.error(f"Erro ao processar PDF: {e}")
else:
    st.info("Envie os documentos, preencha os dados e selecione o status da ação para começar a análise.")