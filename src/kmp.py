
def border(pattern: str)->list[int]:
    # border function buat KMP
    m = len(pattern)
    b = [0] * m
    j = 0
    i = 1
    while i<m:
        if pattern[i] == pattern[j]:
            b[i] = j + 1
            j += 1
            i += 1
        else:
            if j > 0:
                j = b[j-1]
            else:
                b[i] = 0
                i += 1
    return b

def kmp(text: str, pattern: str) -> int:
    # ngitung berapa kali pattern muncul di text
    n = len(text)
    m = len(pattern)
    # kalo text atau pattern kosong return 0
    if m == 0 or n == 0:
        return 0
    b = border(pattern)
    i = 0
    j = 0
    total = 0
    while i < n:
        if text[i] == pattern[j]:
            i += 1
            j += 1
            if j == m:
                total += 1
                j = b[j - 1]
        else:
            if j > 0:
                j = b[j - 1]
            else:
                i += 1
    return total
