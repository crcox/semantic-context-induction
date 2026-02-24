#!/usr/bin/env python3
"""
make_pairs_120x2.py

Constructs a 120-trial design for 120 items where each item appears exactly 2 times.
Constraints satisfied:
- Global total order by size (acyclic). All pairs are oriented larger -> smaller.
- Global total order by danger (acyclic). Used to label concordance.
- Four conceptual trial types (30 trials each):
    1) L-L  (both living)
    2) L>N  (larger = living, smaller = nonliving)
    3) N>L  (larger = nonliving, smaller = living)
    4) N-N  (both nonliving)
- In EACH of the four types: 15 danger-concordant, 15 danger-discordant.
- Each of the 120 items appears EXACTLY twice across all trials.
- No repeated pairs.

Outputs:
- A master CSV with all 120 directed pairs (first = larger).
- Two counterbalanced lists (Version A and B) with left/right assignment balanced within each type.
"""

import csv
import argparse
import random
from collections import defaultdict

# ----------------------------
# I/O and basic utilities
# ----------------------------

def load_items(csv_path):
    rows = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "object": r["object"],
                "classification": r["classification"].strip().lower(),
                "size_rank": int(r["size_rank"]),
                "danger_rank": int(r["danger_rank"]),
            })
    return rows

def validate_input(rows):
    # Expect exactly 120 items
    assert len(rows) == 120, "CSV must contain exactly 120 rows (items)."
    # Expect 60 living and 60 nonliving (for the 4x30 block split)
    classes = [r["classification"] for r in rows]
    assert classes.count("living") == 60 and classes.count("nonliving") == 60, \
        "Must have exactly 60 living and 60 nonliving items."

    # size_rank and danger_rank must be permutations of 1..120
    size_ranks = sorted(r["size_rank"] for r in rows)
    danger_ranks = sorted(r["danger_rank"] for r in rows)
    assert size_ranks == list(range(1, 121)), "size_rank must be a permutation of 1..120."
    assert danger_ranks == list(range(1, 121)), "danger_rank must be a permutation of 1..120."

def index_by_name(rows):
    return {r["object"]: r for r in rows}

def split_classes(rows):
    L = [r for r in rows if r["classification"] == "living"]
    N = [r for r in rows if r["classification"] == "nonliving"]
    return L, N

def is_larger(a, b):
    """True if a is larger than b by the global size order."""
    return a["size_rank"] > b["size_rank"]

def is_more_dangerous(a, b):
    """True if a is more dangerous than b by the global danger order."""
    return a["danger_rank"] > b["danger_rank"]


# ----------------------------
# Perfect matchings (within)
# ----------------------------

def random_perfect_matching(names, rng):
    """
    Return a random perfect matching on an even-length list of names as a list of pairs (u,v),
    with no orientation yet (unordered). Uses a simple shuffle+pair scheme.
    """
    names = names[:]
    rng.shuffle(names)
    return [(names[i], names[i+1]) for i in range(0, len(names), 2)]

def orient_by_size(pair, obj_idx):
    """Given an unordered pair of names, return (larger, smaller) by size."""
    a, b = pair
    A, B = obj_idx[a], obj_idx[b]
    return (a, b) if is_larger(A, B) else (b, a)

def within_class_block(items, obj_idx, target_concordant=15, max_tries=10000, rng=None):
    """
    Build ONE perfect matching on 'items' (|items|=60, so 30 pairs), then orient by size
    to form a 30-trial within-class block. We random-restart until exactly 15/15
    danger-concordant/discordant is achieved.
    Returns: list of (larger_name, smaller_name), length 30.
    """
    if rng is None:
        rng = random.Random()

    names = [it["object"] for it in items]

    best = None
    for _ in range(max_tries):
        M = random_perfect_matching(names, rng)
        directed = []
        conc = 0
        for u, v in M:
            a, b = orient_by_size((u, v), obj_idx)
            A, B = obj_idx[a], obj_idx[b]
            if is_more_dangerous(A, B):
                conc += 1
            directed.append((a, b))
        if conc == target_concordant:
            return directed
        # Keep closest for fallback (rarely needed)
        if best is None or abs(conc - target_concordant) < best[0]:
            best = (abs(conc - target_concordant), conc, directed)

    # Fallback if exact 15 not found within tries (very unlikely with random restarts)
    return best[2]


