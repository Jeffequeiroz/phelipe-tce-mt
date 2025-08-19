<<<<<<< HEAD
# app.py - Phelipe Online - Versão Completa (sem OCR)
import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import PyPDF2
import json
from datetime import datetime

# --- INICIALIZAÇÃO DO SESSION_STATE ---
if 'analise_feita' not in st.session_state:
    st.session_state.analise_feita = False
if 'data' not in st.session_state:
    st.session_state.data = {}
if 'csv' not in st.session_state:
    st.session_state.csv = None
if 'csv_filename' not in st.session_state:
    st.session_state.csv_filename = ""

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Phelipe Online - TCE-MT", page_icon="🔍", layout="wide")
st.title("🔍 Phelipe: Assistente de Análise de PPCIs do TCE-MT")

# --- CONFIGURAÇÃO DA API DO GEMINI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")
except Exception as e:
    st.error("⚠️ Erro de configuração. Contate o administrador.")
    st.stop()

# --- PROMPT DO SISTEMA (ANÁLISE GERAL) ---
prompt_sistema = """
Você é Phelipe, um agente especializado em análise de recomendações do TCE-MT, com dupla expertise:
1. Técnico de controle externo (TCE-MT)
2. Especialista em controle interno da SES-MT

OBJETIVO PRINCIPAL:
Verificar se a ação do gestor é compatível com a recomendação, com base apenas nos documentos do processo.

ETAPAS DA ANÁLISE:

1. 📚 ANÁLISE MULTIDOCUMENTAL (Contexto Técnico)
   - Relatório de Auditoria: Falha constatada, contexto fático, base legal, valor do dano
   - Parecer do MPC: Posicionamento técnico, concordância ou ressalva
   - Decisão do TCE-MT: Recomendação específica, prazo, responsabilidades
   - Resposta do Gestor: Ação informada, prazo, evidências anexadas

2. ⏳ RECONSTRUÇÃO DA CRONOLOGIA
   Ordene os eventos:
   - O que foi constatado?
   - Como o MPC opinou?
   - O que decidiram os conselheiros?
   - Qual foi a resposta do gestor?
   - Há coerência entre a resposta e o problema?

3. 🏥 ANÁLISE CONTEXTUAL (SES-MT)
   Avalie a viabilidade prática da ação, considerando:
   - Estrutura da SES-MT
   - Recursos humanos
   - Sistemas de informação

4. 🧩 MEMÓRIA INSTITUCIONAL
   Após a análise, consulte o histórico e gere observações como:
   > 💬 Phelipe lembra: Este tipo de irregularidade já ocorreu em 3 unidades nos últimos 18 meses.

SAÍDA:
Retorne apenas um JSON envolto em ```json ... ```, com:
{
  "relatorio_tecnico": "Texto completo com sumário cronológico, crítica técnica e conclusão.",
  "analise_contextual": "Avaliação da viabilidade dentro da realidade operacional da SES-MT.",
  "insights_capacitacao": {
    "padroes_identificados": [],
    "sugestoes_prevencao": [],
    "modus_operandi": []
  },
  "indicios_dano_erario": {
    "consta_dano": false,
    "descricao": "Não consta",
    "fundamentacao": "Não consta"
  },
  "observacoes_memoria": "..."
}

REGRAS ESTRITAS:
- Nunca invente, suponha ou estime dados.
- Se a informação não estiver no documento, diga "Não consta".
- Sempre cite a fonte: "conforme mencionado na decisão", "segundo o PPCI".
- Use linguagem técnica, clara e objetiva.
- Retorne apenas o JSON. Nada além disso.
"""

# --- FUNÇÃO PARA EXTRAR TEXTO DE PDFs (SEM OCR) ---
def extrair_texto_pdf(uploaded_files):
    documentos_texto = ""
    for file in uploaded_files:
        file.seek(0)
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    documentos_texto += f"[{file.name} - Página {i+1}]\n{text}\n\n"
                else:
                    documentos_texto += f"[{file.name} - Página {i+1}]\n[Texto não extraído - PDF escaneado]\n\n"
        except Exception as e:
            documentos_texto += f"[Erro ao ler {file.name}: {str(e)}]\n"
    return documentos_texto or "Nenhum texto extraído."

