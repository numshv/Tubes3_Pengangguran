import flet as ft
from datetime import datetime
import mysql.connector
from mysql.connector import errorcode
import os
import webbrowser
import re
import time
import threading
import concurrent.futures
import queue
from pathlib import Path
import re


from Solver.kmp import kmp
from Solver.BM import boyer_moore
from Solver.levenshtein import fuzzy_match
from Solver.aho_corasic import aho_corasic, build_trie
from Utils.utils import flatten_file_for_pattern_matching, flatten_file_for_regex_multicolumn
from Utils.ResultStruct import ResultStruct
from Database.encryption import Cipher


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
        self.search_stats = {}

        self.algo_dropdown = ft.Ref[ft.Dropdown]()
        self.keyword_input = ft.Ref[ft.TextField]()
        self.top_search_input = ft.Ref[ft.TextField]()
        self.results_grid = ft.Ref[ft.GridView]()
        self.stats_text = ft.Ref[ft.Text]()
        self.time_display = ft.Ref[ft.Text]()
        self.modal_container = ft.Container()

        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Azkarayan',
            'database': 'pengangguran2',
            'port': 3307
        }
        self.secret_key = "RAHASIA"

        self.loading_indicator_db = ft.ProgressRing(width=50, height=50)
        self.loading_indicator_pdf_cache = ft.ProgressRing(width=50, height=50)
        self.pdf_cache_progress_text = ft.Ref[ft.Text]()

        self.project_root_dir = Path(__file__).parent.parent
        self.results_lock = threading.Lock()

        self.cached_cv_data = {} 
        self.all_applicants_data = []
        self.progress_queue = queue.Queue()

    def setup_database_async(self):
        self.page.add(ft.Column([
            ft.Container(expand=True),
            ft.Row([self.loading_indicator_db, ft.Text("Setting up database...", size=18)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(expand=True)
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        self.page.update()

        success_db = self.setup_database()
        if not success_db:
            self.page.controls.clear()
            self.page.add(ft.Column([
                ft.Container(expand=True),
                ft.Text("Database setup failed. Please check console for errors.", color=ft.colors.RED, size=18),
                ft.Container(expand=True)
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            self.page.update()
            return

        self.page.controls.clear()
        self.page.add(ft.Column([
            ft.Container(expand=True),
            ft.Row([
                self.loading_indicator_pdf_cache, 
                ft.Column([
                    ft.Text("Caching PDF content...", size=18),
                    ft.Text(ref=self.pdf_cache_progress_text, size=14, color=ft.colors.BLACK54)
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(expand=True)
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        self.page.update()
        
        success_cache = self.cache_pdfs_async()
        
        self.page.controls.clear()
        if success_cache:
            self.show_main_view()
            self.update_modal_position(animate=False)
        else:
            self.page.add(ft.Column([
                ft.Container(expand=True),
                ft.Text("PDF caching failed. Search performance might be affected.", color=ft.colors.ORANGE_800, size=18),
                ft.Container(expand=True)
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            self.show_main_view()
            self.update_modal_position(animate=False)
        self.page.update()


    def setup_database(self):
        print("--- Initializing Database Setup ---")
        try:
            db_server_config = self.db_config.copy()
            db_server_config.pop('database', None)
            print("Trying to connect to MySQL server with db_config...")
            connection = mysql.connector.connect(**db_server_config)
            cursor = connection.cursor()
            print("Successfully connected to MySQL server from Python.")
            db_name = self.db_config['database']
            print(f"Checking for database '{db_name}' and using it...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {db_name}")
            print(f"Database '{db_name}' is ready.")

            schema_file_path = self.project_root_dir / "src" / "Database" / "schema.sql"
            if not schema_file_path.exists():
                print(f"Error: schema.sql not found at {schema_file_path}")
                return False

            with open(schema_file_path, 'r', encoding='utf8') as f:
                sql_script = f.read()
            
            commands_to_execute = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
            
            for command in commands_to_execute:
                if command:
                    try:
                        cursor.execute(command)
                        connection.commit()
                        print(f"Executed: {command[:50]}...")
                    except mysql.connector.Error as err:
                        print(f"Failed to execute SQL command: {command[:50]}... Error: {err}")
                        connection.rollback()
                        return False

            print("Database schema and data loaded from provided SQL.")
            
            from Database.seeder import encrypt_all_profiles
            encrypt_all_profiles(self.db_config, self.secret_key)

            if connection.is_connected():
                connection.close()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return False

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            else:
                print(f"Database setup failed: {err}")
            return False

    
    def open_pdf_viewer(self, cv_path: str):
        try:
            abs_path = str(self.project_root_dir / cv_path)
            if not os.path.exists(abs_path):
                print(f"Error: File tidak ditemukan di {abs_path}")
                return
            webbrowser.open_new_tab(f'file://{abs_path}')
        except Exception as e:
            print(f"Gagal membuka file PDF: {e}")

    def perform_search(self, e):
        self.search_stats = {}
        if self.stats_text.current:
            self.stats_text.current.value = ""
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
        loading_indicator = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center,
            expand=True
        )
        self.results_grid.current.controls = [loading_indicator]
        self.page.update()
        self.search_results = self._search_logic(
            keywords=keywords_text,
            algo_choice=algo_choice,
            top_choice=top_choice
        )
        self.update_results_display()
        print("Search and UI update complete.")
    
    def _cache_single_pdf(self, applicant_id: int, cv_path_relative: str, progress_queue: queue.Queue):
        """Helper function to cache a single PDF file's content."""
        full_cv_path = str(self.project_root_dir / cv_path_relative)
        try:
            flat_text = flatten_file_for_pattern_matching(full_cv_path).lower()
            regex_text = flatten_file_for_regex_multicolumn(full_cv_path)
            self.cached_cv_data[applicant_id] = {'flat_text': flat_text, 'regex_text': regex_text}
        except Exception as e:
            print(f"Error caching {full_cv_path}: {e}")
            self.cached_cv_data[applicant_id] = {'flat_text': "Error:", 'regex_text': "Error:"}
        finally:
            progress_queue.put(1)

    def cache_pdfs_async(self):
        all_applicants_details = []
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            query = "SELECT p.applicant_id, d.cv_path FROM ApplicantProfile p JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id"
            cursor.execute(query)
            all_applicants_details = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Failed to fetch applicant CV paths from DB: {err}")
            return False 
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()

        self.total_pdfs_to_cache = len(all_applicants_details)
        self.pdfs_cached_count = 0
        
        self.update_caching_progress_ui()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self._cache_single_pdf, app['applicant_id'], app['cv_path'], self.progress_queue) for app in all_applicants_details]
            
            threading.Thread(target=self._monitor_caching_progress, daemon=True).start()
            
            concurrent.futures.wait(futures)
        
        self.update_caching_progress_ui()
        print("PDF Caching complete.")
        return True


    def _monitor_caching_progress(self):
        while self.pdfs_cached_count < self.total_pdfs_to_cache:
            try:
                processed_count = self.progress_queue.get(timeout=0.1)
                self.pdfs_cached_count += processed_count
                self.update_caching_progress_ui()
            except queue.Empty:
                pass
        self.update_caching_progress_ui()


    def update_caching_progress_ui(self):
        if self.total_pdfs_to_cache > 0:
            progress_value = self.pdfs_cached_count / self.total_pdfs_to_cache
            self.loading_indicator_pdf_cache.value = progress_value 
            self.pdf_cache_progress_text.current.value = f"{self.pdfs_cached_count}/{self.total_pdfs_to_cache} PDFs cached"
        else:
            self.loading_indicator_pdf_cache.value = 0
            self.pdf_cache_progress_text.current.value = "0/0 PDFs cached"
        if self.page:
            self.page.update()


    def _run_exact_match_for_applicant(self, applicant, keyword_list, algo_choice, aho_corasick_trie_data=None):
        applicant_id = applicant['applicant_id']
        
        cached_data = self.cached_cv_data.get(applicant_id)
        if not cached_data or "Error:" in cached_data['flat_text']:
            return None
        
        flat_text = cached_data['flat_text'].lower()
        
        current_applicant_exact_matches = {}
        current_applicant_total_exact_match = 0
        if algo_choice == "Aho-Corasick":
            all_matches = aho_corasic(aho_corasick_trie_data, flat_text)
            for i, keyword in enumerate(keyword_list):
                if all_matches[i] > 0:
                    current_applicant_exact_matches[keyword] = current_applicant_exact_matches.get(keyword, 0) + all_matches[i]
                    current_applicant_total_exact_match += all_matches[i]
        else:
            for keyword in keyword_list:
                exact_matches = kmp(flat_text, keyword) if algo_choice == "KMP" else boyer_moore(flat_text, keyword)
                if exact_matches > 0:
                    current_applicant_exact_matches[keyword] = current_applicant_exact_matches.get(keyword, 0) + exact_matches
                    current_applicant_total_exact_match += exact_matches
        if current_applicant_total_exact_match > 0:
            result = ResultStruct(iID=applicant_id, iFirstName=f"{applicant['first_name']}", iLastName=f"{applicant['last_name']}", iDOB=applicant['date_of_birth'].strftime("%d/%m/%Y") if applicant['date_of_birth'] else "N/A", iAddress=applicant['address'], iPhone=applicant['phone_number'])
            result.cv_path = applicant.get('cv_path')
            result.stringForRegex = cached_data['regex_text']
            result.keywordMatches = current_applicant_exact_matches
            result.totalMatch = current_applicant_total_exact_match
            return result
        return None

    def _run_fuzzy_match_for_applicant(self, applicant, keyword_list, max_distance):
        applicant_id = applicant['applicant_id']
        
        cached_data = self.cached_cv_data.get(applicant_id)
        if not cached_data or "Error:" in cached_data['flat_text']:
            return None
        
        flat_text = cached_data['flat_text'].lower()
        
        fuzzy_applicant_total_match = 0
        fuzzy_applicant_keyword_matches = {}
        for keyword in keyword_list:
            fuzzy_matches = fuzzy_match(flat_text, keyword, max_distance)
            if fuzzy_matches > 0:
                fuzzy_applicant_keyword_matches[keyword] = fuzzy_matches
                fuzzy_applicant_total_match += fuzzy_matches
        if fuzzy_applicant_total_match > 0:
            result = ResultStruct(iID=applicant_id, iFirstName=f"{applicant['first_name']}", iLastName=f"{applicant['last_name']}", iDOB=applicant['date_of_birth'].strftime("%d/%m/%Y") if applicant['date_of_birth'] else "N/A", iAddress=applicant['address'], iPhone=applicant['phone_number'])
            result.totalMatch = fuzzy_applicant_total_match
            result.keywordMatches = fuzzy_applicant_keyword_matches
            result.cv_path = applicant.get('cv_path')
            result.stringForRegex = cached_data['regex_text']
            return result
        return None


    def _search_logic(self, keywords: str, algo_choice: str, top_choice: int, max_distance: int = 2):
        print(f"--- Starting Search with {algo_choice} (Top {top_choice if top_choice != float('inf') else 'All'}) ---")
        all_applicants = []
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            query = "SELECT p.applicant_id, p.first_name, p.last_name, p.date_of_birth, p.address, p.phone_number, d.application_role, d.cv_path FROM ApplicantProfile p JOIN ApplicantDetail d ON p.applicant_id = d.applicant_id"
            cursor.execute(query)
            all_applicants = cursor.fetchall()
            num_total_applicants = len(all_applicants)
        except mysql.connector.Error as err:
            print(f"Failed to fetch applicants from DB: {err}")
            return []
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()

        keyword_list = [kw.strip().lower() for kw in keywords.split(',') if kw.strip()]
        final_results_dict = {}
        
        aho_corasick_trie_data = None
        if algo_choice == "Aho-Corasick":
            print("Building Aho-Corasick Trie...")
            aho_corasick_trie_data = build_trie(keyword_list)
            print("Aho-Corasick Trie built.")

        print("--- Phase 1: Performing Exact Search ---")
        start_time_exact = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            exact_search_futures = {executor.submit(self._run_exact_match_for_applicant, applicant, keyword_list, algo_choice, aho_corasick_trie_data): applicant for applicant in all_applicants}
            for future in concurrent.futures.as_completed(exact_search_futures):
                applicant = exact_search_futures[future]
                try:
                    result = future.result()
                    if result:
                        with self.results_lock:
                            final_results_dict[result.id] = result
                except Exception as exc:
                    print(f'{applicant.get("first_name")} generated an exception during exact search: {exc}')
        end_time_exact = time.perf_counter()
        self.search_stats['exact_time'] = (end_time_exact - start_time_exact) * 1000
        self.search_stats['exact_count'] = num_total_applicants
        if len(final_results_dict) >= top_choice:
            print("Top choice reached with exact matches. Skipping fuzzy search.")
            self.search_stats['fuzzy_time'] = 0
            self.search_stats['fuzzy_count'] = 0
        else:
            print("--- Phase 2: Performing Fuzzy Search on remaining candidates ---")
            fuzzy_scanned_count = 0
            start_time_fuzzy = time.perf_counter()
            remaining_applicants = [app for app in all_applicants if app['applicant_id'] not in final_results_dict]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                fuzzy_search_futures = {executor.submit(self._run_fuzzy_match_for_applicant, applicant, keyword_list, max_distance): applicant for applicant in remaining_applicants}
                for future in concurrent.futures.as_completed(fuzzy_search_futures):
                    if len(final_results_dict) >= top_choice:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    applicant = fuzzy_search_futures[future]
                    fuzzy_scanned_count += 1
                    try:
                        result = future.result()
                        if result:
                            with self.results_lock:
                                final_results_dict[result.id] = result
                    except Exception as exc:
                        print(f'{applicant.get("first_name")} (fuzzy) generated an exception: {exc}')
            
            end_time_fuzzy = time.perf_counter()
            self.search_stats['fuzzy_time'] = (end_time_fuzzy - start_time_fuzzy) * 1000
            self.search_stats['fuzzy_count'] = fuzzy_scanned_count

        final_results = list(final_results_dict.values())
        final_results.sort(key=lambda r: r.totalMatch, reverse=True)
        print(f"--- Search Finished. Found {len(final_results)} matching candidates. ---")
        return final_results[:top_choice]

    def create_result_card(self, result: ResultStruct):
        keyword_list = [ft.Text(f"- {keyword}: {count}x", size=12, color=ft.Colors.BLACK54) for keyword, count in result.keywordMatches.items()]
        return ft.Container(
            height=255,
            width=280,
            padding=15, 
            border=ft.border.all(1, ft.Colors.BLACK), 
            border_radius=8, 
            bgcolor='#F0EFFF',
            content=ft.Column(
                controls=[
                    ft.Text(Cipher.vigenere_decrypt(result.firstName, self.secret_key) + " " + Cipher.vigenere_decrypt(result.lastName, self.secret_key), size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    ft.Text(f"{result.totalMatch} total matches", size=12, color=ft.Colors.BLACK54),
                    ft.Text("Matched keywords:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                    ft.Column(keyword_list, spacing=2, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
                    ft.Row(
                        [
                            ft.FilledButton(
                                text="Summary",
                                style=ft.ButtonStyle(bgcolor='#EACD8C', color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}),
                                on_click=lambda _, r=result: self.show_summary_view(r)
                            ),
                            ft.FilledButton(
                                text="Show CV", 
                                style=ft.ButtonStyle(bgcolor='#EACD8C', color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=5), side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}),
                                on_click=lambda _, r=result: self.open_pdf_viewer(r.cv_path)
                            )
                        ]
                    )
                ], 
                spacing=5,
            ),
        )

    def create_search_settings_content(self):
        return ft.Column([
            ft.Text("Search Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Algorithm choice:", size=14, weight=ft.FontWeight.BOLD), 
                            ft.Dropdown(ref=self.algo_dropdown, width=250, options=[ft.dropdown.Option("KMP"), ft.dropdown.Option("BM"), ft.dropdown.Option("Aho-Corasick")], value="KMP", bgcolor='#FFF9EB', filled=True,fill_color="#FFF9EB"),
                            ft.Text("Top choice (optional):", size=14, weight=ft.FontWeight.BOLD), 
                            ft.TextField(ref=self.top_search_input, hint_text="e.g., 5", width=250, border_color=ft.Colors.BLACK, keyboard_type=ft.KeyboardType.NUMBER, bgcolor='#FFF9EB')
                        ],
                        spacing=10
                    ),
                    ft.Column(
                        [
                            ft.Text("Keywords (comma-separated):", size=14, weight=ft.FontWeight.BOLD), 
                            ft.TextField(ref=self.keyword_input, hint_text="e.g., python, data science", multiline=True, min_lines=5, border_color=ft.Colors.BLACK, expand=True, bgcolor='#FFF9EB'),
                            ft.Row(
                                [
                                    ft.ElevatedButton("🔍 Search", bgcolor="#28A745", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)), on_click=self.perform_search)
                                ],
                                alignment=ft.MainAxisAlignment.END
                            )
                        ],
                        spacing=10,
                        expand=True
                    )
                ],
                spacing=20,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    def update_results_display(self):
        stats = self.search_stats
        stat_string = ""
        if stats.get('exact_count', 0) > 0:
            stat_string += f"Exact Match: {stats['exact_count']} CVs in {stats['exact_time']:.2f}ms."
        if stats.get('fuzzy_count', 0) > 0:
            stat_string += f"\nFuzzy Match: {stats['fuzzy_count']} CVs in {stats['fuzzy_time']:.2f}ms."

        if self.stats_text.current:
            self.stats_text.current.value = stat_string
        
        if not self.search_results:
            self.results_grid.current.controls = [ft.Row([ft.Text("No matching candidates found.")], alignment=ft.MainAxisAlignment.CENTER)]
        else:
            self.results_grid.current.controls = [self.create_result_card(result) for result in self.search_results]
        self.page.update()

    def show_main_view(self, e=None):
        """
        Builds and displays the main application view.
        """
        self.page.controls.clear()
        
        main_content = ft.Container(
            content=ft.Column(
                [
                    self.create_header(),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("Results", size=28, weight=ft.FontWeight.BOLD),
                                        ft.Container(expand=True),
                                        ft.Text(ref=self.stats_text, text_align=ft.TextAlign.RIGHT, color=ft.Colors.BLACK54)
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.GridView(
                                    ref=self.results_grid,
                                    expand=True,
                                    runs_count=5,
                                    max_extent=300,
                                    child_aspect_ratio=1.0,
                                    spacing=20,
                                    run_spacing=20,
                                    controls=[self.create_result_card(result) for result in self.search_results] if self.search_results else [ft.Row([ft.Text("Perform a search to see results.")], alignment=ft.MainAxisAlignment.CENTER)]
                                )
                            ],
                            expand=True
                        ),
                        padding=20,
                        margin=ft.margin.only(top=10),
                        expand=True
                    )
                ],
                expand=True
            ),
            expand=True,
        )

        self.modal_container.content = ft.GestureDetector(
            content=self.create_draggable_modal(),
            on_pan_start=self.on_pan_start, on_pan_update=self.on_pan_update,
            on_pan_end=self.on_pan_end, on_tap=self.toggle_modal,
        )
        self.modal_container.height=(self.page.window.height or 900) * 0.65
        
        self.page.add(ft.Stack([main_content, self.modal_container], expand=True))
        self.page.update()
    
    def main(self, page: ft.Page):
        self.page = page
        page.title = "CV ATS Search"
        page.bgcolor = "#FFFFFF"
        page.padding = 0
        page.window.width = 1400
        page.window.height = 900
        page.on_resized = self.on_page_resize
        
        threading.Thread(target=self.setup_database_async).start()
        threading.Thread(target=self.update_clock, daemon=True).start()

    def update_clock(self):
        while True:
            current_time = datetime.now().strftime("%H.%M")
            if self.time_display.current:
                self.time_display.current.value = current_time
                self.page.update()
            time.sleep(1)


    def create_header(self):
        return ft.Container(
            content=ft.Row([
                ft.Text("LOGO", size=20, weight=ft.FontWeight.BOLD, color="#E74C3C"),
                ft.Container(expand=True),
                ft.Text("CV ATS Search", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.Container(expand=True),
                ft.Text(ref=self.time_display, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK)
            ]),
            padding=20,
            bgcolor='#FFF9EB',
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.BLACK))
        )

    def create_draggable_modal(self):
        return ft.Container(content=ft.Column([self.create_modal_handle(), ft.Container(content=self.create_search_settings_content(), padding=20, expand=True)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#eaf4f4", border=ft.border.all(1, ft.Colors.BLACK), border_radius=ft.border_radius.only(top_left=15, top_right=15))

    def create_modal_handle(self):
        return ft.Container(content=ft.Container(height=5, width=40, bgcolor=ft.Colors.BLACK54, border_radius=3), padding=15, alignment=ft.alignment.center)

    def on_pan_start(self, e: ft.DragStartEvent):
        self.drag_start_y = e.global_y
        if self.page and self.page.window.height > 0: self.modal_start_position = self.modal_container.top / self.page.window.height
        else: self.modal_start_position = self.modal_position

    def on_pan_update(self, e: ft.DragUpdateEvent):
        if self.page and self.page.window.height > 0:
            delta_y = e.global_y - self.drag_start_y
            new_position = self.modal_start_position + (delta_y / self.page.window.height)
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
        if self.modal_container and self.page and self.page.window.height and self.page.window.width:
            window_height = self.page.window.height
            window_width = self.page.window.width
            
            self.modal_container.animate_position = ft.Animation(300, "decelerate") if animate else None
            self.modal_container.top = window_height * self.modal_position
            
            modal_width = window_width * 0.6
            self.modal_container.width = modal_width
            self.modal_container.left = (window_width - modal_width) / 2
            
            self.page.update()

    def on_page_resize(self, e):
        self.update_modal_position(animate=False)

    def _extract_section_content(self, full_text: str, headers: list[str], all_known_headers: list[str]) -> str:
        """Mengekstrak blok teks dari sebuah seksi (misal, 'Experience') hingga seksi berikutnya."""
        safe_headers = [re.escape(h) for h in headers]
        safe_stop_headers = [re.escape(h) for h in all_known_headers if h.lower() not in [header.lower() for header in headers]]

        start_pattern = r'^\s*(?:' + '|'.join(safe_headers) + r')\s*$'
        start_match = re.search(start_pattern, full_text, re.IGNORECASE | re.MULTILINE)
        
        if not start_match:
            return ""

        text_after_start = full_text[start_match.end():]
        first_stop_position = len(text_after_start)

        if safe_stop_headers:
            stop_pattern = r'^\s*(?:' + '|'.join(safe_stop_headers) + r')\s*$'
            stop_match = re.search(stop_pattern, text_after_start, re.IGNORECASE | re.MULTILINE)
            if stop_match:
                first_stop_position = stop_match.start()

        return text_after_start[:first_stop_position].strip()

    def _parse_structured_section(self, section_text: str) -> list[dict]:
        """MANAJER PARSER: Mencoba setiap 'pakar' parser pekerjaan."""
        if not section_text: return []
        
        job_parsers = [
            self._parse_jobs_format_specific,
            self._parse_jobs_format_general,
            self._parse_jobs_flexible,
        ]

        for parser in job_parsers:
            try:
                entries = parser(section_text)
                if entries:
                    print(f"Job History parsed with: {parser.__name__}")
                    return entries
            except Exception as e:
                print(f"Parser {parser.__name__} failed: {e}")
        
        print("All job parsers failed.")
        return []
    
    def _parse_jobs_flexible(self, section_text: str) -> list[dict]:
        """
        [PAKAR UTAMA] Menangani berbagai format riwayat pekerjaan dengan fokus pada senioritas.
        """
        entries = []
        
        date_range_pattern = r"""
            (?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{1,2}[/-]\d{4}) # Tanggal mulai
            \s*(?:to|-|hingga|sampai)\s* # Pemisah
            (?:Current|Present|Sekarang|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})|(?:\d{1,2}[/-]\d{4})) # Tanggal selesai
        """
        
        job_title_pattern = r"""
            \b(?:Lead|Senior|Junior|Head\s+of|Manager|Staff|Intern|Specialist|Coordinator|Director|Engineer|Developer|Analyst|Designer)\b[\w\s-]*
        """
        
        blocks = re.split(r'\n\s*\n+', section_text.strip())
        
        for block in blocks:
            if not block.strip():
                continue

            title = "N/A"
            period = "N/A"
            description = block

            period_match = re.search(date_range_pattern, description, re.IGNORECASE | re.VERBOSE)
            if period_match:
                period = period_match.group(0).strip()
                description = description.replace(period, '').strip()
            
            title_match = re.search(job_title_pattern, description, re.IGNORECASE | re.VERBOSE)
            if title_match:
                title = title_match.group(0).strip()
                description = description.replace(title, '').strip()
            else:
                lines = description.strip().split('\n')
                if lines:
                    title = lines[0].strip()
                    description = '\n'.join(lines[1:]).strip()

            cleaned_desc = '\n'.join([line.lstrip('•●- ').strip() for line in description.split('\n') if line.strip()])

            entries.append({
                'title': title,
                'period': period,
                'desc': cleaned_desc
            })
            
        return [e for e in entries if e['title'] != 'N/A' or e['desc']]

    def _parse_jobs_format_specific(self, section_text: str) -> list[dict]:
        """PAKAR 1: Menangani format terstruktur (termasuk bullet point)."""
        splitter_pattern = re.compile(r"""
            \n\s*
            (?=
                (?:^\s*●\s[^\n]+\n\s*\d{2}/\d{4}\s*-\s*\d{2}/\d{4})
                |
                (?:^\s*\d{2}/\d{4}\s*-\s*\d{2}/\d{4}\s*$)
            )
        """, re.MULTILINE | re.VERBOSE)

        raw_entries = splitter_pattern.split(section_text)
        if len(raw_entries) <= 1: return []

        parsed_entries = []
        for entry_text in raw_entries:
            lines = [line.strip() for line in entry_text.strip().split('\n') if line.strip()]
            if lines:
                entry = self._parse_single_block_specific(lines)
                if entry:
                    parsed_entries.append(entry)
        return parsed_entries

    def _parse_jobs_format_general(self, section_text: str) -> list[dict]:
        """PAKAR 2: Menangani format 'acak' dengan memecah per baris kosong lalu menggabungkan."""
        entries = []
        date_pattern = re.compile(r"""
            ^
            (
                (?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})
                |
                (?:\d{1,2}/\d{4})
            )
            \s*(?:to|-)\s*
            (?:Current|Present|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})|(?:\d{1,2}/\d{4}))
            $
        """, re.IGNORECASE | re.VERBOSE)

        current_entry = {}
        blocks = re.split(r'\n\s*\n+', section_text)

        for block in blocks:
            lines = block.strip().split('\n')
            first_line = lines[0].strip()

            if date_pattern.match(first_line):
                if current_entry.get('title') and current_entry.get('desc'):
                    entries.append(current_entry)
                
                current_entry = {'period': first_line, 'desc': ''}
                
                if len(lines) > 1:
                    title_info = "\n".join(lines[1:])
                    current_entry['title'] = title_info
                
            elif 'Company Name' in first_line or 'City, State' in "\n".join(lines):
                if current_entry.get('title') and current_entry.get('desc'):
                     entries.append(current_entry)
                     current_entry = {} # Reset
                
                current_entry['title'] = block
                if 'period' not in current_entry:
                    current_entry['period'] = 'N/A'
                if 'desc' not in current_entry:
                    current_entry['desc'] = ''

            elif current_entry:
                if 'desc' not in current_entry:
                    current_entry['desc'] = ''
                current_entry['desc'] += ('\n' if current_entry['desc'] else '') + block
        
        if current_entry.get('title'):
            entries.append(current_entry)

        return entries

    def _parse_single_block_specific(self, lines: list[str]) -> dict:
        """HELPER: Mem-parse blok tunggal dari parser spesifik."""
        if not lines: return None
        
        if lines[0].strip().startswith('●') and len(lines) > 1 and re.fullmatch(r'\d{2}/\d{4}\s*-\s*\d{2}/\d{4}', lines[1].strip()):
            title = lines[0].strip()[1:].strip()
            period = lines[1].strip()
            desc_lines = [l.strip()[1:].strip() if l.strip().startswith('●') else l.strip() for l in lines[2:] if l.strip().lower() != 'n/a']
            return {'title': title, 'period': period, 'desc': '\n'.join(desc_lines)}

        elif re.fullmatch(r'\d{2}/\d{4}\s*-\s*\d{2}/\d{4}', lines[0].strip()):
            period = lines[0].strip()
            title = lines[1] if len(lines) > 1 else "N/A"
            description = '\n'.join(lines[2:])
            return {'title': title, 'period': period, 'desc': description}
        return None


    def _parse_education_section(self, section_text: str) -> list[dict]:
        """MANAJER PARSER PENDIDIKAN."""
        if not section_text: return []
        
        edu_parsers = [
            self._parse_education_format_classic,
            self._parse_education_format_year_first,
            self._parse_education_flexible,
        ]

        for parser in edu_parsers:
            try:
                entries = parser(section_text)
                if entries:
                    print(f"Education parsed with: {parser.__name__}")
                    return entries
            except Exception as e:
                print(f"Parser {parser.__name__} failed: {e}")
        
        print("All education parsers failed.")
        return []

    def _parse_education_format_classic(self, section_text: str) -> list[dict]:
        """PAKAR PENDIDIKAN 1: Menangani format NAMA_UNIV [Tahun] [Gelar]."""
        entries = []
        pattern = re.compile(
            r"^(?P<school>[A-Z\s,]+(?:UNIVERSITY|COLLEGE))\s*.*?(?P<year>\d{4})\s+(?P<degree>[^\n]+(?:\n[^\n]+)*)",
            re.MULTILINE | re.IGNORECASE
        )
        
        for match in pattern.finditer(section_text):
            data = match.groupdict()
            desc = f"School: {data['school'].strip()}"
            gpa_search = re.search(r"GPA:\s*([\d\.]+)", data['degree'])
            if gpa_search:
                desc += f"\nGPA: {gpa_search.group(1)}"
            
            degree_clean = re.sub(r'gpa:.*','', data['degree'], flags=re.IGNORECASE).strip()

            entries.append({
                'title': degree_clean,
                'period': data['year'],
                'desc': desc
            })
        return entries

    def _parse_education_flexible(self, section_text: str) -> list[dict]:
        """[PAKAR UTAMA] Menangani berbagai format pendidikan dengan memisahkan gelar dan institusi."""
        entries = []
        
        degree_pattern = r"""
            \b(?:
                Master(?:\s+of\s+[\w\s]+)? | Bachelor(?:\s+of\s+[\w\s]+)? |
                Sarjana(?:\s+[\w\s,]+)? | Diploma(?:\s+[\w\d]+)? |
                Ph\.?D\.? | M\.?Sc\.? | M\.?B\.?A\.? | S\.?\s?\w{2,}\. |
                S-?\d | D-?\d
            )\b
        """
        institution_pattern = r"""
            \b(?:
                University|Universitas|Institute|Institut|College|
                Sekolah\s+Tinggi|Politeknik|Academy|Akademi
            )[\w\s,.]*
        """
        year_pattern = r'\b(\d{4}(?:\s*(?:-|to|sampai|hingga)\s*\d{2,4})?)\b'
        
        blocks = re.split(r'\n\s*\n+', section_text.strip())

        for block in blocks:
            if not block.strip():
                continue
                
            title, period, inst_desc = "N/A", "N/A", ""
            remaining_block = block

            degree_match = re.search(degree_pattern, remaining_block, re.IGNORECASE | re.VERBOSE)
            if degree_match:
                title = degree_match.group(0).strip().replace('\n', ' ')
                remaining_block = remaining_block.replace(degree_match.group(0), '').strip()
            
            institution_match = re.search(institution_pattern, remaining_block, re.IGNORECASE | re.VERBOSE)
            if institution_match:
                inst_desc = institution_match.group(0).strip().replace('\n', ' ')
                remaining_block = remaining_block.replace(institution_match.group(0), '').strip()

            year_match = re.search(year_pattern, remaining_block)
            if year_match:
                period = year_match.group(1).strip()
                remaining_block = remaining_block.replace(period, '').strip()

            final_desc = (inst_desc + " " + remaining_block.replace('\n', ' ').strip()).strip()
            final_desc = re.sub(r'^\W+', '', final_desc) # Hapus non-alphanum di awal

            if title == "N/A":
                title = block.split('\n')[0]

            entries.append({
                'title': title,
                'period': period,
                'desc': final_desc
            })
            
        return [e for e in entries if e['title'] != "N/A" or e['desc']]

    def _parse_education_format_year_first(self, section_text: str) -> list[dict]:
        """PAKAR PENDIDIKAN 2: Menangani format Tahun lalu Nama Universitas."""
        lines = [line.strip() for line in section_text.split('\n') if line.strip()]
        if not lines or not re.fullmatch(r'\d{4}', lines[0]): return []

        period = lines[0]
        title_line = lines[1] if len(lines) > 1 else ""
        desc_lines = lines[2:]
        title = title_line.split(':')[1].strip() if ':' in title_line else title_line
        institution = title_line.split(':')[0].strip() if ':' in title_line else title_line
        description = f"{institution}\n" + '\n'.join(desc_lines)
        
        return [{'title': title, 'period': period, 'desc': description.strip()}]


    def _parse_single_job_entry(self, lines: list[str]) -> dict:
        """
        PARSER BLOK TUNGGAL: Khusus untuk mem-parse blok yang sudah dipisahkan oleh
        _parse_jobs_format_bullet_point.
        """
        if not lines:
            return None
            
        if lines[0].strip().startswith('●') and len(lines) > 1 and re.fullmatch(r'\d{2}/\d{4}\s*-\s*\d{2}/\d{4}', lines[1].strip()):
            title = lines[0].strip()[1:].strip()
            period = lines[1].strip()
            desc_lines = lines[2:]
            clean_desc_lines = []
            for line in desc_lines:
                stripped_line = line.strip()
                if stripped_line.lower() == 'n/a': continue
                if stripped_line.startswith('●'):
                    clean_desc_lines.append(stripped_line[1:].strip())
                else:
                    clean_desc_lines.append(stripped_line)
            description = '\n'.join(clean_desc_lines)
            return {'title': title, 'period': period, 'desc': description}

        elif re.fullmatch(r'\d{2}/\d{4}\s*-\s*\d{2}/\d{4}', lines[0].strip()):
            period = lines[0].strip()
            title_line = lines[1] if len(lines) > 1 else ""
            desc_lines = lines[2:] if len(lines) > 2 else []
            title_match = re.search(r'.*,\s*\w+\s+(.*)', title_line)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = title_line.split('∩╝')[-1].strip() if '∩╝' in title_line else title_line
            description = '\n'.join(line.strip() for line in desc_lines)
            return {'title': title, 'period': period, 'desc': description}
            
        return None
    
    def show_summary_view(self, candidate: ResultStruct):
        self.page.controls.clear()

        try:
            decrypted_name = Cipher.vigenere_decrypt(candidate.firstName, self.secret_key) + " " + Cipher.vigenere_decrypt(candidate.lastName, self.secret_key)
            decrypted_address = Cipher.vigenere_decrypt(candidate.address, self.secret_key)
            decrypted_phone = Cipher.vigenere_decrypt(candidate.phone, self.secret_key)
            decrypted_dob = Cipher.vigenere_decrypt(candidate.dob, self.secret_key)
        except Exception as e:
            print(f"Decryption failed for a field: {e}. Displaying raw data.")
            decrypted_name = f"{candidate.firstName} (Decryption Failed)"
            decrypted_address = f"{candidate.address} (Decryption Failed)"
            decrypted_phone = f"{candidate.phone} (Decryption Failed)"
            decrypted_dob = f"{candidate.dob} (Decryption Failed)"

        PRIMARY_SKILLS_HEADERS = ['skills', 'keahlian']
        SECONDARY_SKILLS_HEADERS = ['skills', 'keahlian', 'skill highlights', 'core qualifications', 'highlights']
        JOB_HEADERS = ['experience', 'work experience', 'professional experience', 'job history', 'pengalaman kerja', 'riwayat pekerjaan']
        EDU_HEADERS = ['education', 'education and training', 'pendidikan']
        ALL_KNOWN_HEADERS = PRIMARY_SKILLS_HEADERS + SECONDARY_SKILLS_HEADERS + JOB_HEADERS + EDU_HEADERS
        cv_text = candidate.stringForRegex
        skills_text = self._extract_section_content(cv_text, PRIMARY_SKILLS_HEADERS, ALL_KNOWN_HEADERS)
        if not skills_text:
            print("Primary skills section not found, trying secondary headers...")
            skills_text = self._extract_section_content(cv_text, SECONDARY_SKILLS_HEADERS, ALL_KNOWN_HEADERS)
        job_text = self._extract_section_content(cv_text, JOB_HEADERS, ALL_KNOWN_HEADERS)
        edu_text = self._extract_section_content(cv_text, EDU_HEADERS, ALL_KNOWN_HEADERS)
        
        job_history_list = self._parse_structured_section(job_text)
        education_list = self._parse_education_section(edu_text)
        
        intro_card = ft.Container(padding=20, border=ft.border.all(2, ft.Colors.OUTLINE), border_radius=8, content=ft.Column([ft.Text(f"Introducing, {decrypted_name}!", size=24, weight=ft.FontWeight.BOLD), ft.Text(f"Address: {decrypted_address}", size=14), ft.Text(f"Phone: {decrypted_phone}", size=14)]))
        
        rank_card = ft.Container(
            padding=20, 
            border=ft.border.all(2, ft.Colors.OUTLINE), 
            border_radius=8, 
            bgcolor="#F9E79F", 
            height=120,  # Fixed height
            content=ft.Column([
                ft.Text(f"#{self.search_results.index(candidate) + 1:02}", size=36, weight=ft.FontWeight.BOLD), 
                ft.Text(f"of {len(self.search_results)} results", size=16)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, run_alignment=ft.MainAxisAlignment.CENTER),
            expand=True
        )

        birth_card = ft.Container(
            padding=20, 
            border=ft.border.all(2, ft.Colors.OUTLINE), 
            border_radius=8, 
            bgcolor="#A9DFBF", 
            height=120, 
            content=ft.Column([
                ft.Text("Birth Date", size=18, weight=ft.FontWeight.BOLD), 
                ft.Text(decrypted_dob, size=16, weight=ft.FontWeight.BOLD)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, run_alignment=ft.MainAxisAlignment.CENTER),
            expand=True
        )
        
        skills_card = ft.Container(padding=20, border=ft.border.all(2, ft.Colors.OUTLINE), border_radius=8, content=ft.Column([ft.Text("Skills", size=24, weight=ft.FontWeight.BOLD), ft.Column([ft.Text(skills_text or "No skills section found.", size=16)], expand=True, scroll=ft.ScrollMode.ADAPTIVE)]), expand=True)
        job_history_card = ft.Container(padding=20, border=ft.border.all(2, ft.Colors.OUTLINE), border_radius=8, bgcolor="#E8DAEF", expand=True, content=ft.Column([ft.Text("Job History", size=24, weight=ft.FontWeight.BOLD), ft.Column(controls=[ft.Column([ft.Text(f"● {job['title']}", weight=ft.FontWeight.BOLD), ft.Text(job['period'], size=12, italic=True), ft.Text(job['desc'], size=14, selectable=True)], spacing=2, alignment=ft.MainAxisAlignment.START) for job in job_history_list] if job_history_list else [ft.Text("No job history found.")], spacing=15, scroll=ft.ScrollMode.ADAPTIVE, expand=True)]))
        education_card = ft.Container(padding=20, border=ft.border.all(2, ft.Colors.OUTLINE), border_radius=8, bgcolor="#D4E6F1", expand=True, content=ft.Column([ft.Text("Education", size=24, weight=ft.FontWeight.BOLD), ft.Column(controls=[ft.Column([ft.Text(f"● {edu['title']}", weight=ft.FontWeight.BOLD), ft.Text(edu['period'], size=12, italic=True), ft.Text(edu['desc'], size=14, selectable=True)], spacing=2, alignment=ft.MainAxisAlignment.START) for edu in education_list] if education_list else [ft.Text("No education history found.")], spacing=15, scroll=ft.ScrollMode.ADAPTIVE, expand=True)]))
        back_button = ft.Container(content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, color='white'), ft.Text("Back to Results", color='white', size=18, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER), bgcolor='black', padding=15, border_radius=8, on_click=self.show_main_view, tooltip="Go back to results")
        
        summary_layout = ft.Column([
            self.create_header(), 
            ft.Container(
                padding=20, 
                expand=True, 
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                intro_card, 
                                ft.Row([rank_card, birth_card], spacing=20), 
                                skills_card
                            ], 
                            spacing=20, 
                            expand=2
                        ), 
                        ft.Column([job_history_card], spacing=20, expand=3), 
                        ft.Column([education_card, back_button], spacing=20, expand=3)
                    ], 
                    spacing=20, 
                    expand=True
                )
            )
        ], 
        expand=True, 
        alignment=ft.MainAxisAlignment.START
    )
        self.page.add(summary_layout)
        self.page.update()

def main(page: ft.Page):
    app = CVATSSearchApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)