# ----------------------------
# Mixed block = one perfect matching LxN
# with four quotas of 15 edges each:
#   1) Llarger & danger-concordant
#   2) Llarger & danger-discordant
#   3) Nlarger & danger-concordant
#   4) Nlarger & danger-discordant
# ----------------------------

def categorize_edge(L_item, N_item):
    """
    Returns category label among:
    'LL_conc'  : size(L)>size(N) and danger(L)>danger(N)
    'LL_disc'  : size(L)>size(N) and danger(L)<danger(N)
    'NL_conc'  : size(N)>size(L) and danger(N)>danger(L)
    'NL_disc'  : size(N)>size(L) and danger(N)<danger(L)
    Note: with strict total orders, size ties cannot occur.
    """
    Llarger = L_item["size_rank"] > N_item["size_rank"]
    if Llarger:
        if L_item["danger_rank"] > N_item["danger_rank"]:
            return "LL_conc"
        else:
            return "LL_disc"
    else:
        if N_item["danger_rank"] > L_item["danger_rank"]:
            return "NL_conc"
        else:
            return "NL_disc"

def build_mixed_matching(L, N, obj_idx, rng, max_attempts=1000):
    """
    Build exactly ONE perfect matching between L and N (so each L and N is used once),
    while meeting the four quotas:
        |LL_conc| = 15, |LL_disc| = 15, |NL_conc| = 15, |NL_disc| = 15
    Returns: list of oriented pairs (larger, smaller) of length 60,
             plus the split into L>N block (30) and N>L block (30).
    """
    L_names = [it["object"] for it in L]
    N_names = [it["object"] for it in N]

    # Precompute all edges by category
    LL_conc = []
    LL_disc = []
    NL_conc = []
    NL_disc = []
    for a in L:
        for b in N:
            cat = categorize_edge(a, b)
            if cat == "LL_conc":
                LL_conc.append((a["object"], b["object"]))
            elif cat == "LL_disc":
                LL_disc.append((a["object"], b["object"]))
            elif cat == "NL_conc":
                NL_conc.append((a["object"], b["object"]))
            else:
                NL_disc.append((a["object"], b["object"]))

    # Quick feasibility checks (enough edges available?)
    if min(len(LL_conc), len(LL_disc), len(NL_conc), len(NL_disc)) < 15:
        raise RuntimeError("Insufficient edges in one or more categories to meet 15/15/15/15 quotas.")

    # Try random greedy assembly with restarts
    for _ in range(max_attempts):
        capL = {name: 1 for name in L_names}
        capN = {name: 1 for name in N_names}

        # Shuffle each pool
        rng.shuffle(LL_conc)
        rng.shuffle(LL_disc)
        rng.shuffle(NL_conc)
        rng.shuffle(NL_disc)

        # We'll interleave categories to reduce dead-ends; try a few random orderings
        cat_orderings = [
            ["LL_conc", "LL_disc", "NL_conc", "NL_disc"],
            ["NL_conc", "NL_disc", "LL_conc", "LL_disc"],
            ["LL_conc", "NL_conc", "LL_disc", "NL_disc"],
            ["LL_disc", "NL_disc", "LL_conc", "NL_conc"],
        ]
        rng.shuffle(cat_orderings)

        success = False
        for order in cat_orderings:
            chosen = { "LL_conc": [], "LL_disc": [], "NL_conc": [], "NL_disc": [] }
            # Local copies
            capL2 = capL.copy()
            capN2 = capN.copy()
            pools = {
                "LL_conc": LL_conc[:],
                "LL_disc": LL_disc[:],
                "NL_conc": NL_conc[:],
                "NL_disc": NL_disc[:],
            }
            # Target per category
            needs = { "LL_conc": 15, "LL_disc": 15, "NL_conc": 15, "NL_disc": 15 }

            # Greedy pass, cycling categories while there is still need
            stalled = False
            while sum(needs.values()) > 0 and not stalled:
                stalled = True
                for cat in order:
                    if needs[cat] == 0:
                        continue
                    pool = pools[cat]
                    # Try to pick one edge for this category
                    picked = False
                    # heuristic: iterate through pool and pick the first feasible edge
                    # you can also prefer endpoints with tighter capacity (but capacities are all 1)
                    for idx, (lname, nname) in enumerate(pool):
                        if capL2[lname] > 0 and capN2[nname] > 0:
                            chosen[cat].append((lname, nname))
                            capL2[lname] -= 1
                            capN2[nname] -= 1
                            # remove from pool
                            pool[idx], pool[-1] = pool[-1], pool[idx]
                            pool.pop()
                            needs[cat] -= 1
                            picked = True
                            stalled = False
                            break
                    if sum(needs.values()) == 0:
                        break
                # continue cycling until we either satisfy all or stall

            # Check if we built a full perfect matching (60 edges)
            if sum(len(v) for v in chosen.values()) == 60:
                success = True
                # Assemble oriented pairs and split into the two mixed blocks
                block2_LN = []  # L>N: (L, N) where size(L) > size(N)
                block3_NL = []  # N>L: (N, L) where size(N) > size(L)
                oriented_all = []

                # LL_* categories are size(L) > size(N)
                for (lname, nname) in chosen["LL_conc"] + chosen["LL_disc"]:
                    LA, NB = obj_idx[lname], obj_idx[nname]
                    assert LA["size_rank"] > NB["size_rank"]
                    block2_LN.append((lname, nname))
                    oriented_all.append((lname, nname))
                # NL_* categories are size(N) > size(L)
                for (lname, nname) in chosen["NL_conc"] + chosen["NL_disc"]:
                    LA, NB = obj_idx[lname], obj_idx[nname]
                    assert NB["size_rank"] > LA["size_rank"]
                    block3_NL.append((nname, lname))
                    oriented_all.append((nname, lname))

                # Sanity: per-object capacity used exactly once in mixed
                assert all(v == 0 for v in capL2.values())
                assert all(v == 0 for v in capN2.values())

                # Also ensure 15/15 danger splits inside each mixed block
                def conc_count(pairs):
                    # pairs are oriented (larger, smaller)
                    c = 0
                    for a, b in pairs:
                        if is_more_dangerous(obj_idx[a], obj_idx[b]):
                            c += 1
                    return c
                assert conc_count(block2_LN) == 15
                assert conc_count(block3_NL) == 15

                return oriented_all, block2_LN, block3_NL

        # else restart

    raise RuntimeError("Failed to construct the mixed perfect matching with 15/15/15/15 quotas. "
                       "Try a different --seed or increase --max-attempts.")


