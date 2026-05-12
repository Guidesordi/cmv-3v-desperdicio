"""Dashboard de Desperdício — Grupo 3V (acesso público pros gerentes).

Standalone — não depende de Atlas, Cantucci OS, nem planilhas locais.
Lê só o CSV do Google Forms (público via export).

Deploy: Streamlit Community Cloud (free).
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, timedelta

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# CONFIG
# ============================================================
SHEET_ID = "1qX36AZptjemPuwzoYq9n3QB7AD3NibhSizLXG9BtFKM"
GID = "2068526568"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# Mapeamento Unidade da planilha → label amigável
UNIDADE_MAP = {
    "ASA NORTE": "Cantucci Asa Norte",
    "ASA SUL": "Cantucci Asa Sul",
    "AGUAS CLARAS": "Cantucci Águas Claras",
    "ÁGUAS CLARAS": "Cantucci Águas Claras",
    "MANÉ": "Mané Brasília",
    "MANE": "Mané Brasília",
    "SUPERQUADRA": "Superquadra Norte",
    "SUPERQUADRA NORTE": "Superquadra Norte",
    "KOJI": "Koji",
}

# Cluster de motivos (mesmo do app principal, simplificado)
_CLUSTERS = {
    "Equipamento": ["GELADEIRA", "FREEZER", "CAMARA", "DESCONGELAMENTO",
                    "DESCONGELOU", "FERMENTOU", "RESISTENCIA", "PRODUTO CONGELOU"],
    "Cliente/iFood": ["IFOOD", "CLIENTE", "RECLAMACAO", "RECLAMAÇÃO", "CORTESIA"],
    "Validade": ["VALIDADE", "VENCIDO", "VENCEU", "VENCEND"],
    "Erro produção": ["ERRO DE PRODUCAO", "ERRO PRODUCAO", "ERROU", "ERRO DA COZINHA",
                       "PRODUTO ERRADO", "DESCONFIGUROU", "DESCONFIGURADO"],
    "Erro de salão": ["GARCOM", "GARÇOM", "DERRUBOU", "DERRAMOU", "PEDIDO ERRADO"],
    "Acidente": ["CAIU", "QUEBROU", "ACIDENTE", "QUEIMOU"],
    "Pré-preparo": ["DESCARTE NORMAL", "DESCARTE DE PROCESSAMENTO", "APARA"],
    "Outro": [],
}


def _norm(s: str) -> str:
    if not s:
        return ""
    s = str(s).upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return s


def _cluster_motivo(motivo: str) -> str:
    if not motivo:
        return "Outro"
    n = _norm(motivo)
    for cluster, kws in _CLUSTERS.items():
        if any(kw in n for kw in kws):
            return cluster
    return "Outro"


# ============================================================
# CARREGAR DADOS
# ============================================================
@st.cache_data(ttl=600, show_spinner="📥 Baixando dados...")
def carregar_desperdicio() -> pd.DataFrame:
    """Baixa CSV público do Google Forms e retorna DataFrame normalizado."""
    r = httpx.get(URL_CSV, follow_redirects=True, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))

    # Normalizar nomes de coluna — ordem IMPORTA (mais específico primeiro)
    # Coluna "Observação" contém substring "produto" no texto explicativo;
    # idem "Unidade de medida" contém "produto". Tratar específicos antes.
    REGRAS = [
        ("carimbo", "timestamp"),
        ("timestamp", "timestamp"),
        ("medida", "qty_unidade"),                # ANTES de "produto"
        ("observa", "observacao"),                # ANTES de "produto"
        ("motivo", "motivo"),
        ("quantidade", "qty_raw"),
        ("qual o produto", "produto"),            # match específico (pergunta do Form)
        ("produto que foi", "produto"),
        ("descartado", "produto"),                # fallback
        ("unidade", "unidade_raw"),               # POR ÚLTIMO (genérico)
    ]
    rename = {}
    for c in df.columns:
        norm = _norm(c).lower()
        for kw, target in REGRAS:
            if kw in norm:
                # Pula se já achou esse target em outra coluna (1ª ganha)
                if target not in rename.values():
                    rename[c] = target
                    break
    df = df.rename(columns=rename)

    # Data
    df["data"] = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["data"])

    # Unidade normalizada
    df["unidade_raw_norm"] = df["unidade_raw"].apply(_norm)
    df["unidade"] = df["unidade_raw_norm"].map(UNIDADE_MAP).fillna(df["unidade_raw"])

    # Cluster do motivo
    df["cluster"] = df["motivo"].apply(_cluster_motivo)

    # Quantidade (numérica — só pega o número, ignora unidade)
    def _parse_qty(v):
        if pd.isna(v):
            return None
        s = str(v).replace(",", ".")
        m = re.search(r"\d+(?:\.\d+)?", s)
        return float(m.group()) if m else None
    df["qty"] = df["qty_raw"].apply(_parse_qty)

    return df[["data", "unidade", "produto", "qty", "qty_unidade",
               "motivo", "cluster", "observacao"]].copy()


# ============================================================
# UI
# ============================================================
st.set_page_config(
    page_title="Desperdício · Grupo 3V",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="collapsed",  # mobile-friendly
)

# Cabeçalho mobile-friendly
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    .stMetric {background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px;}
    h1 {font-size: 1.6rem !important;}
    h2 {font-size: 1.3rem !important;}
    @media (max-width: 768px) {
        .stMetric {padding: 8px;}
        h1 {font-size: 1.3rem !important;}
    }
</style>
""", unsafe_allow_html=True)