# --- INTERFACE ---
st.subheader("📥 Documentos do Processo")
uploaded_files = st.file_uploader(
    "Envie todos os documentos (PDFs)", 
    type=["pdf"], 
    accept_multiple_files=True
)

st.subheader("📝 Dados da Decisão (mesma para todas as recomendações)")
num_decisao = st.text_input("🔢 Número da Decisão (ex: Acórdão 1234/2025)")
data_decisao = st.text_input("📅 Data da Decisão")
num_processo_tce = st.text_input("📋 Número do Processo no TCE")
orgao_decisao = st.text_input("🏛️ Órgão que emitiu a decisão", value="TCE-MT")

st.subheader("📌 Análise da Recomendação")
servidor_uniseci = st.text_input("🧑‍💼 Servidor da UNISECI/SES-MT")
data_analise = datetime.now().strftime("%d/%m/%Y")
num_ppci = st.text_input("📄 Número do PPCI")
num_recomendacao = st.text_input("🔖 Número da Recomendação")
cod_responsavel = st.text_input("🔐 Código do Responsável OU Procedimento")
gestor = st.text_input("👨‍💼 Gestor")

recomendacao = st.text_area("📌 Recomendação", height=150)

# --- 🔍 CAMPO CORRIGIDO: Status da Ação apresentada pelo Gestor ---
status_acao = st.selectbox(
    "🔧 Status da Ação apresentada pelo Gestor",
    ["Selecione...", "Implementada", "Em Implementação"],
    help="Status informado pelo gestor: se a ação já foi realizada ou está em andamento/planejada."
)

data_implementacao_gestor = st.text_input(
    "📅 Data informada pelo gestor (de implementação ou previsão)",
    help="Ex: 15/03/2025 (para 'Em Implementação') ou 10/02/2025 (para 'Implementada')"
)

acao_gestor = st.text_area("📝 Ação do Gestor", height=150)

if st.button("🚀 Analisar com Phelipe") and uploaded_files and num_decisao and status_acao != "Selecione...":
    with st.spinner("Phelipe está analisando... ⏳"):
        try:
            # Extrai texto dos PDFs (sem OCR)
            documentos_texto = extrair_texto_pdf(uploaded_files)

            # Monta prompt completo
            prompt_completo = f"{prompt_sistema}\n\n=== DOCUMENTOS DO PROCESSO ===\n{documentos_texto}"
            
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

                # Salva no session_state
                st.session_state.data = data
                st.session_state.analise_feita = True

                # --- GERAÇÃO DE CSV ---
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
                    "status_acao": status_acao,
                    "data_implementacao_gestor": data_implementacao_gestor,
                    "relatorio_tecnico": data.get("relatorio_tecnico", "Não disponível"),
                    "analise_contextual": data.get("analise_contextual", "Não disponível"),
                    "classificacao_final": data.get("classificacao_final", "Não classificado"),
                    "insights_prevencao": ", ".join(data.get("insights_capacitacao", {}).get("sugestoes_prevencao", ["Nenhuma"])),
                    "indicio_dano": "Sim" if data.get("indicios_dano_erario", {}).get("consta_dano") else "Não",
                    "detalhe_dano": data.get("indicios_dano_erario", {}).get("descricao", "Não consta"),
                    "observacoes_memoria": data.get("observacoes_memoria", "Nenhuma")
                }])
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.session_state.csv = csv
                st.session_state.csv_filename = f"phelipe_{num_decisao.replace('/', '-')}.csv"

            except Exception as e:
                st.error(f"Erro ao processar saída: {e}")
                st.text(output)

        except Exception as e:
            st.error(f"Erro ao processar PDF: {e}")

