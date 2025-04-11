import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json
import re

# Função auxiliar para formatar os valores de intervalo
def format_range(value, is_currency=False):
    """
    Converte uma string no formato "lower_bound: X, upper_bound: Y" para um texto legível em português.
    Se não encontrar a faixa completa, tenta extrair apenas o lower_bound e formata-o.
    """
    if isinstance(value, str):
        # Tenta extrair a faixa completa
        match = re.search(r"lower_bound:\s*([\d.]+),\s*upper_bound:\s*([\d.]+)", value)
        if match:
            lower = match.group(1)
            upper = match.group(2)
            try:
                lower_num = int(lower)
                upper_num = int(upper)
                lower_fmt = f"{lower_num:,}".replace(',', '.')
                upper_fmt = f"{upper_num:,}".replace(',', '.')
            except Exception as e:
                lower_fmt = lower
                upper_fmt = upper
            if is_currency:
                return f"R$ {lower_fmt} a R$ {upper_fmt}"
            else:
                return f"{lower_fmt} a {upper_fmt}"
        else:
            # Se não encontrar os dois valores, tenta extrair apenas o lower_bound
            match2 = re.search(r"lower_bound:\s*([\d.]+)", value)
            if match2:
                lower = match2.group(1)
                try:
                    lower_num = int(lower)
                    lower_fmt = f"{lower_num:,}".replace(',', '.')
                except Exception as e:
                    lower_fmt = lower
                if is_currency:
                    return f"R$ {lower_fmt}"
                else:
                    return lower_fmt
    return value

# Carregamento dos dados
df_roberto = pd.read_csv("data/roberto-claudio.csv")
df_gov_ce = pd.read_csv("data/gov-ce.csv")
gov_alece = pd.read_csv("data/alece.csv")

# Configura os dados para cada candidato e anexa a origem do arquivo
df_roberto["candidato"] = "roberto"
df_gov_ce["candidato"] = "governo do estado do ceará"
gov_alece["candidato"] = "Assembleia Legislativa"

df_roberto["arquivo_base"] = "roberto-claudio"
df_gov_ce["arquivo_base"] = "gov-ce"
gov_alece["arquivo_base"] = "alece"

df_all = pd.concat([df_roberto, df_gov_ce, gov_alece])

# Define as cores para cada candidato
cores = {
    "roberto": "#fff89a",
    "Assembleia Legislativa": "rgb(86, 167, 178)",
    "governo do estado do ceará": "#1b3b1a"
}

# Inicializa o app utilizando Bootstrap (e CSS customizado, se desejar, colocando arquivos na pasta assets/)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Anúncios de Candidatos"
server = app.server

# Layout principal do app
app.layout = html.Div([
    dcc.Store(id="selected-candidate"),
    html.Div([
        html.H1("Selecione um Candidato", className="header-title", style={"textAlign": "center", "marginTop": "30px"}),
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    dbc.Button("Roberto Cláudio", id="btn-roberto", color="warning", className="btn-lg w-100 mb-2"),
                    md=4
                ),
                dbc.Col(
                    dbc.Button("Assembleia Legislativa", id="btn-alece", color="info", className="btn-lg w-100 mb-2"),
                    md=4
                ),
                dbc.Col(
                    dbc.Button("Governo do Estado do Ceará", id="btn-governo", color="success", className="btn-lg w-100 mb-2"),
                    md=4
                ),
            ], justify="center")
        ], className="my-4"),
        html.Div(id="candidate-details")
    ])
])

# Callback para definir o candidato selecionado
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

# Callback para exibição dos detalhes e gráficos dos anúncios do candidato selecionado
@app.callback(
    Output("candidate-details", "children"),
    Output("candidate-details", "style"),
    Input("selected-candidate", "data")
)
def show_candidate_details(candidato):
    if not candidato:
        return "", {"display": "none"}
    
    # Filtra os dados pelo candidato e define status (Ativo se não houver data de finalização)
    df = df_all[df_all["candidato"] == candidato].copy()
    df["status"] = df["ad_delivery_stop_time"].isna().map({True: "Ativo", False: "Inativo"})

    total = len(df)
    ativos = len(df[df["status"] == "Ativo"])
    inativos = total - ativos

    # Gráfico: Quantidade de anúncios ao longo do tempo
    fig_temporal = px.histogram(
        df,
        x="ad_creation_time",
        color="status",
        barmode="group",
        title="Quantidade de Anúncios ao Longo do Tempo",
        template="plotly_white"
    )
    
    # Seleciona a imagem do candidato conforme o arquivo_base
    nome_arquivo = df["arquivo_base"].iloc[0]
    caminho_imagem = f"/assets/images/{nome_arquivo}.jpg"

    card = dbc.Card([
        dbc.CardImg(src=caminho_imagem, top=True, style={"maxHeight": "300px", "objectFit": "contain"}),
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
    ], className="custom-card mb-4")
    
    background_color = cores.get(candidato, "#ffffff")
    style = {
        "display": "block",
        "backgroundColor": background_color,
        "padding": "20px",
        "borderRadius": "10px",
        "margin": "20px 0"
    }
    
    # Organiza o layout: card e gráfico temporal em uma linha
    row1 = dbc.Row([
        dbc.Col(card, md=4),
        dbc.Col(dcc.Graph(figure=fig_temporal), md=8)
    ], align="center", className="mb-4")
    
    content = dbc.Container([row1])
    return content, style

