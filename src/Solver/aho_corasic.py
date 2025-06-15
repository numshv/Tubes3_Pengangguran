import collections

def build_trie(keyword_list: list[str]) -> tuple:
    if not keyword_list:
        return ({}, [[]], [0], [])
    trie = [{}]
    output = [[]]
    fail = [0]
    def insert(word, idx):
        node = 0
        for char in word:
            if char not in trie[node]:
                trie.append({})
                output.append([])
                fail.append(0)
                trie[node][char] = len(trie) - 1
            node = trie[node][char]
        output[node].append(idx)
    for i, word in enumerate(keyword_list):
        insert(word, i)
    queue = collections.deque()
    for char in trie[0]:
        child = trie[0][char]
        queue.append(child)
    while queue:
        current = queue.popleft()
        for char, next_node in trie[current].items():
            queue.append(next_node)
            fail_node = fail[current]
            while fail_node != 0 and char not in trie[fail_node]:
                fail_node = fail[fail_node]
            fail[next_node] = trie[fail_node].get(char, 0)
            output[next_node].extend(output[fail[next_node]])
    return (trie, output, fail, keyword_list)

def aho_corasic(trie_data: tuple, text: str) -> list[int]:
    """
    Mencari beberapa pola dalam sebuah teks menggunakan trie Aho-Corasick yang sudah dibangun.

    Args:
        trie_data: Sebuah tuple (trie, output, fail, keyword_list) dari build_aho_corasick_trie.
        text: Teks yang akan dicari.

    Returns:
        Sebuah list integer, di mana setiap elemen adalah jumlah kemunculan
        untuk setiap pola sesuai urutan aslinya.
    """
    trie, output, fail, keyword_list = trie_data
    if not keyword_list:
        return []

    result = [0] * len(keyword_list)
    node = 0
    for char in text:
        while node != 0 and char not in trie[node]:
            node = fail[node]
        node = trie[node].get(char, 0)
        for keyword_idx in output[node]:
            result[keyword_idx] += 1
            
    return result