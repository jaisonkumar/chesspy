import requests
import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend for Flask
import matplotlib.pyplot as plt
import calendar
from flask import Flask, request, render_template, send_from_directory
import os
import json
from collections import defaultdict
from datetime import datetime, timezone

app = Flask(__name__)

# Register the filter
@app.template_filter('datetimeformat')
def datetimeformat(value):
    """Format Unix timestamp to datetime string."""
    if isinstance(value, int):  # Check if value is a Unix timestamp (integer)
        try:
            # Convert to datetime only if the timestamp is valid
            return datetime.utcfromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError):
            return ""  # Return an empty string instead of "Invalid timestamp"
    return value  # If not a timestamp, return the original value
if not os.path.exists("static"):
    os.makedirs("static")

def apply_light_mode():
    """Apply light mode styling to Matplotlib."""
    plt.style.use("ggplot")  # Light theme for Matplotlib
    plt.rcParams.update({
        "axes.facecolor": "#f0f0f0",       # Light background
        "axes.edgecolor": "#333333",       # Dark axes
        "axes.labelcolor": "#333333",      # Dark text
        "xtick.color": "#333333",          # Dark x-tick labels
        "ytick.color": "#333333",          # Dark y-tick labels
        "text.color": "#333333",           # Dark text
        "grid.color": "#DDDDDD",           # Light grid lines
        "figure.facecolor": "#f0f0f0",     # Light figure background
        "figure.edgecolor": "#f0f0f0"      # Ensure figure has the same background
    })

def add_box_around_plot():
    """Add a box around the plot."""
    ax = plt.gca()  # Get current axes
    for spine in ax.spines.values():
        spine.set_edgecolor('black')  # Set box color to black
        spine.set_linewidth(2)  # Set line width for the box

def fetch_lichess_data(username):
    """Fetch user data from Lichess API."""
    url = f"https://lichess.org/api/user/{username}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

def fetch_rating_history(username):
    """Fetch user's rating history from Lichess API."""
    url = f"https://lichess.org/api/user/{username}/rating-history"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

def fetch_tournament_data(username, nb=10, performance=True):
    """Fetch tournaments played by a user from Lichess API."""
    url = f"https://lichess.org/api/user/{username}/tournament/played"
    params = {
        "nb": nb,  # Maximum number of tournaments to fetch
        "performance": performance  # Include player performance rating
    }
    response = requests.get(url, params=params, stream=True)  # Enable streaming
    if response.status_code != 200:
        return None

    tournament_data = []
    for line in response.iter_lines():
        if line:
            try:
                # Parse each line as JSON directly
                tournament_data.append(json.loads(line.decode('utf-8')))  # Decode and load the JSON
            except ValueError:
                continue  # Skip lines that aren't valid JSON

    return tournament_data

def generate_results_chart(data):
    """Generate pie chart for game results."""
    apply_light_mode()  # Apply light mode styling
    
    labels = ["Wins", "Losses", "Draws", "Total Games"]
    wins = data["count"].get("win", 0)
    losses = data["count"].get("loss", 0)
    draws = data["count"].get("draw", 0)
    total_games = wins + losses + draws
    values = [wins, losses, draws, total_games]
    colors = ["#1E88E5", "#D32F2F", "#FBC02D", "#7E57C2"]  # Adjusted for light background

    plt.figure(figsize=(5, 5))
    wedges, texts, autotexts = plt.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140)
    
    # Adding value labels to the pie chart
    for i, a in enumerate(autotexts):
        a.set_text(f"{values[i]} ({a.get_text()})")

    plt.title(f"Game Results Distribution (Total: {total_games})", color="black")
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Add box around the plot
    add_box_around_plot()

    plt.savefig("static/results_chart.png", facecolor="#f0f0f0")
    plt.close()

def generate_playtime_chart(data):
    """Generate bar chart for playtime."""    
    apply_light_mode()  # Apply light mode styling
    
    labels = ["Total Playtime (hours)", "TV Playtime (hours)"]
    values = [data["playTime"]["total"] / 3600, data["playTime"]["tv"] / 3600]
    colors = ["#03DAC6", "#BB86FC"]

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=colors)
    plt.ylabel("Hours", color="black")
    plt.title("Playtime Distribution", color="black")
    
    # Add value labels to the bars
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom', color="black")

    # Add box around the plot
    add_box_around_plot()

    plt.tight_layout()
    plt.savefig("static/playtime_chart.png", facecolor="#f0f0f0")
    plt.close()

def generate_win_loss_chart(data):
    """Generate bar chart for Wins vs. Losses with Total Games."""    
    apply_light_mode()  # Apply light mode styling
    
    wins = data["count"].get("win", 0)
    losses = data["count"].get("loss", 0)
    total_games = wins + losses + data["count"].get("draw", 0)
    labels = ["Wins", "Losses", "Total Games"]
    values = [wins, losses, total_games]
    colors = ["#4CAF50", "#FF6347", "#FF914D"]  # Green for wins, Red for losses, Orange for total games

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=colors)
    plt.ylabel("Games", color="black")
    plt.title(f"Win/Loss Comparison (Total: {total_games})", color="black")

    # Add value labels to the bars
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{bar.get_height()}', ha='center', va='bottom', color="black")

    # Add box around the plot
    add_box_around_plot()

    plt.tight_layout()
    plt.savefig("static/win_loss_chart.png", facecolor="#f0f0f0")
    plt.close()

