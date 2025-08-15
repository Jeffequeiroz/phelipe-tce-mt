# app.py - Phelipe Local - Versão Final Atualizada (12/08/2025)
# Assistente de Análise de PPCIs do TCE-MT com memória institucional

import streamlit as st
import google.generativeai as genai
import os
import io
import pandas as pd
import PyPDF2
from pdf2image import convert_from_bytes  # ✅ Importação correta
import pytesseract  # ✅ Importação correta
import json
from datetime import datetime
import glob

# Configuração da página
st.set_page_config(page_title="Phelipe - TCE-MT", page_icon="🔍", layout="wide")
st.title("🔍 Phelipe: Assistente de Análise de PPCIs do TCE-MT")

# Configurar API do Gemini
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Configure a chave da API do Gemini em `.streamlit/secrets.toml` ou como variável de ambiente.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-pro")

# Função para extrair texto com OCR se necessário
def extrair_texto_estruturado(uploaded_files):
    documentos_texto = ""
    for file in uploaded_files:
        # Lê o PDF
        file.seek(0)  # Garante que o ponteiro está no início
        pdf_reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                documentos_texto += f"\n[{file.name} - Página {i+1}]\n{text}\n"
        
        # Se não extraiu texto suficiente, tenta OCR
        if len(documentos_texto.strip()) < 100:  # PDF escaneado
            st.info(f"📄 {file.name} sem texto suficiente. Aplicando OCR...")
            try:
                images = convert_from_bytes(file.getvalue(), dpi=150)
                for i, img in enumerate(images):
                    ocr_text = pytesseract.image_to_string(img, lang='por')
                    documentos_texto += f"\n[{file.name} - Página {i+1} (OCR)]\n{ocr_text}\n"
            except Exception as e:
                st.warning(f"Erro ao aplicar OCR em {file.name}: {e}")
    
    return documentos_texto

# Prompt detalhado com análise diferenciada por status da ação
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
  → Se não houver prazo na recomendação, avalie se o prazo apresentado é adequado.
  → Considere riscos de não conclusão.

- Se a ação está "Implementada":
  → Verifique se há evidência documental da execução.
  → Avalie se a ação realmente implementou a recomendação.
  → Confira se a evidência apresentada comprova de fato o que foi afirmado.

ANÁLISE CONTEXTUAL (SES-MT):
Avalie a viabilidade prática da ação, considerando:
- Estrutura da SES-MT
- Recursos humanos
- Sistemas de informação

MEMÓRIA INSTITUCIONAL:
Após a análise, consulte o histórico e gere observações como:
> 💬 Phelipe lembra: Este tipo de irregularidade já ocorreu em 3 unidades nos últimos 18 meses.

SAÍDA:
Retorne apenas um JSON com:
{
  "relatorio_tecnico": "Texto completo com sumário, análise e conclusão.",
  "analise_contextual": "Avaliação da viabilidade dentro da SES-MT.",
  "classificacao_final": "✅ Compatível",
  "insights_capacitacao": {},
  "observacoes_memoria": ""
}
"""

# Interface
st.subheader("📥 Documentos do Processo")
uploaded_files = st.file_uploader("Envie todos os documentos (PDFs, imagens)", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

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

# NOVOS CAMPOS ADICIONADOS
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
            documentos_texto = extrair_texto_estruturado(uploaded_files)
            
            prompt_completo = f"{prompt_sistema}\n\nNúmero da Decisão: {num_decisao}\nData da Decisão: {data_decisao}\nProcesso: {num_processo_tce}\nPPCI: {num_ppci}\nRecomendação: {recomendacao}\nStatus da Ação: {status_acao}\nData de Implementação (Gestor): {data_implementacao_gestor}\nAção do Gestor: {acao_gestor}\n\n{documentos_texto}"
            
            response = model.generate_content(prompt_completo)
            output = response.text

            try:
                # Extrai JSON (suporta ```json ou apenas { })
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

                # Salva no histórico
                historico_path = "memoria/historico.csv"
                os.makedirs("memoria", exist_ok=True)
                if os.path.exists(historico_path):
                    df_hist = pd.read_csv(historico_path)
                    df_hist = pd.concat([df_hist, df], ignore_index=True)
                else:
                    df_hist = df
                df_hist.to_csv(historico_path, index=False, encoding='utf-8-sig')

                # Campo de perguntas
                st.subheader("🧠 Pergunte ao Phelipe (Memória Institucional)")
                pergunta = st.text_input("Ex: Já houve recomendação sobre dispensa de licitação em Rondonópolis?")
                if pergunta:
                    st.info("Phelipe está analisando padrões no histórico...")
                    # Aqui você pode integrar uma busca com Gemini no histórico

            except json.JSONDecodeError as e:
                st.error(f"Erro ao decodificar JSON: {e}")
                st.text("Saída bruta do Gemini:")
                st.text(output)
            except Exception as e:
                st.error(f"Erro ao processar saída: {e}")
                st.text(output)

        except Exception as e:
            st.error(f"Erro ao processar PDF: {e}")
else:
    st.info("Envie os documentos, preencha os dados e selecione o status da ação para começar a análise.")