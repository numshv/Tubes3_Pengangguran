import flet as ft
from datetime import datetime
import mysql.connector
from mysql.connector import errorcode

# --- TAMBAHAN 1: Impor library untuk membuka file ---
import os
import webbrowser

from Database.seeder import run_seeding
from Solver.kmp import kmp
from Solver.BM import boyer_moore
from Solver.levenshtein import fuzzy_match
from Utils.utils import flatten_file_for_pattern_matching, flatten_file_for_regex_multicolumn
from Utils.ResultStruct import ResultStruct


class CVATSSearchApp:
    def __init__(self):
        self.page = None
        self.modal_open = False
        
        self.open_pos = 0.4     
        self.closed_pos = 0.75  
        self.modal_position = self.closed_pos

        self.drag_start_y = 0
        self.modal_start_position = 0

        self.search_results = []

        self.algo_dropdown = ft.Ref[ft.Dropdown]()
        self.keyword_input = ft.Ref[ft.TextField]()
        self.top_search_input = ft.Ref[ft.TextField]()
        self.results_grid = ft.Ref[ft.GridView]()

        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'n0um1sy1fa',
            'database': 'ats_pengangguran1'
        }

    # ... (setup_database tetap sama) ...
    def setup_database(self):
        print("--- Initializing Database Setup ---")
        try:
            db_server_config = self.db_config.copy()
            db_server_config.pop('database', None)
            
            connection = mysql.connector.connect(**db_server_config)
            cursor = connection.cursor()
            
            db_name = self.db_config['database']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {db_name}")
            print(f"Database '{db_name}' is ready.")

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
                    cursor.execute(table_sql)

                except mysql.connector.Error as err:
                    print(f"Failed creating table: {err}")

            cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
            if cursor.fetchone()[0] == 0:
                print("Database is empty. Running seeder...")
                connection.close()
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
    
    # --- TAMBAHAN 2: Fungsi untuk membuka file PDF ---
    def open_pdf_viewer(self, cv_path: str):
        """Membuka file PDF menggunakan aplikasi default sistem."""
        try:
            # Menggunakan realpath untuk mendapatkan path absolut yang kanonis
            abs_path = os.path.realpath(cv_path)
            if not os.path.exists(abs_path):
                print(f"Error: File tidak ditemukan di {abs_path}")
                # Anda bisa menampilkan dialog error di sini
                return
                
            # webbrowser lebih portabel untuk Windows, Mac, dan Linux
            webbrowser.open_new_tab(f'file://{abs_path}')
            print(f"Membuka file: {abs_path}")
        except Exception as e:
            print(f"Gagal membuka file PDF: {e}")


    def perform_search(self, e):
        algo_choice = self.algo_dropdown.current.value
        keywords_text = self.keyword_input.current.value
        top_search_text = self.top_search_input.current.value
        
        if not keywords_text:
            print("Search skipped. Keywords are empty.")
            return
        
        try:
            top_choice = int(top_search_text) if top_search_text else float('inf')
        except ValueError:
            print("Invalid 'Top choice' input. Defaulting to all results.")
            top_choice = float('inf')

        is_kmp_choice = True if algo_choice == "KMP" else False

        self.results_grid.current.controls = [ft.Row([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER)]
        self.page.update()

        self.search_results = self._search_logic(
            keywords=keywords_text,
            is_kmp=is_kmp_choice,
            top_choice=top_choice
        )
        
        self.update_results_display()
        print("Search and UI update complete.")

    # Ganti fungsi _search_logic Anda dengan yang ini

    def _search_logic(self, keywords: str, is_kmp: bool, top_choice: int, max_distance: int = 2):
        """
        Logika pencarian inti dengan aturan baru:
        1. Cari semua kecocokan TEPAT terlebih dahulu.
        2. Cari kecocokan FUZZY hanya untuk pelamar yang TIDAK ditemukan pada tahap 1.
        """
        print(f"--- Starting Search with New Logic (Top {top_choice if top_choice != float('inf') else 'All'}) ---")
        
        # Dapatkan semua data pelamar dari database
        all_applicants = []
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            query = "SELECT p.applicant_id, p.first_name, p.last_name, p.date_of_birth, p.address, p.phone_number, d.application_role, d.cv_path FROM ApplicantProfile p JOIN ApplicantDetail d ON p.applicant_id = d.applicant_id"
            cursor.execute(query)
            all_applicants = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Failed to fetch applicants from DB: {err}")
            return []
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()

        keyword_list = [kw.strip().lower() for kw in keywords.split(',') if kw.strip()]
        
        # Gunakan dictionary untuk menyimpan hasil agar mudah diakses berdasarkan ID
        final_results_dict = {}

        # --- FASE 1: PENCARIAN TEPAT (EXACT MATCHING) ---
        print("--- Phase 1: Performing Exact Search ---")
        for applicant in all_applicants:
            cv_path = applicant.get('cv_path')
            if not cv_path: continue

            flat_text = flatten_file_for_pattern_matching(cv_path).lower()
            if "Error:" in flat_text: continue

            for keyword in keyword_list:
                exact_matches = kmp(flat_text, keyword) if is_kmp else boyer_moore(flat_text, keyword)
                
                if exact_matches > 0:
                    applicant_id = applicant['applicant_id']
                    
                    # Jika pelamar ini belum ada di hasil, buat struct baru
                    if applicant_id not in final_results_dict:
                        final_results_dict[applicant_id] = ResultStruct(
                            iID=applicant_id,
                            iName=f"{applicant['first_name']} {applicant['last_name']}",
                            iDOB=applicant['date_of_birth'].strftime("%d/%m/%Y") if applicant['date_of_birth'] else "N/A",
                            iAddress=applicant['address'],
                            iPhone=applicant['phone_number']
                        )
                        final_results_dict[applicant_id].cv_path = cv_path
                        final_results_dict[applicant_id].stringForRegex = flatten_file_for_regex_multicolumn(cv_path)

                    # Tambahkan skor kecocokan
                    final_results_dict[applicant_id].keywordMatches[keyword] = final_results_dict[applicant_id].keywordMatches.get(keyword, 0) + exact_matches
                    final_results_dict[applicant_id].totalMatch += exact_matches

        # --- FASE 2: PENCARIAN FUZZY (FUZZY MATCHING) ---
        print("--- Phase 2: Performing Fuzzy Search on remaining candidates ---")
        for applicant in all_applicants:
            # Hentikan jika hasil sudah memenuhi kuota top_choice
            if len(final_results_dict) >= top_choice:
                break
                
            applicant_id = applicant['applicant_id']
            
            # LEWATI pelamar ini jika sudah ditemukan di FASE 1
            if applicant_id in final_results_dict:
                continue

            cv_path = applicant.get('cv_path')
            if not cv_path: continue

            flat_text = flatten_file_for_pattern_matching(cv_path).lower()
            if "Error:" in flat_text: continue

            # Hitung dulu kecocokan fuzzy untuk pelamar baru ini
            fuzzy_applicant_total_match = 0
            fuzzy_applicant_keyword_matches = {}

            for keyword in keyword_list:
                fuzzy_matches = fuzzy_match(flat_text, keyword, max_distance)
                if fuzzy_matches > 0:
                    fuzzy_applicant_keyword_matches[keyword] = fuzzy_matches
                    fuzzy_applicant_total_match += fuzzy_matches
            
            # Jika ada kecocokan fuzzy, buat struct baru dan tambahkan ke hasil
            if fuzzy_applicant_total_match > 0:
                result = ResultStruct(
                    iID=applicant_id,
                    iName=f"{applicant['first_name']} {applicant['last_name']}",
                    iDOB=applicant['date_of_birth'].strftime("%d/%m/%Y") if applicant['date_of_birth'] else "N/A",
                    iAddress=applicant['address'],
                    iPhone=applicant['phone_number']
                )
                result.totalMatch = fuzzy_applicant_total_match
                result.keywordMatches = fuzzy_applicant_keyword_matches
                result.cv_path = cv_path
                result.stringForRegex = flatten_file_for_regex_multicolumn(cv_path)
                final_results_dict[applicant_id] = result

        # Konversi dictionary hasil menjadi list
        final_results = list(final_results_dict.values())
        final_results.sort(key=lambda r: r.totalMatch, reverse=True)
        
        print(f"--- Search Finished. Found {len(final_results)} matching candidates. ---")
        return final_results[:top_choice]

    def create_result_card(self, result: ResultStruct):
        keyword_list = [ft.Text(f"- {keyword}: {count}x", size=12, color='black54') for keyword, count in result.keywordMatches.items()]
        
        return ft.Container(
            content=ft.Column([
                ft.Text(result.name, size=16, weight=ft.FontWeight.BOLD, color='black'),
                ft.Text(f"{result.totalMatch} total matches", size=12, color='black54'),
                ft.Container(
                    content=ft.Text("Matched keywords:", size=12, weight=ft.FontWeight.BOLD, color='black'),
                    margin=ft.margin.only(top=5)
                ),
                ft.Column(keyword_list, spacing=2),
                ft.Container(
                    content=ft.Row([
                        ft.FilledButton(
                            text="Summary",
                            style=ft.ButtonStyle(bgcolor='#EACD8C', color='black', shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}),
                            on_click=lambda _, r=result: self.show_summary_view(r)
                        ),
                        # --- TAMBAHAN 4: Hubungkan tombol ke fungsi open_pdf_viewer ---
                        ft.FilledButton(
                            text="Show CV", 
                            style=ft.ButtonStyle(bgcolor='#EACD8C', color='black', shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}),
                            on_click=lambda _, r=result: self.open_pdf_viewer(r.cv_path)
                        )
                    ]),
                    margin=ft.margin.only(top=10) 
                )
            ], spacing=4, tight=True),
            padding=15, border=ft.border.all(2, 'black'), border_radius=8, bgcolor='#F0EFFF', width=280,
        )

    # ... (Sisa kode lainnya tetap sama, tidak perlu diubah) ...
    def create_search_settings_content(self):
        return ft.Column([
            ft.Text("Search Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Column([
                    ft.Text("Algorithm choice:", size=14, weight=ft.FontWeight.BOLD), 
                    ft.Dropdown(
                        ref=self.algo_dropdown,
                        width=200, 
                        options=[ft.dropdown.Option("KMP"), ft.dropdown.Option("BM")], 
                        value="KMP"
                    )
                ]),
                ft.Column([
                    ft.Text("Keywords (comma-separated):", size=14, weight=ft.FontWeight.BOLD), 
                    ft.TextField(
                        ref=self.keyword_input,
                        hint_text="e.g., python, data science", 
                        multiline=True, min_lines=3, width=400, border_color='black'
                    )
                ])
            ], spacing=50, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.Column([
                    ft.Text("Top choice (optional):", size=14, weight=ft.FontWeight.BOLD), 
                    ft.TextField(
                        ref=self.top_search_input,
                        hint_text="e.g., 5", 
                        width=200, 
                        border_color='black',
                        keyboard_type=ft.KeyboardType.NUMBER
                    )
                ]),
                ft.ElevatedButton(
                    "🔍 Search", 
                    bgcolor="#28A745", color="white", 
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)), 
                    on_click=self.perform_search
                )
            ], spacing=50, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END)
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def update_results_display(self):
        if not self.search_results:
            self.results_grid.current.controls = [ft.Row([ft.Text("No matching candidates found.")], alignment=ft.MainAxisAlignment.CENTER)]
        else:
            self.results_grid.current.controls = [self.create_result_card(result) for result in self.search_results]
        self.page.update()

    def show_main_view(self, e=None):
        self.page.controls.clear()
        main_content = ft.Container(
            content=ft.Column([
                self.create_header(),
                ft.Container(
                    content=ft.Column([
                        ft.Container(content=ft.Text("Results", size=28, weight=ft.FontWeight.BOLD)),
                        ft.GridView(
                            ref=self.results_grid,
                            expand=True, runs_count=5, max_extent=300, child_aspect_ratio=0.8,
                            spacing=20, run_spacing=20,
                            controls=[ft.Row([ft.Text("Perform a search to see results.")], alignment=ft.MainAxisAlignment.CENTER)]
                        )
                    ]),
                    padding=20, expand=True
                )
            ]),
            expand=True
        )
        self.modal_container = ft.Container(
            content=ft.GestureDetector(
                content=self.create_draggable_modal(),
                on_pan_start=self.on_pan_start, on_pan_update=self.on_pan_update,
                on_pan_end=self.on_pan_end, on_tap=self.toggle_modal,
            ),
            width=(self.page.window_width or 1200) * 0.6,
            height=(self.page.window_height or 900) * 0.65,
            left=(((self.page.window_width or 1200) * 0.4) / 2)+50,
            top=(self.page.window_height or 900) * self.modal_position
        )
        self.page.add(ft.Stack([main_content, self.modal_container], expand=True))
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
        self.show_main_view()
    
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

    def create_draggable_modal(self):
        return ft.Container(
            content=ft.Column([self.create_modal_handle(), ft.Container(content=self.create_search_settings_content(), padding=20, expand=True)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#eaf4f4", border=ft.border.all(2, 'black'), border_radius=ft.border_radius.only(top_left=15, top_right=15),
        )

    def create_modal_handle(self):
        return ft.Container(content=ft.Container(height=5, width=40, bgcolor='black54', border_radius=3), padding=15, alignment=ft.alignment.center)

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
            
            modal_width = window_width * 0.6
            self.modal_container.left = (window_width - modal_width) / 2
            self.modal_container.width = modal_width
            
            self.page.update()

    def on_page_resize(self, e):
        if hasattr(self, 'modal_container'):
            self.update_modal_position(animate=False)

    def show_summary_view(self, candidate: ResultStruct):
        print(f"Showing summary for: {candidate.name}")
        pass

def main(page: ft.Page):
    app = CVATSSearchApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)