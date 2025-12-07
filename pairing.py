from models import Player, Match

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
    # Prefetch matches to avoid N+1 query problem
    all_matches = sess.query(Match).all()
    p_map = {p.id: p for p in sess.query(Player).all()}
    
    # Build adjacency list
    played = {pid: [] for pid in p_map}
    for m in all_matches:
        if m.p1_id and m.p2_id:
            played[m.p1_id].append(m.p2_id)
            played[m.p2_id].append(m.p1_id)

    for pid in p_map:
        opp_scores = [scores.get(oid, 0) for oid in played.get(pid, [])]
        out[pid] = sum(opp_scores)
    return out

def find_pairings(sess):
    # 1. Fetch all data upfront to minimize DB access
    players = {p.id: p for p in sess.query(Player).all()}
    ids = list(players.keys())
    scores = compute_scores(sess)
    
    # 2. Build a set of existing matches for O(1) lookups
    # Format: frozenset({p1_id, p2_id})
    played_pairs = set()
    for m in sess.query(Match).all():
        if m.p1_id and m.p2_id:
            played_pairs.add(frozenset([m.p1_id, m.p2_id]))

    # 3. Sort players: Higher score first, then higher rating
    ids.sort(key=lambda x: (-scores.get(x, 0), -players[x].rating))

    # Helper to check validity without DB hits
    def is_valid_pair(a, b):
        # Team constraint
        if players[a].team and players[b].team and players[a].team == players[b].team:
            return False
        # Repeat match constraint
        if frozenset([a, b]) in played_pairs:
            return False
        return True

    # 4. Recursive Backtracking Solver
    memo = {}

    def solve(player_pool):
        # Convert list to tuple for dictionary key (memoization)
        pool_key = tuple(player_pool)
        if pool_key in memo:
            return memo[pool_key]

        # Base case: No players left
        if not player_pool:
            return []

        # Base case: 1 player left (Bye)
        if len(player_pool) == 1:
            return [(player_pool[0], None)]

        p1 = player_pool[0]
        
        # Try to pair p1 with the next best available player
        for i in range(1, len(player_pool)):
            p2 = player_pool[i]
            
            if is_valid_pair(p1, p2):
                # Construct remaining list excluding p1 and p2
                remaining = player_pool[1:i] + player_pool[i+1:]
                
                # Recurse
                result = solve(remaining)
                
                if result is not None:
                    # Found a valid path! Bubble it up.
                    final_res = [(p1, p2)] + result
                    memo[pool_key] = final_res
                    return final_res
        
        # If we are here, p1 cannot pair with anyone in the current pool.
        # In a strict system, we might backtrack. 
        # For simplicity/robustness: if we have an odd number, maybe p1 gets the bye?
        # This branch handles the case where p1 is forced to be the Bye 
        # (only if length is odd and we haven't found a match).
        if len(player_pool) % 2 == 1:
             # Try making p1 the bye and solving for the rest
             remaining = player_pool[1:]
             result = solve(remaining)
             if result is not None:
                 final_res = [(p1, None)] + result
                 memo[pool_key] = final_res
                 return final_res

        # No solution found for this branch
        memo[pool_key] = None
        return None

    # Run the solver
    pairs_list = solve(ids)

    if pairs_list:
        final_pairs = []
        bye_player = None
        for p1, p2 in pairs_list:
            if p2 is None:
                bye_player = players[p1]
            else:
                final_pairs.append((p1, p2))
        return True, final_pairs, bye_player
    
    return False, [], None