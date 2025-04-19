import requests
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime, timedelta


def get_today_date():
    today=datetime.now()
    return today.strftime("%Y-%m-%d") #Format YYYY-MM-DD

def get_yesterday_date():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d") #Format YYYY-MM-DD

def get_numberof_games(date):
    date_today=get_today_date()
    nhl_games_url=f"https://api-web.nhle.com/v1/score/{date_today}"
    response=requests.get(nhl_games_url)
    data=response.json()
    game_ids = [game["id"] for game in data["games"]]
    num_games=len(game_ids)
    return num_games

date_today=get_today_date()
nhl_games_url=f"https://api-web.nhle.com/v1/score/{date_today}"
response=requests.get(nhl_games_url)
data=response.json()

games_info={}

for i, game in enumerate(data.get("games", []), start=1):
    game_data = {}

    # 1. Venue
    game_data["venue"] = game.get("venue", {}).get("default", None)

    # 2. TV Broadcast (id == 385)
    broadcast_385 = next((b for b in game.get("tvBroadcasts", []) if b["id"] == 385), {})
    game_data["tv_country_code"] = broadcast_385.get("countryCode")
    game_data["tv_network"] = broadcast_385.get("network")

    # 3. Away Team Info
    away_team = game.get("awayTeam", {})
    game_data["away_team_name"] = f"{away_team.get('abbrev')} {away_team.get('name', {}).get('default')}"
    game_data["away_team_record"] = away_team.get("record")
    odds_away = next((o for o in away_team.get("odds", []) if o["providerId"] == 9), {})
    game_data["away_team_odds"] = odds_away.get("value")

    # 4. Home Team Info
    home_team = game.get("homeTeam", {})
    game_data["home_team_name"] = f"{home_team.get('abbrev')} {home_team.get('name', {}).get('default')}"
    game_data["home_team_record"] = home_team.get("record")
    odds_home = next((o for o in home_team.get("odds", []) if o["providerId"] == 9), {})
    game_data["home_team_odds"] = odds_home.get("value")

    # 5. Series Status
    game_data["series_status"] = game.get("seriesStatus", {})

    # 6. Team Leaders
    game_data["team_leaders"] = game.get("teamLeaders", [])

    # Store each game in the dictionary using a dynamic key
    games_info[f"game_{i}"] = game_data


def format_email(games_info):
    email_body = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
        .game-preview {{ border: 1px solid #ccc; padding: 16px; margin-bottom: 20px; border-radius: 10px; background-color: #f9f9f9; }}
        .team-block {{ display: flex; justify-content: space-between; }}
        .team {{ width: 48%; }}
        .team-name {{ font-size: 1.2em; font-weight: bold; }}
        .record, .odds {{ font-size: 0.95em; color: #555; }}
        .vs {{ text-align: center; font-weight: bold; margin: 10px 0; }}
        h2 {{ color: #003366; }}
    </style>
</head>
<body>
    <h2>NHL Stanley Cup Playoff Preview – {}</h2>
""".format(datetime.now().strftime('%B %d, %Y'))

    for game_id, game in games_info.items():
        away_name = game.get("away_team_name", "N/A")
        home_name = game.get("home_team_name", "N/A")
        email_body += f"""
        <div class="game-preview">
            <div><strong>Venue:</strong> {game.get("venue", "TBD")}</div>
            <div><strong>TV Broadcast:</strong> {game.get("tv_network", "TBD")} ({game.get("tv_country_code", "")})</div>
            <br/>
            <div class="team-block">
                <div class="team">
                    <div class="team-name">{away_name}</div>
                    <div class="record">Record: {game.get("away_team_record", "N/A")}</div>
                    <div class="odds">Odds: {game.get("away_team_odds", 'N/A')}</div>
                </div>
                <div class="vs">vs</div>
                <div class="team">
                    <div class="team-name">{home_name}</div>
                    <div class="record">Record: {game.get("home_team_record", "N/A")}</div>
                    <div class="odds">Odds: {game.get("home_team_odds", 'N/A')}</div>
                </div>
            </div>
            <br/>
        """

        series = game.get("series_status", {})
        if series:
            top_team = series.get("topSeedTeamAbbrev", "TBD")
            top_wins = series.get("topSeedWins", 0)
            bottom_team = series.get("bottomSeedTeamAbbrev", "TBD")
            bottom_wins = series.get("bottomSeedWins", 0)
            series_round= series.get("seriesTitle", "TBD")
            email_body += f"<div><strong>Series Status:</strong> {series_round} - {top_team} {top_wins} vs {bottom_team} {bottom_wins}</div>"

        # Team leaders section
        leaders = game.get("team_leaders", [])
        if leaders:
            email_body += "<br/><div><strong>Top Performers from the Regular Season:</strong><ul>"
            for leader in leaders:
                first_name = leader.get("firstName", {}).get("default", "")
                last_name = leader.get("lastName", {}).get("default", "")
                name = f"{first_name} {last_name}".strip()
                stat = leader.get("value", "")
                stat_label = leader.get("category", {})
                team_abbrev = leader.get("teamAbbrev",{})
                email_body += f"<li>{name} {team_abbrev} - {stat} {stat_label}</li>"
            email_body += "</ul></div>"

        email_body += "</div>"

    email_body += "</body></html>"
    return email_body





from config import EMAIL_PASSWORD
EMAIL_ADDRESS = "nsofianakos@gmail.com"
EMAIL_PASSWORD = EMAIL_PASSWORD


def send_email(email_content, recipient_list):
    msg = EmailMessage()
    #msg.set_content(email_content)
    msg["Subject"] = "NHL Stanley Cup Preview for Today's Games"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(recipient_list)
    
    # Add the HTML content as the alternative part of the message
    msg.add_alternative(email_content, subtype='html')

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        try:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("Email successfully sent!")
        except Exception as e:
            print(f"Error sending email: {e}")


# Example usage

# Format the email content
email_content = format_email(games_info)

# List of recipients
recipient_list = ['nsofianakos@gmail.com', 'c2lns4@aol.com','']

# Send the email
send_email(email_content, recipient_list)









