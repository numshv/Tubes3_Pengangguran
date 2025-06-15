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


from Database.seeder import run_seeding
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
            'database': 'ats_pengangguran2',
            'port': 3307
        }
        self.secret_key = "RAHASIA"
        self.loading_indicator_db = ft.ProgressRing(width=50, height=50)
        self.loading_text = ft.Text("Setting up database...", size=18)
        self.progress_bar = ft.ProgressBar(width=400, value=0)
        self.progress_text = ft.Text("0/0 PDFs cached", size=16)


        self.project_root_dir = Path(__file__).parent.parent
        self.results_lock = threading.Lock()

        self.cached_cv_data = {}
        self.progress_queue = queue.Queue()
        self.total_pdfs_to_cache = 0
        self.pdfs_cached_count = 0


    def setup_database_async(self):
        # Always include the progress bar and text column, their values will update later
        self.page.add(ft.Column([
            ft.Container(expand=True),
            ft.Row([self.loading_indicator_db, self.loading_text], alignment=ft.MainAxisAlignment.CENTER),
            ft.Column([self.progress_bar, self.progress_text], alignment=ft.CrossAxisAlignment.CENTER), # Removed conditional rendering
            ft.Container(expand=True)
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        self.page.update()

        success = self.setup_database()
        if success:
            self.loading_text.value = "Caching PDF files..."
            self.page.update() # Update the loading text

            self.cache_pdfs_async() # Start caching after DB setup
            
            # After caching is done and UI is ready, clear loading screen and show main view
            self.page.controls.clear()
            self.show_main_view()
            self.update_modal_position(animate=False)
        else:
            self.page.controls.clear()
            self.page.add(ft.Column([
                ft.Container(expand=True),
                ft.Text("Database setup failed. Please check console for errors.", color=ft.colors.RED, size=18),
                ft.Container(expand=True)
            ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
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
            
            # --- Perubahan di sini: Drop database jika sudah ada ---
            print(f"Dropping database '{db_name}' if it exists...")
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            print(f"Database '{db_name}' dropped (if it existed).")
            
            # Close connection to the server, as we are about to create a new database
            if connection.is_connected():
                connection.close()

            # Reconnect to ensure we are not "using" a dropped database
            connection = mysql.connector.connect(**db_server_config)
            cursor = connection.cursor()

            print(f"Creating database '{db_name}' and using it...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {db_name}")
            print(f"Database '{db_name}' is ready.")

            tables = {
                "ApplicantProfile": "CREATE TABLE IF NOT EXISTS `ApplicantProfile` (`applicant_id` INT PRIMARY KEY NOT NULL, `first_name` VARCHAR(50) DEFAULT NULL, `last_name` VARCHAR(50) DEFAULT NULL, `date_of_birth` DATE DEFAULT NULL, `address` VARCHAR(255) DEFAULT NULL, `phone_number` VARCHAR(20) DEFAULT NULL) ENGINE=InnoDB;",
                "ApplicantDetail": "CREATE TABLE IF NOT EXISTS `ApplicantDetail` (`applicant_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT, `application_role` VARCHAR(100) DEFAULT NULL, `cv_path` TEXT) ENGINE=InnoDB;"
            }
            for table_name, table_sql in tables.items():
                try:
                    cursor.execute(table_sql)
                except mysql.connector.Error as err:
                    print(f"Failed creating table: {err}")
                    return False
            
            # Since we drop and recreate, we always run seeder
            print("Database recreated. Running seeder...")
            connection.close() # Close current connection before seeder opens its own
            run_seeding(self.db_config)
            
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
            self.cached_cv_data[applicant_id] = {'flat_text': "Error:", 'regex_text': "Error:"} # Store error indicator
        finally:
            progress_queue.put(1) # Signal that one PDF has been processed

    def cache_pdfs_async(self):
        all_applicants_details = []
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor(dictionary=True)
            # Fetch only applicant_id and cv_path
            query = "SELECT p.applicant_id, d.cv_path FROM ApplicantProfile p JOIN ApplicantDetail d ON p.applicant_id = d.applicant_id"
            cursor.execute(query)
            all_applicants_details = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Failed to fetch applicant CV paths from DB: {err}")
            return
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()

        self.total_pdfs_to_cache = len(all_applicants_details)
        self.pdfs_cached_count = 0
        
        # Update progress bar and text initially
        self.update_caching_progress_ui() # Call directly, Flet handles thread safety for UI updates

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self._cache_single_pdf, app['applicant_id'], app['cv_path'], self.progress_queue) for app in all_applicants_details]
            
            threading.Thread(target=self._monitor_caching_progress, daemon=True).start()
            
            concurrent.futures.wait(futures)
        
        self.update_caching_progress_ui()
        print("PDF Caching complete.")


    def _monitor_caching_progress(self):
        while self.pdfs_cached_count < self.total_pdfs_to_cache:
            try:
                processed_count = self.progress_queue.get(timeout=0.1)
                self.pdfs_cached_count += processed_count
                self.update_caching_progress_ui() # Call directly, Flet handles thread safety for UI updates
            except queue.Empty:
                pass
        self.update_caching_progress_ui() # Final update after loop


    def update_caching_progress_ui(self):
        if self.total_pdfs_to_cache > 0:
            progress_value = self.pdfs_cached_count / self.total_pdfs_to_cache
            self.progress_bar.value = progress_value
            self.progress_text.value = f"{self.pdfs_cached_count}/{self.total_pdfs_to_cache} PDFs cached"
        else:
            self.progress_bar.value = 0
            self.progress_text.value = "0/0 PDFs cached"
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
        stop_headers = [h for h in all_known_headers if h.lower() not in [header.lower() for header in headers]]
        start_pattern = r'^\s*(' + '|'.join(headers) + r')\s*$'
        start_match = re.search(start_pattern, full_text, re.IGNORECASE | re.MULTILINE)
        if not start_match: return ""
        text_after_start = full_text[start_match.end():]
        first_stop_position = len(text_after_start)
        for stop_header in stop_headers:
            stop_pattern = r'^\s*(' + stop_header + r')\s*$'
            stop_match = re.search(stop_pattern, text_after_start, re.IGNORECASE | re.MULTILINE)
            if stop_match and stop_match.start() < first_stop_position:
                first_stop_position = stop_match.start()
        return text_after_start[:first_stop_position].strip()

    
    def _parse_structured_section(self, section_text: str) -> list[dict]:
        entries = []
        raw_entries = re.split(r'\n\s*\n+|\n(?=\d{2}/\d{4}|\w+\s+\d{4})', section_text.strip())
        
        for entry_text in raw_entries:
            if not entry_text.strip(): continue
            lines = [line.strip() for line in entry_text.strip().split('\n') if line.strip()]
            if len(lines) == 0: continue
            
            entry = self._parse_single_job_entry(lines)
            if entry:
                entries.append(entry)
        
        return entries
    
    def _parse_single_job_entry(self, lines: list[str]) -> dict:
        """Parse a single job entry handling various CV formats"""
        if not lines:
            return None
            
        date_first_pattern = r'^((?:\w+\s+)?\d{1,2}/?\d{4}(?:\s*(?:to|-)\s*(?:\w+\s+)?\d{1,2}/?\d{4}|\s*to\s*(?:Current|Present))?)'
        if re.match(date_first_pattern, lines[0], re.IGNORECASE):
            period = lines[0]
            if len(lines) > 1:
                company_title = lines[1]
                desc_lines = lines[2:] if len(lines) > 2 else []
                title = company_title
            else:
                title = "Position"
                desc_lines = []
        
        elif len(lines) > 0:
            first_line = lines[0]
            date_in_title = re.search(r'(\w{3}\s+\d{4}(?:\s+to\s+(?:Current|\w{3}\s+\d{4}))?|\d{1,2}/\d{4}(?:\s*-\s*\d{1,2}/\d{4})?)', first_line, re.IGNORECASE)
            
            if date_in_title:
                period = date_in_title.group(1)
                title = first_line[:date_in_title.start()].strip() or first_line
                desc_lines = lines[1:]
            else:
                title = lines[0]
                period = "N/A"
                desc_start_idx = 1
                
                for i, line in enumerate(lines[1:], 1):
                    if re.search(r'\d{4}|present|current', line, re.IGNORECASE):
                        if re.search(r'^(?:\w+\s+)?\d{1,2}/?\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', line, re.IGNORECASE):
                            period = line
                            desc_start_idx = i + 1
                            break
                        elif re.search(r'Company|Corp|Inc|LLC|Ltd', line, re.IGNORECASE):
                            period_match = re.search(r'(\w{3}\s+\d{4}(?:\s+to\s+(?:Current|\w{3}\s+\d{4}))?)', line, re.IGNORECASE)
                            if period_match:
                                period = period_match.group(1)
                                desc_start_idx = i + 1
                                break
                
                desc_lines = lines[desc_start_idx:] if desc_start_idx < len(lines) else []
        
        desc = '\n'.join(desc_lines).strip()
        
        desc = re.sub(r'^(Company Name\s*[-–]\s*City\s*,\s*State\s*)', '', desc, flags=re.IGNORECASE)
        desc = re.sub(r'^(City\s*,\s*State\s*)', '', desc, flags=re.IGNORECASE)
        
        if not desc:
            desc = "No description available."
        
        title = re.sub(r'\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*Company Name.*$', '', title, flags=re.IGNORECASE)
        
        return {
            'title': title.strip() or "Position",
            'period': period.strip(),
            'desc': desc
        }
    
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

        SKILLS_HEADERS = ['skills', 'keahlian', 'skill highlights', 'core qualifications', 'highlights']
        JOB_HEADERS = ['experience', 'work experience', 'professional experience', 'job history', 'pengalaman kerja', 'riwayat pekerjaan']
        EDU_HEADERS = ['education', 'education and training', 'pendidikan']
        ALL_KNOWN_HEADERS = SKILLS_HEADERS + JOB_HEADERS + EDU_HEADERS
        
        cv_text = self.cached_cv_data.get(candidate.id, {}).get('regex_text', "")
        if not cv_text or "Error:" in cv_text:
            cv_text = flatten_file_for_regex_multicolumn(str(self.project_root_dir / candidate.cv_path))

        skills_text = self._extract_section_content(cv_text, SKILLS_HEADERS, ALL_KNOWN_HEADERS)
        job_text = self._extract_section_content(cv_text, JOB_HEADERS, ALL_KNOWN_HEADERS)
        edu_text = self._extract_section_content(cv_text, EDU_HEADERS, ALL_KNOWN_HEADERS)
        job_history_list = self._parse_structured_section(job_text)
        education_list = self._parse_structured_section(edu_text)
        
        intro_card = ft.Container(padding=20, border=ft.border.all(2, ft.Colors.OUTLINE), border_radius=8, content=ft.Column([ft.Text(f"Introducing, {decrypted_name}!", size=24, weight=ft.FontWeight.BOLD), ft.Text(f"Address: {decrypted_address}", size=14), ft.Text(f"Phone: {decrypted_phone}", size=14)]))
        
        rank_card = ft.Container(
            padding=20, 
            border=ft.border.all(2, ft.Colors.OUTLINE), 
            border_radius=8, 
            bgcolor="#F9E79F", 
            height=120,
            content=ft.Column([
                ft.Text(f"#{self.search_results.index(candidate) + 1:02}", size=36, weight=ft.FontWeight.BOLD), 
                ft.Text(f"of {len(self.search_results)} results", size=16)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
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
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
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