def parse(sentence: str) -> list:
    return sentence.split()

def levenshtein_distance(S1: str, S2: str) -> int:
    s1 = S1.lower()
    s2 = S2.lower()
    matriks = [[float('inf')] * (len(s2) + 1) for _ in range(len(s1) + 1)]
    for j in range(len(s2) + 1):
        matriks[len(s1)][j] = len(s2) - j
    for i in range(len(s1) + 1):
        matriks[i][len(s2)] = len(s1) - i
    for i in range(len(s1) - 1, -1, -1):
        for j in range(len(s2) - 1, -1, -1):
            if s1[i] == s2[j]:
                matriks[i][j] = matriks[i + 1][j + 1]
            else:
                matriks[i][j] = 1 + min(
                    matriks[i + 1][j],
                    matriks[i][j + 1],
                    matriks[i + 1][j + 1]
                )
    return matriks[0][0]

def fuzzy_match(S1: str, S2: str, maxDistance: int) -> int:
    words1 = parse(S1)
    words2 = parse(S2)
    count = 0
    len2 = len(words2)
    for i in range(len(words1) - len2 + 1):
        chunk = ' '.join(words1[i:i + len2])
        if levenshtein_distance(chunk, S2) <= maxDistance:
            count += 1
    return count