# --- EXIBIÇÃO DOS RESULTADOS ---
if st.session_state.analise_feita:
    data = st.session_state.data

    st.subheader("📄 Relatório Técnico")
    st.write(data.get("relatorio_tecnico", "Não disponível"))

    st.subheader("🏥 Análise Contextual (SES-MT)")
    st.write(data.get("analise_contextual", "Não disponível"))

    # --- 📝 ANÁLISE DA AÇÃO DO GESTOR (com prompt isolado) ---
    st.subheader("📝 Análise da Ação do Gestor")
    
    try:
        prompt_analise_acao = f"""
        Você é Phelipe, um especialista técnico em controle interno, controle externo, SES/MT, integridade e normas aplicáveis.
        Sua tarefa é **avaliar diretamente se a ação do gestor cumpre a recomendação**, com base apenas nos documentos.

        ### RECOMENDAÇÃO:
        {recomendacao}

        ### AÇÃO DO GESTOR:
        {acao_gestor}

        ### STATUS DA AÇÃO:
        {status_acao}

        ### INSTRUÇÕES:
        1. Compare diretamente a ação com a recomendação.
        2. Se o status for "Implementada":
           - Verifique se há **evidência documental** da execução.
           - Avalie se a ação **realmente implementou** a recomendação.
        3. Se o status for "Em Implementação":
           - Avalie o **potencial de eficácia**: a ação descrita corrige a causa raiz?
           - Verifique se o **prazo informado é coerente e factível**.
        4. Classifique com base nisso:
           - ✅ Compatível: ação completa e comprovada (ou plano viável)
           - ⚠️ Parcialmente compatível: ação incompleta, sem evidência ou com risco alto
           - ❌ Incompatível: ação irrelevante, contradiz a recomendação ou não corrige o problema
           - 🚫 Não Aplicável: justifique
        5. Retorne apenas um texto claro, técnico e objetivo, com até 150 palavras.
        6. Nunca invente dados. Se não constar, diga "Não consta no documento".
        """

        response = model.generate_content(prompt_analise_acao)
        analise_acao = response.text.strip()
        st.write(analise_acao)

        # Atualiza a classificação final
        if "✅ Compatível" in analise_acao:
            st.session_state.data["classificacao_final"] = "✅ Compatível"
        elif "⚠️ Parcialmente" in analise_acao:
            st.session_state.data["classificacao_final"] = "⚠️ Parcialmente compatível"
        elif "❌ Incompatível" in analise_acao:
            st.session_state.data["classificacao_final"] = "❌ Incompatível"
        elif "🚫 Não Aplicável" in analise_acao:
            st.session_state.data["classificacao_final"] = "🚫 Não Aplicável"

    except Exception as e:
        st.error(f"Erro ao gerar análise da ação: {e}")

    # --- 📊 CLASSIFICAÇÃO FINAL ---
    st.subheader("📊 Classificação Final")
    st.markdown(f"**{data.get('classificacao_final', 'Não classificado')}**")

    # --- 🧠 INSIGHTS PARA CAPACITAÇÃO ---
    st.subheader("🎓 Insights para Capacitação")
    insights = data.get("insights_capacitacao", {})
    st.write("**Padrões identificados:**")
    for p in insights.get("padroes_identificados", []):
        st.write(f"• {p}")
    st.write("**Sugestões de prevenção:**")
    for s in insights.get("sugestoes_prevencao", []):
        st.write(f"• {s}")
    st.write("**Modus Operandi (se houver indício de má-fé):**")
    for m in insights.get("modus_operandi", []):
        st.write(f"• {m}")

    # --- 💸 INDÍCIOS DE DANO AO ERÁRIO ---
    st.subheader("⚠️ Indícios de Dano ao Erário")
    dano = data.get("indicios_dano_erario", {})
    if dano.get("consta_dano"):
        st.markdown(f"**✅ Há indício de dano ao erário**")
        st.write(dano.get("descricao", "Não especificado"))
        st.caption(f"Fonte: {dano.get('fundamentacao', 'Não consta')}")
    else:
        st.markdown(f"**❌ Não há menção a dano ao erário**")
        st.caption(dano.get("descricao", "Não consta"))

    # --- 🧠 OBSERVAÇÕES DE MEMÓRIA INSTITUCIONAL ---
    st.subheader("🧠 Observações Contextuais (Memória Institucional)")
    obs = data.get("observacoes_memoria", "Nenhuma observação registrada.")
    st.write(obs)

    # --- BOTÃO DE DOWNLOAD DO CSV ---
    if st.session_state.csv:
        st.download_button(
            "⬇️ Baixar CSV (completo)",
            data=st.session_state.csv,
            file_name=st.session_state.csv_filename,
            mime="text/csv"
        )