def generate_rating_chart(rating_data):
    """Generate line chart for Blitz and Rapid rating history."""
    if not rating_data:
        return

    blitz_points = []
    rapid_points = []
    
    for category in rating_data:
        if category["name"] == "Blitz":
            blitz_points = category["points"]
        elif category["name"] == "Rapid":
            rapid_points = category["points"]

    if not blitz_points and not rapid_points:
        return

    # Group points by month and take the last rating for each month for both Blitz and Rapid
    monthly_ratings_blitz = defaultdict(list)
    monthly_ratings_rapid = defaultdict(list)

    for p in blitz_points:
        month_year = f"{calendar.month_name[p[1]]} {p[0]}"  # Format "Month Year"
        monthly_ratings_blitz[month_year].append(p[3])

    for p in rapid_points:
        month_year = f"{calendar.month_name[p[1]]} {p[0]}"  # Format "Month Year"
        monthly_ratings_rapid[month_year].append(p[3])

    # Take the last rating of each month for both Blitz and Rapid
    dates_blitz = list(monthly_ratings_blitz.keys())
    ratings_blitz = [monthly_ratings_blitz[month][-1] for month in dates_blitz]  # Get last rating for the month

    dates_rapid = list(monthly_ratings_rapid.keys())
    ratings_rapid = [monthly_ratings_rapid[month][-1] for month in dates_rapid]  # Get last rating for the month

    # Combine and plot both Blitz and Rapid ratings in the same graph
    plt.figure(figsize=(8, 4))
    plt.plot(dates_blitz, ratings_blitz, marker="o", linestyle="-", color="blue", markersize=6, linewidth=2, label="Blitz")
    plt.plot(dates_rapid, ratings_rapid, marker="o", linestyle="-", color="green", markersize=6, linewidth=2, label="Rapid")
    plt.xticks(rotation=45, fontsize=10)
    plt.ylabel("Rating", color="black")
    plt.title("Blitz and Rapid Rating History", color="black")
    
    # Add box around the plot
    add_box_around_plot()

    plt.tight_layout()  # Adjust spacing to prevent clipping
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.savefig("static/rating_history_chart.png", facecolor="#f0f0f0")
    plt.close()

def generate_rating_extremes_chart(rating_data):
    """Generate a grouped bar chart for the highest and lowest ratings."""    
    if not rating_data:
        return
    
    blitz_points = []
    rapid_points = []
    
    for category in rating_data:
        if category["name"] == "Blitz":
            blitz_points = category["points"]
        elif category["name"] == "Rapid":
            rapid_points = category["points"]

    # Handle missing Blitz and Rapid points
    if blitz_points:
        highest_blitz = max([p[3] for p in blitz_points])
        lowest_blitz = min([p[3] for p in blitz_points])
    else:
        highest_blitz = lowest_blitz = 0  # Set default if no Blitz data

    if rapid_points:
        highest_rapid = max([p[3] for p in rapid_points])
        lowest_rapid = min([p[3] for p in rapid_points])
    else:
        highest_rapid = lowest_rapid = 0  # Set default if no Rapid data

    # Plotting the highest and lowest ratings for both Blitz and Rapid as grouped bars
    labels = ['Blitz', 'Rapid']
    highest_values = [highest_blitz, highest_rapid]
    lowest_values = [lowest_blitz, lowest_rapid]

    x = range(len(labels))  # X positions for the groups

    plt.figure(figsize=(8, 5))
    bar_width = 0.35  # Width of the bars
    plt.bar(x, highest_values, bar_width, label='Highest Rating', color="#4CAF50")
    plt.bar([p + bar_width for p in x], lowest_values, bar_width, label='Lowest Rating', color="#FF6347")

    plt.xticks([p + bar_width / 2 for p in x], labels)
    plt.ylabel("Rating", color="black")
    plt.title("Highest and Lowest Ratings (Blitz & Rapid)", color="black")
    
    # Add value labels to the bars
    for i, v in enumerate(highest_values):
        plt.text(x[i], v + 10, str(v), ha='center', va='bottom', color="black")
    for i, v in enumerate(lowest_values):
        # Fix the index error here by ensuring the index is valid
        plt.text(x[i] + bar_width, v + 10, str(v), ha='center', va='bottom', color="black")

    # Add box around the plot
    add_box_around_plot()

    plt.tight_layout()
    plt.legend()
    plt.savefig("static/rating_extremes_chart.png", facecolor="#f0f0f0")
    plt.close()


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    data = None
    rating_data = None
    tournament_data = None

    if request.method == "POST":
        username = request.form["username"]
        data = fetch_lichess_data(username)
        if data is None:
            error = "Player not found or invalid username."
        else:
            rating_data = fetch_rating_history(username)
            tournament_data = fetch_tournament_data(username)
            if rating_data:
                generate_rating_chart(rating_data)
                generate_rating_extremes_chart(rating_data)
            if data:
                generate_results_chart(data)
                # Removed playtime chart generation here
                generate_win_loss_chart(data)
                
    return render_template("index.html", data=data, rating_data=rating_data, tournament_data=tournament_data, error=error)

if __name__ == "__main__":
    app.run(debug=True)
