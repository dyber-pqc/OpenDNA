"""Sequence alignment - pairwise and consensus."""

from __future__ import annotations

# BLOSUM62 substitution matrix (subset)
BLOSUM62 = {}
BLOSUM62_RAW = """
A:A=4 R:-1 N:-2 D:-2 C:0 Q:-1 E:-1 G:0 H:-2 I:-1 L:-1 K:-1 M:-1 F:-2 P:-1 S:1 T:0 W:-3 Y:-2 V:0
R:A=-1 R:5 N:0 D:-2 C:-3 Q:1 E:0 G:-2 H:0 I:-3 L:-2 K:2 M:-1 F:-3 P:-2 S:-1 T:-1 W:-3 Y:-2 V:-3
N:A=-2 R:0 N:6 D:1 C:-3 Q:0 E:0 G:0 H:1 I:-3 L:-3 K:0 M:-2 F:-3 P:-2 S:1 T:0 W:-4 Y:-2 V:-3
D:A=-2 R:-2 N:1 D:6 C:-3 Q:0 E:2 G:-1 H:-1 I:-3 L:-4 K:-1 M:-3 F:-3 P:-1 S:0 T:-1 W:-4 Y:-3 V:-3
C:A=0 R:-3 N:-3 D:-3 C:9 Q:-3 E:-4 G:-3 H:-3 I:-1 L:-1 K:-3 M:-1 F:-2 P:-3 S:-1 T:-1 W:-2 Y:-2 V:-1
Q:A=-1 R:1 N:0 D:0 C:-3 Q:5 E:2 G:-2 H:0 I:-3 L:-2 K:1 M:0 F:-3 P:-1 S:0 T:-1 W:-2 Y:-1 V:-2
E:A=-1 R:0 N:0 D:2 C:-4 Q:2 E:5 G:-2 H:0 I:-3 L:-3 K:1 M:-2 F:-3 P:-1 S:0 T:-1 W:-3 Y:-2 V:-2
G:A=0 R:-2 N:0 D:-1 C:-3 Q:-2 E:-2 G:6 H:-2 I:-4 L:-4 K:-2 M:-3 F:-3 P:-2 S:0 T:-2 W:-2 Y:-3 V:-3
H:A=-2 R:0 N:1 D:-1 C:-3 Q:0 E:0 G:-2 H:8 I:-3 L:-3 K:-1 M:-2 F:-1 P:-2 S:-1 T:-2 W:-2 Y:2 V:-3
I:A=-1 R:-3 N:-3 D:-3 C:-1 Q:-3 E:-3 G:-4 H:-3 I:4 L:2 K:-3 M:1 F:0 P:-3 S:-2 T:-1 W:-3 Y:-1 V:3
L:A=-1 R:-2 N:-3 D:-4 C:-1 Q:-2 E:-3 G:-4 H:-3 I:2 L:4 K:-2 M:2 F:0 P:-3 S:-2 T:-1 W:-2 Y:-1 V:1
K:A=-1 R:2 N:0 D:-1 C:-3 Q:1 E:1 G:-2 H:-1 I:-3 L:-2 K:5 M:-1 F:-3 P:-1 S:0 T:-1 W:-3 Y:-2 V:-2
M:A=-1 R:-1 N:-2 D:-3 C:-1 Q:0 E:-2 G:-3 H:-2 I:1 L:2 K:-1 M:5 F:0 P:-2 S:-1 T:-1 W:-1 Y:-1 V:1
F:A=-2 R:-3 N:-3 D:-3 C:-2 Q:-3 E:-3 G:-3 H:-1 I:0 L:0 K:-3 M:0 F:6 P:-4 S:-2 T:-2 W:1 Y:3 V:-1
P:A=-1 R:-2 N:-2 D:-1 C:-3 Q:-1 E:-1 G:-2 H:-2 I:-3 L:-3 K:-1 M:-2 F:-4 P:7 S:-1 T:-1 W:-4 Y:-3 V:-2
S:A=1 R:-1 N:1 D:0 C:-1 Q:0 E:0 G:0 H:-1 I:-2 L:-2 K:0 M:-1 F:-2 P:-1 S:4 T:1 W:-3 Y:-2 V:-2
T:A=0 R:-1 N:0 D:-1 C:-1 Q:-1 E:-1 G:-2 H:-2 I:-1 L:-1 K:-1 M:-1 F:-2 P:-1 S:1 T:5 W:-2 Y:-2 V:0
W:A=-3 R:-3 N:-4 D:-4 C:-2 Q:-2 E:-3 G:-2 H:-2 I:-3 L:-2 K:-3 M:-1 F:1 P:-4 S:-3 T:-2 W:11 Y:2 V:-3
Y:A=-2 R:-2 N:-2 D:-3 C:-2 Q:-1 E:-2 G:-3 H:2 I:-1 L:-1 K:-2 M:-1 F:3 P:-3 S:-2 T:-2 W:2 Y:7 V:-1
V:A=0 R:-3 N:-3 D:-3 C:-1 Q:-2 E:-2 G:-3 H:-3 I:3 L:1 K:-2 M:1 F:-1 P:-2 S:-2 T:0 W:-3 Y:-1 V:4
"""