# --- 💬 PERGUNTE AO PHELipe (com memória) ---
st.subheader("💬 Pergunte ao Phelipe")
pergunta = st.text_input("Ex: Quem são os auditores? Já houve isso em Rondonópolis?")
if pergunta:
    with st.spinner("Buscando no histórico..."):
        try:
            contexto = ""
            try:
                df = pd.read_csv("memoria/historico.csv")
                candidatos = df[
                    df['num_decisao'].str.contains(pergunta, case=False, na=True) |
                    df['recomendacao'].str.contains(pergunta, case=False, na=True) |
                    df['gestor'].str.contains(pergunta, case=False, na=True)
                ]
                if not candidatos.empty:
                    contexto += "📌 Casos semelhantes encontrados:\n"
                    for _, row in candidatos.iterrows():
                        contexto += f"- {row['num_decisao']}: {row['recomendacao'][:100]}...\n"
            except Exception as e:
                contexto += "⚠️ Nenhum caso encontrado no histórico.\n"

            if contexto.strip():
                prompt_busca = f"""
                Com base no contexto abaixo, responda à pergunta com rigor técnico.
                Se a informação não estiver no documento, diga "Não consta".

                Pergunta: {pergunta}
                Contexto: {contexto}
                """
                response = model.generate_content(prompt_busca)
                st.write(response.text)
            else:
                st.info("🔍 Nenhum dado encontrado para responder.")

        except Exception as e:
            st.error(f"Erro na busca: {e}")
=======
# app.py - Phelipe Online - Versão para Streamlit Cloud (sem OCR)
import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import PyPDF2
import json
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Phelipe Online - TCE-MT", page_icon="🔍", layout="wide")
st.title("🔍 Phelipe: Assistente de Análise de PPCIs do TCE-MT")

# --- CONFIGURAÇÃO DA API DO GEMINI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")
except Exception as e:
    st.error("⚠️ Erro de configuração. Contate o administrador.")
    st.stop()