st.title("🗑️ Desperdício · Grupo 3V")

# Botão atualizar (sidebar pra não poluir o app)
with st.sidebar:
    st.markdown("### Controles")
    if st.button("🔄 Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Dados atualizados automaticamente a cada 10 minutos.")

# Carregar dados
try:
    df = carregar_desperdicio()
except Exception as e:
    st.error(f"❌ Erro ao carregar dados: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

# ============================================================
# FILTROS (no topo, mobile-friendly)
# ============================================================
st.markdown("##### 🔎 Filtros")
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    unidades_disponiveis = ["Todas"] + sorted(df["unidade"].dropna().unique().tolist())
    unidade_sel = st.selectbox("Unidade", unidades_disponiveis, index=0)

with col2:
    opcoes_periodo = {
        "Últimos 7 dias": 7,
        "Últimos 14 dias": 14,
        "Últimos 30 dias": 30,
        "Últimos 90 dias": 90,
        "Mês atual": "mes_atual",
        "Tudo": None,
    }
    periodo_sel = st.selectbox("Período", list(opcoes_periodo.keys()), index=2)

with col3:
    clusters_disponiveis = ["Todos"] + sorted(df["cluster"].dropna().unique().tolist())
    cluster_sel = st.selectbox("Tipo de perda", clusters_disponiveis, index=0)

# Aplicar filtros
df_f = df.copy()
hoje = date.today()

valor_periodo = opcoes_periodo[periodo_sel]
if valor_periodo == "mes_atual":
    df_f = df_f[df_f["data"].dt.month == hoje.month]
    df_f = df_f[df_f["data"].dt.year == hoje.year]
elif isinstance(valor_periodo, int):
    di = hoje - timedelta(days=valor_periodo)
    df_f = df_f[df_f["data"].dt.date >= di]

if unidade_sel != "Todas":
    df_f = df_f[df_f["unidade"] == unidade_sel]

if cluster_sel != "Todos":
    df_f = df_f[df_f["cluster"] == cluster_sel]

if df_f.empty:
    st.info(f"Sem lançamentos para os filtros selecionados.")
    st.stop()

st.markdown("---")

# ============================================================
# KPIs
# ============================================================
n_lancamentos = len(df_f)
top_cluster = df_f["cluster"].value_counts().index[0] if len(df_f) > 0 else "—"
n_unidades = df_f["unidade"].nunique()
periodo_dias = (df_f["data"].max() - df_f["data"].min()).days + 1 if len(df_f) > 1 else 1
media_dia = n_lancamentos / periodo_dias if periodo_dias > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📋 Lançamentos", f"{n_lancamentos:,}".replace(",", "."))
with col2:
    st.metric("📅 Média/dia", f"{media_dia:.1f}")
with col3:
    st.metric("🏢 Unidades", n_unidades)
with col4:
    st.metric("🎯 Top motivo", top_cluster)

st.markdown("---")

# ============================================================
# GRÁFICOS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Por motivo", "📦 Top produtos", "📈 Tendência", "📋 Lançamentos"
])

