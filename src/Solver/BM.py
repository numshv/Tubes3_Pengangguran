NO_OF_CHARS = 256 

def bad_char(pattern: str) -> list[int]: 
    bad_char_table = {}
    m = len(pattern)
    for i in range(m):
        bad_char_table[pattern[i]] = i
    return bad_char_table

def boyer_moore(text: str, pattern: str) -> int: 
    n = len(text)
    m = len(pattern)
    total = 0
    if m == 0 or n == 0 or m > n:
        return 0
    
    bad_char_table = bad_char(pattern) 

    s = 0   
    while s <= (n - m):
        j = m - 1   
        while j >= 0 and pattern[j] == text[s + j]:
            j -= 1

        if j < 0:
            total += 1
            if s + m < n:
                mismatched_char_after_match = text[s + m]
                shift = m - bad_char_table.get(mismatched_char_after_match, -1)
                s += shift
            else:
                s += 1
        else:
            mismatched_char = text[s + j]
            shift = j - bad_char_table.get(mismatched_char, -1)
            s += max(1, shift)
            
    return total