# --- PROMPT DO SISTEMA (ANÁLISE GERAL) ---
prompt_sistema = """
Você é Phelipe, um agente especializado em análise de recomendações do TCE-MT, com dupla expertise:
1. Técnico de controle externo (TCE-MT)
2. Especialista em controle interno da SES-MT

OBJETIVO PRINCIPAL:
Verificar se a ação do gestor é compatível com a recomendação, com base apenas nos documentos do processo.

ETAPAS DA ANÁLISE:

1. 📚 ANÁLISE MULTIDOCUMENTAL (Contexto Técnico)
   - Relatório de Auditoria: Falha constatada, contexto fático, base legal, valor do dano
   - Parecer do MPC: Posicionamento técnico, concordância ou ressalva
   - Decisão do TCE-MT: Recomendação específica, prazo, responsabilidades
   - Resposta do Gestor: Ação informada, prazo, evidências anexadas

2. ⏳ RECONSTRUÇÃO DA CRONOLOGIA
   Ordene os eventos:
   - O que foi constatado?
   - Como o MPC opinou?
   - O que decidiram os conselheiros?
   - Qual foi a resposta do gestor?
   - Há coerência entre a resposta e o problema?

3. 🏥 ANÁLISE CONTEXTUAL (SES-MT)
   Avalie a viabilidade prática da ação, considerando:
   - Estrutura da SES-MT
   - Recursos humanos
   - Sistemas de informação

4. 🧩 MEMÓRIA INSTITUCIONAL
   Após a análise, consulte o histórico e gere observações como:
   > 💬 Phelipe lembra: Este tipo de irregularidade já ocorreu em 3 unidades nos últimos 18 meses.

SAÍDA:
Retorne apenas um JSON envolto em ```json ... ```, com:
{
  "relatorio_tecnico": "Texto completo com sumário cronológico, crítica técnica e conclusão.",
  "analise_contextual": "Avaliação da viabilidade dentro da realidade operacional da SES-MT.",
  "insights_capacitacao": {
    "padroes_identificados": [],
    "sugestoes_prevencao": [],
    "modus_operandi": []
  },
  "indicios_dano_erario": {
    "consta_dano": false,
    "descricao": "Não consta",
    "fundamentacao": "Não consta"
  },
  "observacoes_memoria": "..."
}

REGRAS ESTRITAS:
- Nunca invente, suponha ou estime dados.
- Se a informação não estiver no documento, diga "Não consta".
- Sempre cite a fonte: "conforme mencionado na decisão", "segundo o PPCI".
- Use linguagem técnica, clara e objetiva.
- Retorne apenas o JSON. Nada além disso.
"""

# --- FUNÇÃO PARA EXTRAR TEXTO DE PDFs (SEM OCR) ---
def extrair_texto_pdf(uploaded_files):
    documentos_texto = ""
    for file in uploaded_files:
        file.seek(0)
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    documentos_texto += f"[{file.name} - Página {i+1}]\n{text}\n\n"
                else:
                    documentos_texto += f"[{file.name} - Página {i+1}]\n[Texto não extraído - PDF escaneado]\n\n"
        except Exception as e:
            documentos_texto += f"[Erro ao ler {file.name}: {str(e)}]\n"
    return documentos_texto or "Nenhum texto extraído."

# --- INTERFACE ---
st.subheader("📥 Documentos do Processo")
uploaded_files = st.file_uploader(
    "Envie todos os documentos (PDFs)", 
    type=["pdf"], 
    accept_multiple_files=True
)

st.subheader("📝 Dados da Decisão (mesma para todas as recomendações)")
num_decisao = st.text_input("🔢 Número da Decisão (ex: Acórdão 1234/2025)")
data_decisao = st.text_input("📅 Data da Decisão")
num_processo_tce = st.text_input("📋 Número do Processo no TCE")
orgao_decisao = st.text_input("🏛️ Órgão que emitiu a decisão", value="TCE-MT")

st.subheader("📌 Análise da Recomendação")
servidor_uniseci = st.text_input("🧑‍💼 Servidor da UNISECI/SES-MT")
data_analise = datetime.now().strftime("%d/%m/%Y")
num_ppci = st.text_input("📄 Número do PPCI")
num_recomendacao = st.text_input("🔖 Número da Recomendação")
cod_responsavel = st.text_input("🔐 Código do Responsável OU Procedimento")
gestor = st.text_input("👨‍💼 Gestor")

recomendacao = st.text_area("📌 Recomendação", height=150)

# --- 🔍 CAMPO CORRIGIDO: Status da Ação apresentada pelo Gestor ---
status_acao = st.selectbox(
    "🔧 Status da Ação apresentada pelo Gestor",
    ["Selecione...", "Implementada", "Em Implementação"],
    help="Status informado pelo gestor: se a ação já foi realizada ou está em andamento/planejada."
)

data_implementacao_gestor = st.text_input(
    "📅 Data informada pelo gestor (de implementação ou previsão)",
    help="Ex: 15/03/2025 (para 'Em Implementação') ou 10/02/2025 (para 'Implementada')"
)

