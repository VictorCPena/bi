import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import re

# Função para formatar faixas numéricas ou valores monetários
def format_range(value, is_currency=False):
    if isinstance(value, str):
        match = re.search(r"lower_bound:\s*([\d.]+),\s*upper_bound:\s*([\d.]+)", value)
        if match:
            lower = match.group(1)
            upper = match.group(2)
            try:
                lower_num = int(lower)
                upper_num = int(upper)
                lower_fmt = f"{lower_num:,}".replace(',', '.')
                upper_fmt = f"{upper_num:,}".replace(',', '.')
            except Exception:
                lower_fmt = lower
                upper_fmt = upper
            if is_currency:
                return f"R$ {lower_fmt} a R$ {upper_fmt}"
            else:
                return f"{lower_fmt} a {upper_fmt}"
        else:
            match2 = re.search(r"lower_bound:\s*([\d.]+)", value)
            if match2:
                lower = match2.group(1)
                try:
                    lower_num = int(lower)
                    lower_fmt = f"{lower_num:,}".replace(',', '.')
                except Exception:
                    lower_fmt = lower
                if is_currency:
                    return f"R$ {lower_fmt}"
                else:
                    return lower_fmt
    return value

# Função para extrair o valor numérico de 'spend'
def parse_spend(value):
    if isinstance(value, str) and "lower_bound:" in value:
        match = re.search(r"lower_bound:\s*([\d.]+)", value)
        if match:
            try:
                return float(match.group(1))
            except:
                return 0.0
        else:
            return 0.0
    else:
        try:
            return float(value)
        except:
            return 0.0

# Leitura dos dados
df_roberto = pd.read_csv("data/roberto-claudio.csv")
df_gov_ce = pd.read_csv("data/gov-ce.csv")
gov_alece = pd.read_csv("data/alece.csv")

df_roberto["candidato"] = "roberto"
df_gov_ce["candidato"] = "governo do estado do ceará"
gov_alece["candidato"] = "Assembleia Legislativa"

df_roberto["arquivo_base"] = "roberto-claudio"
df_gov_ce["arquivo_base"] = "gov-ce"
gov_alece["arquivo_base"] = "alece"

df_all = pd.concat([df_roberto, df_gov_ce, gov_alece])

# Dicionário para cores personalizadas dos candidatos
cores = {
    "roberto": "#fff89a",
    "Assembleia Legislativa": "rgb(86, 167, 178)",
    "governo do estado do ceará": "#1b3b1a"
}

# Inicialização do app com tema Bootstrap COSMO
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.COSMO],
    suppress_callback_exceptions=True
)
app.title = "Anúncios de Candidatos"
server = app.server

app.layout = html.Div([
    dcc.Store(id="selected-candidate"),
    html.Div([
        html.H1("Selecione um Candidato", className="header-title", 
                style={"textAlign": "center", "marginTop": "30px"}),
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    dbc.Button("Roberto Cláudio", id="btn-roberto", color="warning",
                               className="btn-lg candidate-button w-100 mb-2"),
                    md=4
                ),
                dbc.Col(
                    dbc.Button("Assembleia Legislativa", id="btn-alece", color="info",
                               className="btn-lg candidate-button w-100 mb-2"),
                    md=4
                ),
                dbc.Col(
                    dbc.Button("Governo do Estado do Ceará", id="btn-governo", color="success",
                               className="btn-lg candidate-button w-100 mb-2"),
                    md=4
                ),
            ], justify="center")
        ], className="my-4"),
        html.Div(id="candidate-details", className="rounded-container")
    ], className="container container-rounded")
])

# Callback para atualizar o candidato selecionado
@app.callback(
    Output("selected-candidate", "data"),
    Input("btn-roberto", "n_clicks"),
    Input("btn-alece", "n_clicks"),
    Input("btn-governo", "n_clicks"),
    prevent_initial_call=True
)
def update_selected(n1, n2, n3):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn_id == "btn-roberto":
        return "roberto"
    elif btn_id == "btn-alece":
        return "Assembleia Legislativa"
    elif btn_id == "btn-governo":
        return "governo do estado do ceará"
    return dash.no_update

