from models import Player, Match
from itertools import permutations

# Compute current scores

def compute_scores(sess):
    scores = {}
    for m in sess.query(Match).all():
        if m.p1_id:
            scores[m.p1_id] = scores.get(m.p1_id, 0) + (m.p1_score or 0)
        if m.p2_id:
            scores[m.p2_id] = scores.get(m.p2_id, 0) + (m.p2_score or 0)
    return scores

def buchholz(sess, scores):
    out = {}
    for p in sess.query(Player).all():
        opps = []
        for m in sess.query(Match).filter((Match.p1_id==p.id)|(Match.p2_id==p.id)).all():
            opp = m.p2_id if m.p1_id == p.id else m.p1_id
            if opp:
                opps.append(scores.get(opp, 0))
        out[p.id] = sum(opps)
    return out

def have_played_before(sess, a, b):
    return sess.query(Match).filter(
        ((Match.p1_id == a) & (Match.p2_id == b)) |
        ((Match.p1_id == b) & (Match.p2_id == a))
    ).count() > 0

def can_pair(sess,a, b, players):
    if players[a].team == players[b].team:
        return False
    if have_played_before(sess, a, b):
        return False
    return True


def find_pairings(sess):
    players = {p.id: p for p in sess.query(Player).all()}
    ids = list(players.keys())
    scores = compute_scores(sess)
    ids.sort(key=lambda x: (-scores.get(x, 0), -players[x].rating))

    def valid(pairs, bye):
        used = set()
        for a, b in pairs:
            if a in used or b in used:
                return False
            if not can_pair(sess,a, b, players):
                return False
            used.add(a); used.add(b)
        if bye:
            if bye.id in used:
                return False
        return True

    best = None
    for order in permutations(ids):
        ps = list(order)
        pairs = []
        i = 0
        while i < len(ps)-1:
            a, b = ps[i], ps[i+1]
            pairs.append((a, b))
            i += 2
        bye = players[ps[-1]] if len(ps)%2==1 else None

        if valid(pairs, bye):
            best = (pairs, bye)
            break

    if best:
        return True, best[0], best[1]
    return False, [], None