# ----------------------------
# Assembly & validation
# ----------------------------

def assemble_design(rows, seed=12345, max_tries_within=20000, max_attempts_mixed=2000, shuffle_output=False):
    """
    Builds the full 120-trial design and returns:
      trials_master: list of (block, larger, smaller) length 120
      block2: list of (L, N) length 30 (L>N)
      block3: list of (N, L) length 30 (N>L)
    """
    rng = random.Random(seed)
    validate_input(rows)
    obj_idx = index_by_name(rows)
    L, N = split_classes(rows)

    # Within-class perfect matchings (60 items each -> 30 pairs each)
    LL_pairs = within_class_block(L, obj_idx, target_concordant=15, max_tries=max_tries_within, rng=rng)  # (larger, smaller)
    NN_pairs = within_class_block(N, obj_idx, target_concordant=15, max_tries=max_tries_within, rng=rng)

    # Mixed: ONE perfect matching between L and N with four quotas of 15
    mixed_all, block2_LN, block3_NL = build_mixed_matching(L, N, obj_idx, rng, max_attempts=max_attempts_mixed)

    # Compose master list in canonical block order
    trials = []
    trials += [("L-L", a, b) for (a, b) in LL_pairs]       # 30
    trials += [("L>N", a, b) for (a, b) in block2_LN]      # 30
    trials += [("N>L", a, b) for (a, b) in block3_NL]      # 30
    trials += [("N-N", a, b) for (a, b) in NN_pairs]       # 30
    assert len(trials) == 120

    # Sanity: orientation by SIZE only
    for _, a, b in trials:
        A, B = obj_idx[a], obj_idx[b]
        assert is_larger(A, B), "Pair not oriented by size."

    # Per-object usage = 2 total
    usage = defaultdict(int)
    for _, a, b in trials:
        usage[a] += 1
        usage[b] += 1
    assert all(v == 2 for v in usage.values()), "Each object must appear exactly 2 times."

    # 15/15 danger split per block
    def block_concordance(block_name):
        pairs = [(a, b) for (bn, a, b) in trials if bn == block_name]
        conc = sum(1 for a, b in pairs if is_more_dangerous(obj_idx[a], obj_idx[b]))
        return conc, len(pairs) - conc

    for bn in ("L-L", "L>N", "N>L", "N-N"):
        conc, disc = block_concordance(bn)
        assert conc == 15 and disc == 15, f"{bn}: need 15/15; got {conc}/{disc}"

    # Optional presentation shuffle (safe; blocks are conceptual only)
    if shuffle_output:
        rng.shuffle(trials)

    return trials