acao_gestor = st.text_area("📝 Ação do Gestor", height=150)

if st.button("🚀 Analisar com Phelipe") and uploaded_files and num_decisao and status_acao != "Selecione...":
    with st.spinner("Phelipe está analisando... ⏳"):
        try:
            # Extrai texto dos PDFs (sem OCR)
            documentos_texto = extrair_texto_pdf(uploaded_files)

            # Monta prompt completo
            prompt_completo = f"{prompt_sistema}\n\n=== DOCUMENTOS DO PROCESSO ===\n{documentos_texto}"
            
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

                # --- EXIBIÇÃO DOS RESULTADOS ---
                st.subheader("📄 Relatório Técnico")
                st.write(data.get("relatorio_tecnico", "Não disponível"))

                st.subheader("🏥 Análise Contextual (SES-MT)")
                st.write(data.get("analise_contextual", "Não disponível"))

                # --- 📝 ANÁLISE DA AÇÃO DO GESTOR (com prompt isolado) ---
                st.subheader("📝 Análise da Ação do Gestor")
                
                try:
                    prompt_analise_acao = f"""
                    Você é Phelipe, um especialista técnico em controle interno, controle externo, SES/MT, integridade e normas aplicáveis.
                    Sua tarefa é **avaliar diretamente se a ação do gestor cumpre a recomendação**, com base apenas nos documentos.

                    ### RECOMENDAÇÃO:
                    {recomendacao}

                    ### AÇÃO DO GESTOR:
                    {acao_gestor}

                    ### STATUS DA AÇÃO:
                    {status_acao}

                    ### INSTRUÇÕES:
                    1. Compare diretamente a ação com a recomendação.
                    2. Se o status for "Implementada":
                       - Verifique se há **evidência documental** da execução.
                       - Avalie se a ação **realmente implementou** a recomendação.
                    3. Se o status for "Em Implementação":
                       - Avalie o **potencial de eficácia**: a ação descrita corrige a causa raiz?
                       - Verifique se o **prazo informado é coerente e factível**.
                    4. Classifique com base nisso:
                       - ✅ Compatível: ação completa e comprovada (ou plano viável)
                       - ⚠️ Parcialmente compatível: ação incompleta, sem evidência ou com risco alto
                       - ❌ Incompatível: ação irrelevante, contradiz a recomendação ou não corrige o problema
                       - 🚫 Não Aplicável: justifique
                    5. Retorne apenas um texto claro, técnico e objetivo, com até 150 palavras.
                    6. Nunca invente dados. Se não constar, diga "Não consta no documento".
                    """

                    response_acao = model.generate_content(prompt_analise_acao)
                    analise_acao = response_acao.text.strip()
                    st.write(analise_acao)

                    # Atualiza a classificação final
                    if "✅ Compatível" in analise_acao:
                        classificacao_final = "✅ Compatível"
                    elif "⚠️ Parcialmente" in analise_acao:
                        classificacao_final = "⚠️ Parcialmente compatível"
                    elif "❌ Incompatível" in analise_acao:
                        classificacao_final = "❌ Incompatível"
                    elif "🚫 Não Aplicável" in analise_acao:
                        classificacao_final = "🚫 Não Aplicável"
                    else:
                        classificacao_final = "❓ Não classificado"

                except Exception as e:
                    st.error(f"Erro ao gerar análise da ação: {e}")
                    classificacao_final = "Erro na análise"

                # --- 📊 CLASSIFICAÇÃO FINAL ---
                st.subheader("📊 Classificação Final")
                st.markdown(f"**{classificacao_final}**")

                # --- 🧠 INSIGHTS PARA CAPACITAÇÃO ---
                st.subheader("🎓 Insights para Capacitação")
                insights = data.get("insights_capacitacao", {})
                st.write("**Padrões identificados:**")
                for p in insights.get("padroes_identificados", []):
                    st.write(f"• {p}")
                st.write("**Sugestões de prevenção:**")
                for s in insights.get("sugestoes_prevencao", []):
                    st.write(f"• {s}")
                st.write("**Modus Operandi (se houver indício de má-fé):**")
                for m in insights.get("modus_operandi", []):
                    st.write(f"• {m}")

                # --- 💸 INDÍCIOS DE DANO AO ERÁRIO ---
                st.subheader("⚠️ Indícios de Dano ao Erário")
                dano = data.get("indicios_dano_erario", {})
                if dano.get("consta_dano"):
                    st.markdown(f"**✅ Há indício de dano ao erário**")
                    st.write(dano.get("descricao", "Não especificado"))
                    st.caption(f"Fonte: {dano.get('fundamentacao', 'Não consta')}")
                else:
                    st.markdown(f"**❌ Não há menção a dano ao erário**")
                    st.caption(dano.get("descricao", "Não consta"))

                # --- 🧠 OBSERVAÇÕES DE MEMÓRIA INSTITUCIONAL ---
                st.subheader("🧠 Observações Contextuais (Memória Institucional)")
                obs = data.get("observacoes_memoria", "Nenhuma observação registrada.")
                st.write(obs)

                # --- GERAÇÃO DE CSV ---
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
                    "status_acao": status_acao,
                    "data_implementacao_gestor": data_implementacao_gestor,
                    "relatorio_tecnico": data.get("relatorio_tecnico", "Não disponível"),
                    "analise_contextual": data.get("analise_contextual", "Não disponível"),
                    "classificacao_final": classificacao_final,
                    "insights_prevencao": ", ".join(data.get("insights_capacitacao", {}).get("sugestoes_prevencao", ["Nenhuma"])),
                    "indicio_dano": "Sim" if data.get("indicios_dano_erario", {}).get("consta_dano") else "Não",
                    "detalhe_dano": data.get("indicios_dano_erario", {}).get("descricao", "Não consta"),
                    "observacoes_memoria": data.get("observacoes_memoria", "Nenhuma")
                }])
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    "⬇️ Baixar CSV (completo)",
                    data=csv,
                    file_name=f"phelipe_{num_decisao.replace('/', '-')}.csv",
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"Erro ao processar saída: {e}")
                st.text(output)

        except Exception as e:
            st.error(f"Erro ao processar PDF: {e}")

