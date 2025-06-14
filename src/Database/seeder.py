import os
import mysql.connector
from faker import Faker
from pathlib import Path
from Database.encryption import Cipher

# This file will now be used as a module, so we wrap the logic in a function.

def run_seeding(db_config):
    """
    Main seeder function that connects to the DB and populates it.
    """
    print("--- Starting Database Seeding Process ---")
    
    # Inner functions from your original seeder
    def get_cv_files():
        cv_files = []
        # Assume 'data' folder is in the project root, one level above 'src'
        data_path = Path(__file__).parent.parent.parent / 'data'
        
        if not data_path.exists():
            print(f"!!! Data folder not found at: {data_path}. Cannot seed from CVs.")
            return cv_files
        
        for role_folder in data_path.iterdir():
            if role_folder.is_dir():
                role_name = role_folder.name
                for cv_file in role_folder.iterdir():
                    if cv_file.is_file() and cv_file.suffix.lower() == '.pdf':
                        relative_path = f"data/{role_name}/{cv_file.name}"
                        cv_files.append((role_name, relative_path))
        return cv_files

    def create_connection():
        try:
            return mysql.connector.connect(**db_config)
        except mysql.connector.Error as e:
            print(f"Error connecting to database for seeding: {e}")
            return None

    def seed_applicant_detail(connection, cv_files):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM ApplicantDetail")
        cursor.execute("ALTER TABLE ApplicantDetail AUTO_INCREMENT = 1")
        insert_query = "INSERT INTO ApplicantDetail (application_role, cv_path) VALUES (%s, %s)"
        details = [(role, cv_path) for role, cv_path in cv_files]
        cursor.executemany(insert_query, details)
        connection.commit()
        print(f"Seeded {len(details)} records in ApplicantDetail.")
        cursor.execute("SELECT applicant_id, application_role, cv_path FROM ApplicantDetail")
        return cursor.fetchall()

    def seed_applicant_profile(connection, applicant_details):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM ApplicantProfile")
        fake = Faker('id_ID')
        secret_key = "RAHASIA"
        print(f"Encrypting new profiles with key: '{secret_key}'")

        profiles = []
        for app_id, role, cv_path in applicant_details:
            # Ubah data tanggal lahir menjadi string sebelum enkripsi
            dob_str = fake.date_of_birth(minimum_age=18, maximum_age=65).strftime('%Y-%m-%d')

            encrypted_profile = (
                app_id,
                Cipher.vigenere_encrypt(fake.first_name(), secret_key),
                Cipher.vigenere_encrypt(fake.last_name(), secret_key),
                Cipher.vigenere_encrypt(dob_str, secret_key),
                Cipher.vigenere_encrypt(fake.address(), secret_key),
                Cipher.vigenere_encrypt(fake.phone_number(), secret_key)
            )
            profiles.append(encrypted_profile)
        insert_query = "INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(insert_query, profiles)
        connection.commit()
        print(f"Seeded {len(profiles)} records in ApplicantProfile.")

    # --- Seeding Execution ---
    cv_files = get_cv_files()
    if not cv_files:
        print("Seeding process stopped as no CV files were found.")
        return

    connection = create_connection()
    if not connection:
        return

    try:
        applicant_details = seed_applicant_detail(connection, cv_files)
        seed_applicant_profile(connection, applicant_details)
        print("--- Seeding Completed Successfully! ---")
    except mysql.connector.Error as e:
        print(f"Database error during seeding: {e}")
        connection.rollback()
    finally:
        if connection.is_connected():
            connection.close()
            print("--- Seeder database connection closed. ---")

def encrypt_all_profiles(db_config: dict, key: str):
    """
    Mengambil semua data dari ApplicantProfile, mengenkripsinya, dan menyimpannya kembali.
    Fungsi ini untuk tujuan demonstrasi.
    """
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
            # Mengenkripsi setiap field yang diperlukan
            encrypted_data = (
                Cipher.vigenere_encrypt(str(profile['first_name']), key),
                Cipher.vigenere_encrypt(str(profile['last_name']), key),
                Cipher.vigenere_encrypt(str(profile['date_of_birth']), key),
                Cipher.vigenere_encrypt(str(profile['address']), key),
                Cipher.vigenere_encrypt(str(profile['phone_number']), key),
                profile['applicant_id'] # ID untuk klausa WHERE
            )
            encrypted_data_list.append(encrypted_data)

        # Memperbarui database dengan data terenkripsi
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