# ----------------------------
# Counterbalanced LEFT/RIGHT lists
# ----------------------------

def make_counterbalanced_versions(trials, rows, seed=12345, shuffle_within_type=False):
    """
    Create Version A and Version B presentation lists:
    - For each trial type (L-L, L>N, N>L, N-N), ensure:
        15 trials with larger on LEFT, 15 with larger on RIGHT.
    - Version A: randomly choose which 15 are left/right within each type.
    - Version B: mirror of A (every trial's sides flipped).
    Optionally shuffle within each type for A (B follows the same order).
    """
    rng = random.Random(seed)
    obj_idx = index_by_name(rows)

    # Group by type
    groups = {bn: [] for bn in ("L-L", "L>N", "N>L", "N-N")}
    for bn, a, b in trials:
        groups[bn].append((bn, a, b))  # (block, larger, smaller)

    versionA = []
    versionB = []

    for bn in ("L-L", "L>N", "N>L", "N-N"):
        block_trials = groups[bn][:]
        if shuffle_within_type:
            rng.shuffle(block_trials)

        # Choose 15 indices to place larger on LEFT; remaining 15 → larger on RIGHT
        idxs = list(range(len(block_trials)))
        rng.shuffle(idxs)
        left_idxs = set(idxs[:15])

        # Build A and mirrored B
        for i, (bn_, larger, smaller) in enumerate(block_trials):
            if i in left_idxs:
                # A: larger on left
                left_obj, right_obj = larger, smaller
            else:
                # A: larger on right
                left_obj, right_obj = smaller, larger

            versionA.append((bn_, left_obj, right_obj))

            # Mirror for B
            versionB.append((bn_, right_obj, left_obj))

    return versionA, versionB

# ----------------------------
# Writers
# ----------------------------

def write_master_csv(trials, rows, out_path):
    obj_idx = index_by_name(rows)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "trial",
                "block",
                "larger_object",
                "larger_classification",
                "smaller_object",
                "smaller_classification",
                "larger_size_rank",
                "smaller_size_rank",
                "larger_danger_rank",
                "smaller_danger_rank",
                "larger_is_more_dangerous",
            ],
        )
        writer.writeheader()
        for i, (bn, a, b) in enumerate(trials, start=1):
            A, B = obj_idx[a], obj_idx[b]
            writer.writerow({
                "trial": i,
                "block": bn,
                "larger_object": a,
                "larger_classification": A["classification"],
                "smaller_object": b,
                "smaller_classification": B["classification"],
                "larger_size_rank": A["size_rank"],
                "smaller_size_rank": B["size_rank"],
                "larger_danger_rank": A["danger_rank"],
                "smaller_danger_rank": B["danger_rank"],
                "larger_is_more_dangerous": "yes" if is_more_dangerous(A, B) else "no",
            })