# --- 💬 PERGUNTE AO PHELipe (com memória) ---
st.subheader("💬 Pergunte ao Phelipe")
pergunta = st.text_input("Ex: Quem são os auditores? Já houve isso em Rondonópolis?")
if pergunta:
    with st.spinner("Buscando no histórico..."):
        try:
            contexto = ""
            try:
                df = pd.read_csv("memoria/historico.csv")
                candidatos = df[
                    df['num_decisao'].str.contains(pergunta, case=False, na=True) |
                    df['recomendacao'].str.contains(pergunta, case=False, na=True) |
                    df['gestor'].str.contains(pergunta, case=False, na=True)
                ]
                if not candidatos.empty:
                    contexto += "📌 Casos semelhantes encontrados:\n"
                    for _, row in candidatos.iterrows():
                        contexto += f"- {row['num_decisao']}: {row['recomendacao'][:100]}...\n"
            except Exception as e:
                contexto += "⚠️ Nenhum caso encontrado no histórico.\n"

            if contexto.strip():
                prompt_busca = f"""
                Com base no contexto abaixo, responda à pergunta com rigor técnico.
                Se a informação não estiver no documento, diga "Não consta".

                Pergunta: {pergunta}
                Contexto: {contexto}
                """
                response = model.generate_content(prompt_busca)
                st.write(response.text)
            else:
                st.info("🔍 Nenhum dado encontrado para responder.")

        except Exception as e:
            st.error(f"Erro na busca: {e}")
>>>>>>> 5f27e44ad900bd055175110953dac9009f4d3f3b