# Callback para exibir detalhes do candidato e gráficos
@app.callback(
    Output("candidate-details", "children"),
    Output("candidate-details", "style"),
    Input("selected-candidate", "data")
)
def show_candidate_details(candidato):
    if not candidato:
        return "", {"display": "none"}
    
    df = df_all[df_all["candidato"] == candidato].copy()
    df["status"] = df["ad_delivery_stop_time"].isna().map({True: "Ativo", False: "Inativo"})
    total = len(df)
    ativos = len(df[df["status"] == "Ativo"])
    inativos = total - ativos

    # Gráfico de anúncios ao longo do tempo
    fig_temporal = px.histogram(
        df,
        x="ad_creation_time",
        color="status",
        barmode="group",
        title="Quantidade de Anúncios ao Longo do Tempo",
        template="plotly_white"
    )
    fig_temporal.update_layout(
        autosize=True,
        font=dict(family="Roboto, sans-serif", size=12, color="#333"),
        paper_bgcolor="#f0f2f5",
        plot_bgcolor="#f0f2f5"
    )
    
    # Gráfico de investimento com pontos e linhas
    df["spend_value"] = df["spend"].apply(parse_spend)
    df["ad_creation_time"] = pd.to_datetime(df["ad_creation_time"], errors='coerce')
    df_invest = df.groupby(df["ad_creation_time"].dt.date)["spend_value"].sum().reset_index()
    df_invest.columns = ["Data", "Investimento_R$"]
    
    fig_invest = px.line(
        df_invest,
        x="Data",
        y="Investimento_R$",
        title="Investimento (R$) ao Longo do Tempo",
        template="plotly_white",
        markers=True
    )
    fig_invest.update_layout(
        autosize=True,
        font=dict(family="Roboto, sans-serif", size=12, color="#333"),
        paper_bgcolor="#f0f2f5",
        plot_bgcolor="#f0f2f5"
    )
    
    # Definindo o caminho da imagem com a extensão correta
    nome_arquivo = df["arquivo_base"].iloc[0]
    ext = "png" if nome_arquivo in ["alece", "gov-ce"] else "jpg"
    caminho_imagem = f"/assets/images/{nome_arquivo}.{ext}"

    # Cartão com informações do candidato
    card = dbc.Card([
        dbc.CardImg(src=caminho_imagem, top=True, className="candidate-img"),
        dbc.CardBody([
            html.H3(candidato.title(), className="card-title"),
            html.P(f"📊 Total de Anúncios: {total}"),
            html.P(f"✅ Ativos: {ativos}"),
            html.P(f"🛑 Inativos: {inativos}"),
            html.Hr(),
            html.Label("Filtrar anúncios por status:"),
            dcc.RadioItems(
                id="radio-status",
                options=[
                    {"label": "Ativo", "value": "Ativo"},
                    {"label": "Inativo", "value": "Inativo"}
                ],
                value="Ativo",
                inline=True
            ),
            html.Br(),
            html.Label("Ver detalhes de um anúncio específico:"),
            dcc.Dropdown(id="dropdown-anuncio", placeholder="Selecione um anúncio"),
            html.Div(id="detalhes-anuncio", style={"marginTop": "20px"})
        ])
    ], className="custom-card mb-4 rounded-container")

    container_style = {
        "display": "block",
        "backgroundColor": cores.get(candidato, "#ffffff"),
        "padding": "20px",
        "borderRadius": "20px",
        "margin": "20px 0"
    }

    # Containers com gráficos responsivos
    card_container = dbc.Container(card, className="mb-4 rounded-container")
    graph_temporal_container = dbc.Container(
        dcc.Graph(figure=fig_temporal, config={'responsive': True}),
        className="mb-4 rounded-container"
    )
    graph_invest_container = dbc.Container(
        dcc.Graph(figure=fig_invest, config={'responsive': True}),
        className="mb-4 rounded-container"
    )
    
    content = html.Div(
        [card_container, graph_temporal_container, graph_invest_container],
        className="graph-area"
    )
    
    return content, container_style

