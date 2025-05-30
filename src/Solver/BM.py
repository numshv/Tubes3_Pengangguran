NO_OF_CHARS = 256 #asumsi ukuran char dalam ASCII

def bad_char(pattern: str) -> list[int]: # buat tabel bad character
    # karakter not in pattern = -1
    m = len(pattern)
    bad_char_table = [-1] * NO_OF_CHARS 
    for i in range(m):
        bad_char_table[ord(pattern[i])] = i
    
    return bad_char_table

def boyer_moore(text: str, pattern: str) -> int: # hitung banyaknya kemunculan pattern dalam textt
    n = len(text)
    m = len(pattern)
    total = 0
    # jika teks kosong return 0
    if m == 0 or n == 0 or m > n:
        return 0
    
    bad_char_table = bad_char(pattern)

    s = 0 # shift pattern terhadap text  
    while s <= (n - m):
        j = m - 1  # Mulai dari char terakhir
        while j >= 0 and pattern[j] == text[s + j]:
            j -= 1
        # Jika semua pattern cocok, j=-1
        if j < 0:
            total += 1
            #jika masih ada karakter lain
            if s + m < n:
                #shift 
                shift = m - bad_char_table[ord(text[s + m])]
                s += shift
            else:
                s += 1 #buat stop loop 

        # Jika ada yang ga cocok, shift
        else:
            shift = j - bad_char_table[ord(text[s + j])]
            s += max(1, shift) # minimal geser sekali
    return total

