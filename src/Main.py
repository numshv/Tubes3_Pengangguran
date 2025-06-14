import flet as ft
from datetime import datetime
import mysql.connector
from pathlib import Path
from Database.seeder import run_seeding
from mysql.connector import errorcode

class CVATSSearchApp:
    def __init__(self):
        self.page = None
        self.modal_open = False
        
        # Modal positions for peeking and opening
        self.open_pos = 0.4      # Top of modal is 40% down from the top of the screen
        self.closed_pos = 0.75   # Top of modal is 75% down (more peeking)
        self.modal_position = self.closed_pos

        self.drag_start_y = 0
        self.modal_start_position = 0
        
        # Expanded dummy data for the summary view
        self.search_results = [
            {
                'id': 0, 'name': 'Qodri', 'matches': 4, 'rank': 1, 'total_candidates': 99,
                'address': 'Jl. hahahahah No.69', 'phone': '+6299999999999',
                'birth_date': '09/11/2001',
                'skills': 'Flet, Python, UI/UX Design, Sleeping',
                'keywords': [('React', 2), ('Javascript', 3)],
                'job_history': [
                    {'title': 'CTO', 'period': '2023 - Present', 'desc': 'Leading the tech team to build amazing Flet applications.'},
                    {'title': 'Senior Developer', 'period': '2021 - 2023', 'desc': 'Developed and maintained various software projects.'},
                ],
                'education': [
                    {'degree': 'SMA UBUBUBU', 'period': '2018 - 2021', 'desc': 'Focused on Computer Science and advanced mathematics.'},
                    {'degree': 'SMP Ububub', 'period': '2015 - 2018', 'desc': 'Learned the fundamentals of logic and problem-solving.'},
                ]
            }
        ]
        for i in range(1, 8):
            new_candidate = self.search_results[0].copy()
            new_candidate['id'] = i
            new_candidate['name'] = f'Candidate {i+1}'
            new_candidate['rank'] = i + 1
            self.search_results.append(new_candidate)


        self.db_config = {
            'host': 'localhost',
            'user': 'root',  # Change as needed
            'password': 'n0um1sy1fa',  # Change as needed
            'database': 'ats_pengangguran'
        }

    def setup_database(self):
        """Ensures the database and tables exist, and seeds if necessary."""
        print("--- Initializing Database Setup ---")
        try:
            # Connect to MySQL server without specifying a database
            db_server_config = self.db_config.copy()
            db_server_config.pop('database', None)
            
            connection = mysql.connector.connect(**db_server_config)
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            db_name = self.db_config['database']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {db_name}")
            print(f"Database '{db_name}' is ready.")

            # Create tables from schema (corrected SQL)
            # Note: A real app would read this from schema.sql
            tables = {
                "ApplicantProfile": """
                    CREATE TABLE IF NOT EXISTS `ApplicantProfile` (
                        `applicant_id` INT PRIMARY KEY NOT NULL,
                        `first_name` VARCHAR(50) DEFAULT NULL,
                        `last_name` VARCHAR(50) DEFAULT NULL,
                        `date_of_birth` DATE DEFAULT NULL,
                        `address` VARCHAR(255) DEFAULT NULL,
                        `phone_number` VARCHAR(20) DEFAULT NULL
                    ) ENGINE=InnoDB;
                """,
                "ApplicantDetail": """
                    CREATE TABLE IF NOT EXISTS `ApplicantDetail` (
                        `applicant_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
                        `application_role` VARCHAR(100) DEFAULT NULL,
                        `cv_path` TEXT
                    ) ENGINE=InnoDB;
                """
            }
            for table_name, table_sql in tables.items():
                try:
                    print(f"Creating table '{table_name}'...")
                    cursor.execute(table_sql)
                except mysql.connector.Error as err:
                    print(f"Failed creating table: {err}")

            # Check if the database is empty
            cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
            if cursor.fetchone()[0] == 0:
                print("Database is empty. Running seeder...")
                connection.close() # Close connection before seeder opens its own
                run_seeding(self.db_config)
            else:
                print("Database already contains data. Skipping seeder.")
            
            if connection.is_connected():
                connection.close()

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            else:
                print(f"Database setup failed: {err}")
            return False
        return True

    def load_data_from_db(self):
        """Loads and formats applicant data from the database."""
        print("--- Loading data from database (DEBUG MODE: Fetching only the first record) ---")
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            
            # --- PERUBAHAN DI SINI ---
            # Query asli Anda mengambil semua data.
            # query = """
            #     SELECT 
            #         p.applicant_id, p.first_name, p.last_name, p.date_of_birth, p.address, p.phone_number,
            #         d.application_role
            #     FROM ApplicantProfile p
            #     JOIN ApplicantDetail d ON p.applicant_id = d.applicant_id
            # """
            
            # Query yang dimodifikasi untuk mengambil hanya SATU baris data
            debug_query = """
                SELECT 
                    p.applicant_id, p.first_name, p.last_name, p.date_of_birth, p.address, p.phone_number,
                    d.application_role, d.cv_path
                FROM ApplicantProfile p
                JOIN ApplicantDetail d ON p.applicant_id = d.applicant_id
                LIMIT 1
            """
            
            cursor.execute(debug_query)
            
            # Menggunakan fetchone() untuk mendapatkan satu baris saja
            first_record = cursor.fetchone() 

            # --- Cetak data untuk debugging ---
            if first_record:
                print("\n✅  Successfully fetched the first record for debugging:")
                print(first_record)
                print("\n")
            else:
                print("\n⚠️  No records found in the database.\n")

            # Untuk sekarang, kita akan menghentikan pemrosesan lebih lanjut
            # dan menggunakan data dummy agar aplikasi tetap berjalan.
            # Ganti self.search_results dengan data yang Anda muat jika Anda ingin menampilkannya di UI.
            # self.search_results = [ formatted_data ] # Anda bisa memformat `first_record` di sini jika mau
            
            print("Debug data displayed. App will continue with existing dummy data.")

        except mysql.connector.Error as err:
            print(f"Failed to load data from DB: {err}")
            # Fallback ke data yang ada jika terjadi kesalahan
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()

    def create_header(self):
        return ft.Container(
            content=ft.Row([
                ft.Text("LOGO", size=20, weight=ft.FontWeight.BOLD, color="#E74C3C"),
                ft.Container(expand=True),
                ft.Text("CV ATS Search", size=24, weight=ft.FontWeight.BOLD, color='black'),
                ft.Container(expand=True),
                ft.Text(datetime.now().strftime("%H.%M"), size=20, weight=ft.FontWeight.BOLD, color='black')
            ]),
            padding=20, bgcolor='#FFF9EB', border=ft.border.only(bottom=ft.border.BorderSide(2, 'black'))
        )

    def create_result_card(self, result):
        keyword_list = [ft.Text(f"{i}. {keyword}: {count} occurrences", size=12, color='black54') for i, (keyword, count) in enumerate(result.get('keywords', []), 1)]
        
        return ft.Container(
            content=ft.Column([
                ft.Text(result['name'], size=16, weight=ft.FontWeight.BOLD, color='black'),
                ft.Text(f"{result['matches']} matches", size=12, color='black54'),
                ft.Text("Matched keywords:", size=12, weight=ft.FontWeight.BOLD, color='black'),
                ft.Column(keyword_list, spacing=2),
                ft.Container(
                    content=ft.Row([
                        ft.FilledButton(
                            text="Summary",
                            style=ft.ButtonStyle(bgcolor='#EACD8C', color='black', shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}),
                            on_click=lambda _, r=result: self.show_summary_view(r)
                        ),
                        ft.FilledButton(
                            text="Show CV",
                            style=ft.ButtonStyle(bgcolor='#EACD8C', color='black', shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)})
                        )
                    ], spacing=10),
                    margin=ft.margin.only(top=5) 
                )
            ], spacing=8, tight=True),
            padding=15, border=ft.border.all(2, 'black'), border_radius=8, bgcolor='#F0EFFF', width=280
        )

    # --- MODAL LOGIC ---

    def create_modal_handle(self):
        return ft.Container(content=ft.Container(height=5, width=40, bgcolor='black54', border_radius=3), padding=15, alignment=ft.alignment.center)

    def create_search_settings_content(self):
        return ft.Column([
            ft.Text("Search Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Column([ft.Text("Algorithm choice:", size=14, weight=ft.FontWeight.BOLD), ft.Dropdown(width=200, options=[ft.dropdown.Option("choose...")], value="choose...")]),
                ft.Column([ft.Text("Keywords:", size=14, weight=ft.FontWeight.BOLD), ft.TextField(hint_text="Enter ...", multiline=True, min_lines=3, width=400, border_color='black')])
            ], spacing=50, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.Column([ft.Text("Top choice:", size=14, weight=ft.FontWeight.BOLD), ft.TextField(hint_text="Enter ...", width=200, border_color='black')]),
                ft.ElevatedButton("🔍 search", bgcolor="#28A745", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)), on_click=self.perform_search)
            ], spacing=50, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def create_draggable_modal(self):
        return ft.Container(
            content=ft.Column([self.create_modal_handle(), ft.Container(content=self.create_search_settings_content(), padding=20, expand=True)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#eaf4f4", border=ft.border.all(2, 'black'), border_radius=ft.border_radius.only(top_left=15, top_right=15),
        )

    def on_pan_start(self, e: ft.DragStartEvent):
        self.drag_start_y = e.global_y
        if self.page and self.page.window_height > 0: self.modal_start_position = self.modal_container.top / self.page.window_height
        else: self.modal_start_position = self.modal_position

    def on_pan_update(self, e: ft.DragUpdateEvent):
        if self.page and self.page.window_height > 0:
            delta_y = e.global_y - self.drag_start_y
            new_position = self.modal_start_position + (delta_y / self.page.window_height)
            self.modal_position = max(self.open_pos, min(self.closed_pos, new_position))
            self.update_modal_position(animate=False)

    def on_pan_end(self, e: ft.DragEndEvent):
        threshold = (self.open_pos + self.closed_pos) / 2
        if self.modal_position < threshold: self.modal_position, self.modal_open = self.open_pos, True
        else: self.modal_position, self.modal_open = self.closed_pos, False
        self.update_modal_position(animate=True)

    def toggle_modal(self, e):
        if self.modal_open: self.modal_position, self.modal_open = self.closed_pos, False
        else: self.modal_position, self.modal_open = self.open_pos, True
        self.update_modal_position(animate=True)

    def update_modal_position(self, animate=False):
        if hasattr(self, 'modal_container') and self.page and self.page.window_height:
            window_height, window_width = self.page.window_height, self.page.window_width
            self.modal_container.animate_position = ft.Animation(300, "decelerate") if animate else None
            self.modal_container.top = window_height * self.modal_position
            
            # --- CENTERING LOGIC ---
            modal_width = window_width * 0.6
            self.modal_container.left = (window_width - modal_width) / 2
            self.modal_container.width = modal_width
            
            self.page.update()

    def on_page_resize(self, e):
        if hasattr(self, 'modal_container'):
            self.update_modal_position(animate=False)

    def perform_search(self, e):
        print("Search performed!")

    # --- MANUAL VIEW NAVIGATION LOGIC ---

    def show_main_view(self, e=None):
        """Clears the page and draws the main search view with its modal."""
        self.page.controls.clear()

        main_content = ft.Container(
            content=ft.Column([
                self.create_header(),
                ft.Container(
                    content=ft.Column([
                        ft.Container(content=ft.Text("Results", size=28, weight=ft.FontWeight.BOLD)),
                        ft.GridView(
                            expand=True, runs_count=4, max_extent=300, child_aspect_ratio=1.0,
                            spacing=20, run_spacing=20,
                            controls=[self.create_result_card(result) for result in self.search_results]
                        )
                    ]),
                    padding=20, expand=True
                )
            ]),
            expand=True
        )

        window_width = self.page.window_width or 1200
        window_height = self.page.window_height or 900
        
        modal_width = window_width * 0.6
        
        # --- REDUCED MODAL HEIGHT ---
        modal_height = window_height * 0.65  # Reduced from 0.7 or 0.8
        
        self.modal_container = ft.Container(
            content=ft.GestureDetector(
                content=self.create_draggable_modal(),
                on_pan_start=self.on_pan_start, on_pan_update=self.on_pan_update,
                on_pan_end=self.on_pan_end, on_tap=self.toggle_modal,
            ),
            width=modal_width,
            height=modal_height, # Use the new reduced height
            left=(window_width - modal_width) / 2,
            top=window_height * self.modal_position
        )

        self.page.add(ft.Stack([main_content, self.modal_container], expand=True))
        self.page.update()

    def show_summary_view(self, candidate: dict):
        """Clears the page and redraws it with the summary view."""
        self.page.controls.clear()

        intro_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8,
            content=ft.Column([
                ft.Text(f"Introducing, {candidate['name']}!", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Address: {candidate['address']}", size=14),
                ft.Text(f"Phone: {candidate['phone']}", size=14),
            ])
        )
        rank_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#F9E79F",
            content=ft.Column([
                ft.Text(f"#{candidate['rank']:02}", size=36, weight=ft.FontWeight.BOLD),
                ft.Text(f"#{candidate['total_candidates']} candidates", size=16),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        birth_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#A9DFBF",
            content=ft.Column([
                ft.Text("Birth On?", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(candidate['birth_date'], size=24, weight=ft.FontWeight.BOLD),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        skills_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8,
            content=ft.Column([ft.Text("Skills", size=24, weight=ft.FontWeight.BOLD), ft.Text(candidate['skills'], size=16)])
        )
        job_history_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#E8DAEF", expand=True,
            content=ft.Column([
                ft.Text("Job History", size=24, weight=ft.FontWeight.BOLD),
                ft.Column(
                    controls=[ft.Column([ft.Text(f"● {job['title']}", weight=ft.FontWeight.BOLD), ft.Text(job['period'], size=12, italic=True), ft.Text(job['desc'], size=14)], spacing=2) for job in candidate['job_history']],
                    spacing=15, scroll=ft.ScrollMode.AUTO
                )
            ])
        )
        education_card = ft.Container(
            padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#D4E6F1",
            content=ft.Column([
                ft.Text("Education", size=24, weight=ft.FontWeight.BOLD),
                ft.Column(
                     controls=[ft.Column([ft.Text(f"● {edu['degree']}", weight=ft.FontWeight.BOLD), ft.Text(edu['period'], size=12, italic=True), ft.Text(edu['desc'], size=14)], spacing=2) for edu in candidate['education']],
                     spacing=15, scroll=ft.ScrollMode.AUTO
                )
            ])
        )
        back_button = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, color='white'), ft.Text("Back", color='white', size=20, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor='black', padding=15, border_radius=8, on_click=self.show_main_view, tooltip="Go back to results"
        )
        
        summary_layout = ft.Column([
            self.create_header(),
            ft.Container(
                padding=20, expand=True,
                content=ft.Row([
                    ft.Column([intro_card, ft.Row([rank_card, birth_card], spacing=20, expand=True), skills_card], spacing=20, expand=2),
                    ft.Column([job_history_card], expand=2),
                    ft.Column([education_card, back_button], spacing=20, expand=2),
                ], spacing=20, expand=True)
            )
        ], expand=True)

        self.page.add(summary_layout)
        self.page.update()

    def main(self, page: ft.Page):
        self.page = page
        page.title = "CV ATS Search"
        page.bgcolor = "#FFFFFF"
        page.padding = 0
        page.window_width = 1400
        page.window_height = 900
        page.on_resize = self.on_page_resize
        self.setup_database()
        self.load_data_from_db()
        
        # Start by showing the main view, which includes the peeking modal
        self.show_main_view()

def main(page: ft.Page):
    app = CVATSSearchApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)