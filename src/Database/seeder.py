import mysql.connector
from pathlib import Path
from Database.encryption import Cipher


def encrypt_all_profiles(db_config: dict, key: str):
    print("--- Starting Bulk Encryption Process ---")
    if not key.isalpha():
        print("Error: Encryption key must only contain letters.")
        return

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        print("Fetching all applicant profiles...")
        cursor.execute("SELECT applicant_id, first_name, last_name, date_of_birth, address, phone_number FROM ApplicantProfile")
        profiles_to_encrypt = cursor.fetchall()
        
        if not profiles_to_encrypt:
            print("No profiles to encrypt.")
            return

        print(f"Found {len(profiles_to_encrypt)} profiles. Encrypting fields...")
        encrypted_data_list = []
        for profile in profiles_to_encrypt:
            encrypted_data = (
                Cipher.vigenere_encrypt(str(profile['first_name']), key),
                Cipher.vigenere_encrypt(str(profile['last_name']), key),
                Cipher.vigenere_encrypt(str(profile['date_of_birth']), key),
                Cipher.vigenere_encrypt(str(profile['address']), key),
                Cipher.vigenere_encrypt(str(profile['phone_number']), key),
                profile['applicant_id'] # ID untuk klausa WHERE
            )
            encrypted_data_list.append(encrypted_data)

        update_query = """
            UPDATE ApplicantProfile 
            SET first_name = %s, last_name = %s, date_of_birth = %s, address = %s, phone_number = %s
            WHERE applicant_id = %s
        """
        cursor.executemany(update_query, encrypted_data_list)
        connection.commit()
        print(f"--- Successfully encrypted {cursor.rowcount} profiles. ---")

    except mysql.connector.Error as err:
        print(f"Database error during bulk encryption: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

if __name__ == '__main__':
    DB_CONFIG_TEST = {
        'host': 'localhost',
        'user': 'root',
        'password': 'n0um1sy1fa',
        'database': 'ats_pengangguran2'
    }
    SECRET_KEY = "RAHASIA"
    encrypt_all_profiles(DB_CONFIG_TEST, SECRET_KEY)