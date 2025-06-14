import os
import mysql.connector
from faker import Faker
from pathlib import Path

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
        profiles = [
            (
                app_id, fake.first_name(), fake.last_name(),
                fake.date_of_birth(minimum_age=18, maximum_age=65),
                fake.address(), fake.phone_number()
            ) for app_id, role, cv_path in applicant_details
        ]
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

# This allows the file to be run directly for testing, if needed
if __name__ == "__main__":
    DB_CONFIG_TEST = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'ats_pengangguran1'
    }
    run_seeding(DB_CONFIG_TEST)