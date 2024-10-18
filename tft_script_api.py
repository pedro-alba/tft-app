import streamlit as st
from pulsefire.clients import RiotAPIClient
import asyncio
import pandas as pd
import plotly.express as px
import random

# Substitute this with your actual API key
API_KEY = "RGAPI-05263a1a-f6a0-4d2c-ba22-5cdf9d6cf5e6"

async def main(players, max_games_per_player=10):
    regiao = "americas"
    historico = {"start": 0, "count": 100}  # Fetching 100 games initially to ensure we get enough data
    
    async with RiotAPIClient(default_headers={"X-Riot-Token": API_KEY}) as client:
        try:
            match_data = []

            async def check_summoner(game_name, tag_line):
                account = await client.get_account_v1_by_riot_id(region=regiao, game_name=game_name, tag_line=tag_line)
                puuid = account["puuid"]

                has_more_matches = True
                start_index = 0
                games_fetched = 0  # Track the number of games fetched for each player
                
                while has_more_matches and games_fetched < max_games_per_player:
                    historico["start"] = start_index
                    tft_match_ids = await client.get_tft_match_v1_match_ids_by_puuid(puuid=puuid, region=regiao, queries=historico)
                    
                    if not tft_match_ids:
                        has_more_matches = False
                        break

                    for match_id in tft_match_ids:
                        if games_fetched >= max_games_per_player:
                            break
                        
                        match_details = await client.get_tft_match_v1_match(id=match_id, region=regiao)
                        game_info = match_details["info"]
                        player_data = next((p for p in game_info["participants"] if p["puuid"] == puuid), None)

                        if player_data and game_info["tft_set_number"] == 12:
                            match_data.append({
                                "game_name": game_name,
                                "tag_line": tag_line,
                                "gold_left": player_data["gold_left"],
                                "last_round": player_data["last_round"],
                                "level": player_data["level"],
                                "placement": player_data["placement"],
                                "players_eliminated": player_data["players_eliminated"],
                                "total_damage_to_players": player_data["total_damage_to_players"],
                                "tft_game_type": game_info["tft_game_type"],
                            })
                            games_fetched += 1

                    start_index += len(tft_match_ids)

            for player in players:
                game_name, tag_line = player.split("#")
                await check_summoner(game_name.strip(), tag_line.strip())

            df = pd.DataFrame(match_data)
            return df

        except Exception as e:
            print(f"Ocorreu um erro: {str(e)}")
            return pd.DataFrame()

# Function to assign random colors to players
def assign_colors(players):
    colors = {}
    for player in players:
        colors[player] = f"#{random.randint(0, 0xFFFFFF):06x}"  # Random hex color
    return colors

# Function to display player stats summary
def display_charts(df, colors):
    st.title("Gráficos de Desempenho dos Jogadores de TFT")

    summary_data = []

    for game_name in df['game_name'].unique():
        player_df = df[df['game_name'] == game_name]

        total_games = len(player_df)
        wins = (player_df['placement'] == 1).sum()
        top_4 = (player_df['placement'] <= 4).sum()
        average_placement = player_df['placement'].mean() if total_games > 0 else 0
        average_gold_left = player_df['gold_left'].mean() if total_games > 0 else 0

        summary_data.append({
            "Player": f"{game_name}",
            "Win Rate (%)": (wins / total_games) * 100 if total_games > 0 else 0,
            "Top 4 (%)": (top_4 / total_games) * 100 if total_games > 0 else 0,
            "Average Gold Left": average_gold_left,
            "Average Placement": average_placement,
        })

    summary_df = pd.DataFrame(summary_data)

    # Create columns for the grid layout
    col1, col2 = st.columns(2)

    # Win Rate
    with col1:
        fig_win_rate = px.bar(summary_df, x='Player', y='Win Rate (%)', title="Win Rate (1º lugar)", color='Player',
                              color_discrete_map=colors)
        st.plotly_chart(fig_win_rate)

    # Top 4 Percentage
    with col1:
        fig_top_4 = px.bar(summary_df, x='Player', y='Top 4 (%)', title="Porcentagem entre os 4 primeiros", color='Player',
                           color_discrete_map=colors)
        st.plotly_chart(fig_top_4)

    # Average Gold Left
    with col2:
        fig_gold_left = px.bar(summary_df, x='Player', y='Average Gold Left', title="Média de Ouro Restante", color='Player',
                               color_discrete_map=colors)
        st.plotly_chart(fig_gold_left)

    # Average Placement
    with col2:
        fig_avg_placement = px.bar(summary_df, x='Player', y='Average Placement', title="Colocação Média", color='Player',
                                   color_discrete_map=colors)
        st.plotly_chart(fig_avg_placement)

# Run the main function and display the summary
if __name__ == "__main__":
    st.title("Análise de Jogadores de TFT")

    players_input = st.text_input("Digite os nomes e tags dos invocadores (separados por vírgula, formato: Nome#Tag)", "El Chefinho#BR1, FropZ#GOAT")
    players = [player.strip() for player in players_input.split(",")]

    max_games = st.number_input("Número máximo de partidas por jogador", min_value=1, value=10)

    if st.button("Buscar Dados"):
        df = asyncio.run(main(players, max_games))
        if not df.empty:
            player_colors = assign_colors(df['game_name'].unique())
            display_charts(df, player_colors)
        else:
            st.warning("Nenhum dado foi encontrado.")