def write_presentation_csv(trials_lr, rows, out_path):
    """
    trials_lr: list of (block, left_object, right_object) in intended presentation order.
    """
    obj_idx = index_by_name(rows)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "trial",
                "block",
                "left_object",
                "left_classification",
                "right_object",
                "right_classification",
                "larger_side",  # 'left' or 'right'
                "larger_object",
                "smaller_object",
                "larger_is_more_dangerous",
            ],
        )
        writer.writeheader()
        for i, (bn, left_obj, right_obj) in enumerate(trials_lr, start=1):
            L, R = obj_idx[left_obj], obj_idx[right_obj]
            # Determine which side is larger by SIZE
            if is_larger(L, R):
                larger_side = "left"
                larger_obj, smaller_obj = left_obj, right_obj
                larger_is_more = "yes" if is_more_dangerous(L, R) else "no"
            else:
                larger_side = "right"
                larger_obj, smaller_obj = right_obj, left_obj
                larger_is_more = "yes" if is_more_dangerous(R, L) else "no"

            writer.writerow({
                "trial": i,
                "block": bn,
                "left_object": left_obj,
                "left_classification": L["classification"],
                "right_object": right_obj,
                "right_classification": R["classification"],
                "larger_side": larger_side,
                "larger_object": larger_obj,
                "smaller_object": smaller_obj,
                "larger_is_more_dangerous": larger_is_more,
            })


# ----------------------------
# CLI
# ----------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Construct a 120-trial, degree-2 balanced design with size/danger total orders."
    )
    ap.add_argument("--input", required=True,
                    help="CSV with columns: object,classification,size_rank,danger_rank (120 rows; 60 living + 60 nonliving).")
    ap.add_argument("--out-master", default="pairs_master_120x2.csv",
                    help="Output CSV of the logical pairs (larger->smaller) with block labels.")
    ap.add_argument("--out-versionA", default="stimlist_versionA.csv",
                    help="Presentation CSV with left/right for Version A (balanced within type).")
    ap.add_argument("--out-versionB", default="stimlist_versionB.csv",
                    help="Presentation CSV with left/right for Version B (mirror of A).")
    ap.add_argument("--seed", type=int, default=12345, help="Random seed (controls which valid solution you get).")
    ap.add_argument("--within-tries", type=int, default=20000,
                    help="Max tries to find 15/15 within-class matching (L-L, N-N).")
    ap.add_argument("--mixed-attempts", type=int, default=2000,
                    help="Max attempts for building the mixed perfect matching with 15/15/15/15 quotas.")
    ap.add_argument("--shuffle-master", action="store_true",
                    help="Shuffle the final 120 trials in the master file (presentation can also be shuffled via A/B lists).")
    ap.add_argument("--shuffle-within-type", action="store_true",
                    help="Shuffle trial order within each type when creating Version A/B lists.")
    args = ap.parse_args()

    rows = load_items(args.input)
    trials_master = assemble_design(
        rows,
        seed=args.seed,
        max_tries_within=args.within_tries,
        max_attempts_mixed=args.mixed_attempts,
        shuffle_output=args.shuffle_master,
    )
    write_master_csv(trials_master, rows, args.out_master)

    # Counterbalanced presentation lists (A/B)
    versionA, versionB = make_counterbalanced_versions(
        trials_master, rows, seed=args.seed, shuffle_within_type=args.shuffle_within_type
    )
    write_presentation_csv(versionA, rows, args.out_versionA)
    write_presentation_csv(versionB, rows, args.out_versionB)

    # Quick summary
    obj_idx = index_by_name(rows)
    def block_conc(trials):
        stats = {}
        for bn in ("L-L", "L>N", "N>L", "N-N"):
            pairs = [(a, b) for (bb, a, b) in trials if bb == bn]
            conc = sum(1 for a, b in pairs if is_more_dangerous(obj_idx[a], obj_idx[b]))
            stats[bn] = (len(pairs), conc, len(pairs) - conc)
        return stats

    stats = block_conc(trials_master)
    print("Master block stats (pairs, concordant, discordant):")
    for bn in ("L-L", "L>N", "N>L", "N-N"):
        print(f"  {bn:3s}: {stats[bn]}")
    # Per-object usage
    usage = defaultdict(int)
    for _, a, b in trials_master:
        usage[a] += 1
        usage[b] += 1
    ok = all(v == 2 for v in usage.values())
    print(f"All 120 objects used exactly 2 times? {ok}")
    print(f"Wrote:\n  {args.out_master}\n  {args.out_versionA}\n  {args.out_versionB}")

if __name__ == "__main__":
    main()
