from flask import Flask, request, redirect, url_for, render_template
from models import get_session, Player, Round, Match
from pairing import compute_scores, buchholz, find_pairings
import os

app = Flask(__name__)

@app.route("/")
def index():
    sess = get_session()
    players = sess.query(Player).order_by(Player.id).all()
    return render_template("index.html", players=players)

@app.route("/add_player", methods=["POST"])
def add_player():
    name = request.form.get("name")
    team = request.form.get("team") or ""
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

    if m.p2_id is None:
        m.p1_score = 1.0
        m.p2_score = 0.0
        m.finished = True
        sess.commit()
        return redirect(url_for('rounds'))

    m.p1_score = float(request.form.get("p1_score", 0))
    m.p2_score = float(request.form.get("p2_score", 0))
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)