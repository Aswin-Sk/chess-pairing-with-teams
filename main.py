from flask import Flask, request, redirect, url_for, render_template
from models import get_session, Player, Round, Match
from pairing import compute_scores, buchholz, find_pairings
import os
from io import StringIO
import csv


app = Flask(__name__)

TEAMS = ["Reindeer Rangers", "Elven Strikers", "Sleigh Sprinters", "Snow Titans"]
@app.route("/")
def index():
    sess = get_session()
    players = sess.query(Player).order_by(Player.id).all()
    return render_template("index.html", players=players, teams=TEAMS)

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name")
    team = request.form.get("team") or "None" 
    rating = request.form.get("rating")
    try:
        rating = int(rating) if rating else 1200
    except:
        rating = 1200
    sess = get_session()
    p = Player(name=name, team=team, rating=rating)
    sess.add(p)
    sess.commit()
    return redirect(url_for('index'))

@app.route("/start_round", methods=["POST"])
def start_round():
    sess = get_session()
    last = sess.query(Round).order_by(Round.number.desc()).first()
    next_num = (last.number + 1) if last else 1
    rnd = Round(number=next_num)
    sess.add(rnd)
    sess.commit()

    success, pairs, bye = find_pairings(sess)

    if not success:
        return "Unable to find valid pairings without team clashes or repeat matches.", 400

    for a, b in pairs:
        sess.add(Match(round_id=rnd.id, p1_id=a, p2_id=b))
    if bye:
        sess.add(Match(round_id=rnd.id, p1_id=bye.id, p2_id=None))
    sess.commit()
    return redirect(url_for('rounds'))

@app.route("/rounds")
def rounds():
    sess = get_session()
    try:
        rounds = sess.query(Round).order_by(Round.number).all()
        all_matches = sess.query(Match).all()

        matches = {}
        for r in rounds:
            matches[r.id] = [m for m in all_matches if m.round_id == r.id]

        return render_template("rounds.html", rounds=rounds, matches=matches)
    finally:
        sess.close()

@app.route("/report/<int:match_id>", methods=["POST"])
def report_result(match_id):
    sess = get_session()
    m = sess.query(Match).get(match_id)
    if not m:
        return "Match not found", 404

    # --- Handle BYE Matches (Unchanged) ---
    if m.p2_id is None:
        m.p1_score = 1.0
        m.p2_score = 0.0
        m.finished = True
        sess.commit()
        return redirect(url_for('rounds'))

    # --- NEW LOGIC: Handle Combined Result Dropdown ---
    # The dropdown sends a single string like "1.0-0.0" in the 'result' field.
    result_str = request.form.get("result") 
    
    if not result_str:
        return "Match result not provided.", 400

    try:
        p1_score_str, p2_score_str = result_str.split('-')
        
        m.p1_score = float(p1_score_str)
        m.p2_score = float(p2_score_str)
        
    except ValueError:
        return "Invalid result format submitted. Expected format: 'X.X-Y.Y'.", 400

    m.finished = True
    sess.commit()
    return redirect(url_for('rounds'))

@app.route("/standings")
def standings():
    sess = get_session()
    scores = compute_scores(sess)
    buch = buchholz(sess, scores)
    players = sess.query(Player).all()
    rows = sorted([(p, scores.get(p.id,0.0), buch.get(p.id,0.0)) for p in players], key=lambda t: (-t[1], -t[2], -t[0].rating))
    return render_template("standings.html", rows=rows)

@app.route("/reset", methods=["POST"])
def reset():
    sess = get_session()
    sess.query(Match).delete(); sess.query(Round).delete(); sess.query(Player).delete()
    sess.commit()
    return redirect(url_for('index'))

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file and file.filename.endswith('.csv'):
        csv_data = file.read().decode('utf-8')
        
        f = StringIO(csv_data)
        reader = csv.reader(f)
        
        next(reader, None) 

        sess = get_session()
        new_players = []
        
        # Expecting CSV columns: Name, Team, Rating
        for row in reader:
            if len(row) < 3:
                continue # Skip malformed rows
            
            name = row[0].strip()
            team = row[1].strip() or "None"
            
            try:
                rating = int(row[2].strip())
            except ValueError:
                rating = 1200
            
            if team not in TEAMS and team != 'None':
                 team = "None" 

            p = Player(name=name, team=team, rating=rating)
            new_players.append(p)

        sess.bulk_save_objects(new_players)
        sess.commit()
        return redirect(url_for('index'))
    
    return "Invalid file format. Please upload a CSV.", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)