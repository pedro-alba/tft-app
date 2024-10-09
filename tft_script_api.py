import streamlit as st
from pulsefire.clients import RiotAPIClient
import asyncio
import pandas as pd

# Substitute this with your actual API key
API_KEY = "RGAPI-158464b5-5950-48cc-8bde-a688216cf09f"

async def main(players, num_games):
    regiao = "americas"
    historico = {"start": 0, "count": num_games}  # Number of games to fetch
    
    async with RiotAPIClient(default_headers={"X-Riot-Token": API_KEY}) as client:
        try:
            match_data = []

            async def check_summoner(game_name, tag_line):
                account = await client.get_account_v1_by_riot_id(region=regiao, game_name=game_name, tag_line=tag_line)
                puuid = account["puuid"]
                tft_match_ids = await client.get_tft_match_v1_match_ids_by_puuid(puuid=puuid, region=regiao, queries=historico)

                for match_id in tft_match_ids:
                    match_details = await client.get_tft_match_v1_match(id=match_id, region=regiao)
                    game_info = match_details["info"]
                    player_data = next((p for p in game_info["participants"] if p["puuid"] == puuid), None)
                    
                    if player_data:
                        match_data.append({
                            "game_name": game_name,
                            "tag_line": tag_line,
                            "gold_left": player_data["gold_left"],
                            "last_round": player_data["last_round"],
                            "level": player_data["level"],
                            "placement": player_data["placement"],
                            "players_eliminated": player_data["players_eliminated"],
                            "time_eliminated": player_data["time_eliminated"],
                            "total_damage_to_players": player_data["total_damage_to_players"],
                            "tft_game_type": game_info["tft_game_type"],
                            "game_length": game_info["game_length"],
                            "game_datetime": game_info["game_datetime"],
                            "tft_set_number": game_info["tft_set_number"]
                        })
                    else:
                        print("Dados do jogador não encontrados na partida.")

            for player in players:
                game_name, tag_line = player.split("#")
                await check_summoner(game_name.strip(), tag_line.strip())

            df = pd.DataFrame(match_data)
            return df

        except Exception as e:
            print(f"Ocorreu um erro: {str(e)}")
            return pd.DataFrame()

# Function to display player stats summary
def display_summary(df):
    st.title("Resumo das Estatísticas dos Jogadores")

    # Create a summary DataFrame for each player
    summary_data = []

    for game_name in df['game_name'].unique():
        player_df = df[df['game_name'] == game_name]
        
        # Calculate summary statistics
        total_games = len(player_df)
        average_placement = player_df['placement'].mean() if total_games > 0 else 0
        average_gold_left = player_df['gold_left'].mean() if total_games > 0 else 0
        total_damage = player_df['total_damage_to_players'].sum() if total_games > 0 else 0

        summary_data.append({
            "Player": f"{game_name}",
            "Total Games": total_games,
            "Average Placement": average_placement,
            "Average Gold Left": average_gold_left,
            "Total Damage": total_damage,
        })

    summary_df = pd.DataFrame(summary_data)

    # Display the summary DataFrame
    st.dataframe(summary_df)

# Run the main function and display the summary
if __name__ == "__main__":
    st.title("Análise de Jogadores de TFT")

    # Input for player names in the format Name#Tag
    players_input = st.text_input("Digite os nomes e tags dos invocadores (separados por vírgula, formato: Nome#Tag)", "El Chefinho#BR1, FropZ#GOAT")
    players = [player.strip() for player in players_input.split(",")]

    # Input for number of games to fetch
    num_games = st.number_input("Número de partidas a buscar", min_value=1, value=5)

    if st.button("Buscar Dados"):
        # Run the data collection asynchronously
        df = asyncio.run(main(players, num_games))
        if not df.empty:
            display_summary(df)
        else:
            st.warning("Nenhum dado foi encontrado.")