# Callback para atualizar o dropdown com base no status selecionado
@app.callback(
    Output("dropdown-anuncio", "options"),
    Input("radio-status", "value"),
    State("selected-candidate", "data")
)
def update_dropdown_options(selected_status, candidato):
    if not candidato:
        return []
    df = df_all[df_all["candidato"] == candidato]
    if selected_status == "Ativo":
        df = df[df["ad_delivery_stop_time"].isna()]
    else:
        df = df[df["ad_delivery_stop_time"].notna()]
    
    opcoes_dropdown = []
    for idx, row in df.iterrows():
        texto = row.get("ad_creative_bodies")
        texto = texto[:80] if isinstance(texto, str) else "Sem texto disponível"
        opcoes_dropdown.append({"label": f"{texto}...", "value": idx})
    return opcoes_dropdown

# Callback para exibir os detalhes do anúncio selecionado
@app.callback(
    Output("detalhes-anuncio", "children"),
    Input("dropdown-anuncio", "value"),
    State("selected-candidate", "data")
)
def exibir_detalhes_anuncio(selected_idx, candidato):
    if selected_idx is None:
        return ""
    df_candidato = df_all[df_all["candidato"] == candidato]
    try:
        anuncio = df_candidato.loc[selected_idx]
    except Exception as e:
        return html.Div(f"Erro ao encontrar o anúncio (index: {selected_idx}): {e}", style={"color": "red"})
    
    detalhes = [
        html.H5("📰 Detalhes do Anúncio Selecionado:"),
        html.P(f"🆔 ID do Anúncio: {anuncio['ad_archive_id']}"),
        html.P(f"📅 Criado em: {anuncio['ad_creation_time']}")
    ]
    if pd.notnull(anuncio.get("ad_delivery_stop_time")):
        detalhes.append(html.P(f"⏱️ Finalizado em: {anuncio['ad_delivery_stop_time']}"))
    else:
        detalhes.append(html.P("⏱️ Status: Ativo"))
    
    detalhes.append(html.P(f"💬 Texto: {str(anuncio.get('ad_creative_bodies', 'Sem texto disponível'))[:300]}..."))
    
    spend = anuncio.get('spend', 'N/A')
    impressao = anuncio.get('impressions', 'N/A')
    audiencia = anuncio.get('estimated_audience_size', 'N/A')
    
    formatted_spend = format_range(spend, is_currency=True) if isinstance(spend, str) and "lower_bound:" in spend else spend
    formatted_impressao = format_range(impressao) if isinstance(impressao, str) and "lower_bound:" in impressao else impressao
    formatted_audiencia = format_range(audiencia) if isinstance(audiencia, str) and "lower_bound:" in audiencia else audiencia

    detalhes.append(html.P(f"💰 Gasto: {formatted_spend} {anuncio.get('currency', '')}"))
    detalhes.append(html.P(f"👀 Impressões: {formatted_impressao}"))
    detalhes.append(html.P(f"🎯 Público Estimado: {formatted_audiencia}"))
    
    anuncio_url = f"https://www.facebook.com/ads/library/?id={anuncio['ad_archive_id']}"
    detalhes.append(
        html.A(
            dbc.Button("Ver anúncio no Facebook Ads Library", color="primary", className="mt-2"),
            href=anuncio_url,
            target="_blank"
        )
    )
    
    return html.Div(detalhes, style={
        "backgroundColor": "#f8f9fa",
        "padding": "10px",
        "borderRadius": "20px",
        "marginTop": "10px"
    })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=10000)