for line in BLOSUM62_RAW.strip().split("\n"):
    parts = line.split()
    row_aa = parts[0].split(":")[0]
    BLOSUM62[row_aa] = {}
    first = parts[0].split("=")[1]
    BLOSUM62[row_aa][parts[0].split(":")[1].split("=")[0]] = int(first)
    for token in parts[1:]:
        col, val = token.split(":")
        BLOSUM62[row_aa][col] = int(val)


def score_pair(a: str, b: str) -> int:
    if a == "-" or b == "-":
        return -8
    return BLOSUM62.get(a, {}).get(b, 0)


def needleman_wunsch(seq1: str, seq2: str, gap: int = -8) -> dict:
    """Global pairwise sequence alignment (Needleman-Wunsch)."""
    n = len(seq1)
    m = len(seq2)

    # DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i * gap
    for j in range(m + 1):
        dp[0][j] = j * gap

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match = dp[i - 1][j - 1] + score_pair(seq1[i - 1], seq2[j - 1])
            delete = dp[i - 1][j] + gap
            insert = dp[i][j - 1] + gap
            dp[i][j] = max(match, delete, insert)

    # Traceback
    align1, align2 = [], []
    i, j = n, m
    while i > 0 and j > 0:
        s = score_pair(seq1[i - 1], seq2[j - 1])
        if dp[i][j] == dp[i - 1][j - 1] + s:
            align1.append(seq1[i - 1])
            align2.append(seq2[j - 1])
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + gap:
            align1.append(seq1[i - 1])
            align2.append("-")
            i -= 1
        else:
            align1.append("-")
            align2.append(seq2[j - 1])
            j -= 1

    while i > 0:
        align1.append(seq1[i - 1])
        align2.append("-")
        i -= 1
    while j > 0:
        align1.append("-")
        align2.append(seq2[j - 1])
        j -= 1

    align1.reverse()
    align2.reverse()

    aligned1 = "".join(align1)
    aligned2 = "".join(align2)
    matches = sum(1 for a, b in zip(aligned1, aligned2) if a == b and a != "-")
    similar = sum(1 for a, b in zip(aligned1, aligned2) if a != "-" and b != "-" and score_pair(a, b) > 0)
    aligned_len = sum(1 for a, b in zip(aligned1, aligned2) if a != "-" or b != "-")
    identity = matches / max(min(n, m), 1) * 100
    similarity = similar / max(min(n, m), 1) * 100

    # Build comparison string
    comparison = []
    for a, b in zip(aligned1, aligned2):
        if a == b and a != "-":
            comparison.append("|")
        elif a != "-" and b != "-" and score_pair(a, b) > 0:
            comparison.append(":")
        else:
            comparison.append(" ")

    return {
        "score": dp[n][m],
        "identity_pct": round(identity, 2),
        "similarity_pct": round(similarity, 2),
        "aligned_length": aligned_len,
        "alignment_1": aligned1,
        "alignment_2": aligned2,
        "comparison": "".join(comparison),
        "matches": matches,
    }