# Callback para preencher o dropdown com os anúncios filtrados por status
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
        if not isinstance(texto, str):
            texto = "Sem texto disponível"
        else:
            texto = texto[:80]
        opcoes_dropdown.append({"label": f"{texto}...", "value": idx})
    return opcoes_dropdown

# Callback para exibição dos detalhes do anúncio selecionado
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
    # Exibe "Finalizado em" somente se houver data de finalização; caso contrário, informa "Status: Ativo"
    if pd.notnull(anuncio.get("ad_delivery_stop_time")):
        detalhes.append(html.P(f"⏱️ Finalizado em: {anuncio['ad_delivery_stop_time']}"))
    else:
        detalhes.append(html.P("⏱️ Status: Ativo"))
    
    detalhes.append(html.P(f"💬 Texto: {str(anuncio.get('ad_creative_bodies', 'Sem texto disponível'))[:300]}..."))
    
    # Processamento e formatação dos campos numéricos
    spend = anuncio.get('spend', 'N/A')
    impressao = anuncio.get('impressions', 'N/A')
    audiencia = anuncio.get('estimated_audience_size', 'N/A')
    
    formatted_spend = format_range(spend, is_currency=True) if isinstance(spend, str) and "lower_bound:" in spend else spend
    formatted_impressao = format_range(impressao) if isinstance(impressao, str) and "lower_bound:" in impressao else impressao
    formatted_audiencia = format_range(audiencia) if isinstance(audiencia, str) and "lower_bound:" in audiencia else audiencia

    detalhes.append(html.P(f"💰 Gasto: {formatted_spend} {anuncio.get('currency', '')}"))
    detalhes.append(html.P(f"👀 Impressões: {formatted_impressao}"))
    detalhes.append(html.P(f"🎯 Público Estimado: {formatted_audiencia}"))
    
    # Botão com link para o anúncio no Facebook Ads Library
    anuncio_url = f"https://www.facebook.com/ads/library/?id={anuncio['ad_archive_id']}"
    detalhes.append(
        html.A(
            dbc.Button("Ver anúncio no Facebook Ads Library", color="primary", className="mt-2"),
            href=anuncio_url,
            target="_blank"
        )
    )
    
    # Processamento da distribuição demográfica
    if pd.notnull(anuncio.get("demographic_distribution", None)):
        dist_str = anuncio.get("demographic_distribution", "").strip()
        try:
            # Se a string não inicia com '[', adiciona os colchetes para formar uma lista JSON válida
            if not dist_str.startswith('['):
                dist_str_valid = f"[{dist_str}]"
            else:
                dist_str_valid = dist_str
            dist_list = json.loads(dist_str_valid)
            
            dados = []
            for item in dist_list:
                idade = item.get("age")
                genero = item.get("gender")
                porcentagem = item.get("percentage")
                if idade is not None and genero is not None and porcentagem is not None:
                    genero_traduzido = {
                        "female": "Feminino",
                        "male": "Masculino",
                        "unknown": "Desconhecido"
                    }.get(genero, genero)
                    dados.append({
                        "Idade": idade,
                        "Gênero": genero_traduzido,
                        "Porcentagem": porcentagem
                    })
            
            if not dados:
                raise ValueError("Dados de distribuição vazios após processamento")
            
            # Criação do DataFrame e forçando a conversão para um DataFrame padrão
            df_dist = pd.DataFrame(dados).reset_index(drop=True)
            df_dist = pd.DataFrame(df_dist)  # Força a conversão para DataFrame padrão

            # Converte a coluna "Porcentagem" para numérico
            df_dist["Porcentagem"] = pd.to_numeric(df_dist["Porcentagem"], errors="coerce")
            
            fig_treemap = px.treemap(
                df_dist,
                path=["Idade", "Gênero"],
                values="Porcentagem",
                color="Porcentagem",
                color_continuous_scale="Blues",
                title="Distribuição Demográfica (Idade e Gênero)",
                template="plotly_white"
            )
            detalhes.append(
                html.Div(dcc.Graph(figure=fig_treemap), style={"marginTop": "20px"})
            )
        except Exception as e:
            pass
    
    return html.Div(detalhes, style={
        "backgroundColor": "#f8f9fa",
        "padding": "10px",
        "borderRadius": "10px",
        "marginTop": "10px"
    })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=10000)


    