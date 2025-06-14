# src/Encryption/cipher.py
# Modul ini berisi berbagai fungsi untuk enkripsi dan dekripsi data.

class Cipher:
    """
    Kelas yang menyediakan metode enkripsi dan dekripsi.
    Untuk aplikasi nyata, gunakan pustaka kriptografi standar seperti 'cryptography'.
    Cipher klasik ini disediakan untuk tujuan edukasi.
    """

    @staticmethod
    def _caesar_process(text: str, shift: int, mode: str) -> str:
        """Proses inti untuk Caesar Cipher."""
        result = ""
        for char in text:
            if char.isalpha():
                start = ord('a') if char.islower() else ord('A')
                if mode == 'encrypt':
                    shifted_char_code = (ord(char) - start + shift) % 26 + start
                else: # decrypt
                    shifted_char_code = (ord(char) - start - shift) % 26 + start
                result += chr(shifted_char_code)
            else:
                result += char
        return result

    @staticmethod
    def caesar_encrypt(plaintext: str, shift: int = 3) -> str:
        """
        Mengenkripsi teks menggunakan Caesar Cipher.
        Args:
            plaintext (str): Teks yang akan dienkripsi.
            shift (int): Jumlah pergeseran karakter.
        Returns:
            str: Teks terenkripsi.
        """
        return Cipher._caesar_process(plaintext, shift, 'encrypt')

    @staticmethod
    def caesar_decrypt(ciphertext: str, shift: int = 3) -> str:
        """
        Mendekripsi teks dari Caesar Cipher.
        Args:
            ciphertext (str): Teks yang akan didekripsi.
            shift (int): Jumlah pergeseran yang sama seperti saat enkripsi.
        Returns:
            str: Teks asli.
        """
        return Cipher._caesar_process(ciphertext, shift, 'decrypt')

    @staticmethod
    def _vigenere_process(text: str, key: str, mode: str) -> str:
        """Proses inti untuk Vigenere Cipher."""
        result = ""
        key_index = 0
        for char in text:
            if char.isalpha():
                key_char = key[key_index % len(key)]
                key_shift = ord(key_char.lower()) - ord('a')
                
                start = ord('a') if char.islower() else ord('A')
                
                if mode == 'encrypt':
                    shifted_char_code = (ord(char) - start + key_shift) % 26 + start
                else: # decrypt
                    shifted_char_code = (ord(char) - start - key_shift) % 26 + start
                    
                result += chr(shifted_char_code)
                key_index += 1
            else:
                result += char
        return result

    @staticmethod
    def vigenere_encrypt(plaintext: str, key: str) -> str:
        """
        Mengenkripsi teks menggunakan Vigenere Cipher.
        Kunci harus hanya berisi huruf.
        Args:
            plaintext (str): Teks yang akan dienkripsi.
            key (str): Kunci enkripsi.
        Returns:
            str: Teks terenkripsi.
        """
        if not key.isalpha():
            raise ValueError("Kunci Vigenère harus hanya berisi huruf.")
        return Cipher._vigenere_process(plaintext, key, 'encrypt')

    @staticmethod
    def vigenere_decrypt(ciphertext: str, key: str) -> str:
        """
        Mendekripsi teks dari Vigenere Cipher.
        Args:
            ciphertext (str): Teks yang akan didekripsi.
            key (str): Kunci yang sama seperti saat enkripsi.
        Returns:
            str: Teks asli.
        """
        if not key.isalpha():
            raise ValueError("Kunci Vigenère harus hanya berisi huruf.")
        return Cipher._vigenere_process(ciphertext, key, 'decrypt')