# ---- Tab 1: Cluster ----
with tab1:
    ag = df_f.groupby("cluster").agg(
        n_lancamentos=("produto", "size"),
    ).reset_index().sort_values("n_lancamentos", ascending=False)
    ag["pct"] = (100 * ag["n_lancamentos"] / ag["n_lancamentos"].sum()).round(1)

    col_g, col_t = st.columns([3, 2])
    with col_g:
        fig = px.bar(
            ag.iloc[::-1],
            x="n_lancamentos",
            y="cluster",
            orientation="h",
            text="n_lancamentos",
            color="cluster",
            labels={"n_lancamentos": "Lançamentos", "cluster": ""},
        )
        fig.update_layout(showlegend=False, height=350,
                          margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    with col_t:
        st.dataframe(
            ag[["cluster", "n_lancamentos", "pct"]].rename(columns={
                "cluster": "Motivo", "n_lancamentos": "Qtd", "pct": "%"
            }),
            hide_index=True, use_container_width=True,
        )

# ---- Tab 2: Top produtos ----
with tab2:
    n_top = st.slider("Top N produtos", 5, 30, 15)
    ag_p = (df_f.groupby("produto", dropna=False)
            .agg(n_lancamentos=("produto", "size"),
                 motivo_top=("cluster", lambda s: s.value_counts().index[0]))
            .reset_index()
            .sort_values("n_lancamentos", ascending=False)
            .head(n_top))

    fig = px.bar(
        ag_p.iloc[::-1],
        x="n_lancamentos",
        y="produto",
        orientation="h",
        text="n_lancamentos",
        color="motivo_top",
        labels={"n_lancamentos": "Lançamentos", "produto": "", "motivo_top": "Motivo"},
    )
    fig.update_layout(height=max(350, 25 * n_top), margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 3: Tendência ----
with tab3:
    df_t = df_f.copy()
    df_t["data_d"] = df_t["data"].dt.date
    ag_t = df_t.groupby("data_d").size().reset_index(name="n")

    fig = px.line(
        ag_t,
        x="data_d",
        y="n",
        markers=True,
        labels={"data_d": "Data", "n": "Lançamentos"},
    )
    fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    # Por unidade (se Todas selecionada)
    if unidade_sel == "Todas":
        df_t2 = df_t.groupby(["data_d", "unidade"]).size().reset_index(name="n")
        fig2 = px.line(
            df_t2, x="data_d", y="n", color="unidade", markers=True,
            labels={"data_d": "Data", "n": "Lançamentos", "unidade": "Unidade"},
        )
        fig2.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

# ---- Tab 4: Lançamentos detalhados ----
with tab4:
    busca = st.text_input("🔍 Buscar produto, motivo ou observação",
                           placeholder="Ex: pão, geladeira, cliente")
    df_show = df_f.copy()
    if busca:
        b = _norm(busca)
        mask = (
            df_show["produto"].astype(str).apply(_norm).str.contains(b, na=False) |
            df_show["motivo"].astype(str).apply(_norm).str.contains(b, na=False) |
            df_show["observacao"].astype(str).apply(_norm).str.contains(b, na=False)
        )
        df_show = df_show[mask]

    df_show = df_show.sort_values("data", ascending=False).copy()
    df_show["data"] = df_show["data"].dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(
        df_show[["data", "unidade", "produto", "qty", "qty_unidade",
                  "cluster", "motivo", "observacao"]].rename(columns={
            "data": "Data", "unidade": "Unidade", "produto": "Produto",
            "qty": "Qty", "qty_unidade": "Un.", "cluster": "Tipo",
            "motivo": "Motivo", "observacao": "Observação",
        }),
        hide_index=True,
        use_container_width=True,
        height=500,
    )
    st.caption(f"Mostrando {len(df_show)} de {len(df_f)} lançamentos do filtro atual.")

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.caption(
    f"📥 Última atualização dos dados: cache de até 10 min · "
    f"Total lançamentos no banco: {len(df):,}".replace(",", ".")
)
