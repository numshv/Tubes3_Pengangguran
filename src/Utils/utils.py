import flet as ft
import os
import time
import re
from collections import Counter
import sys
import json
import threading # Import the threading module

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.Utils import utils
    from src.Solver import kmp, BM
    print(f"Successfully imported modules from src.")
except ImportError as e:
    print(f"FATAL IMPORT ERROR: {e}")
    print("Please ensure:")
    print(f"  1. You are running 'python src/Main.py' from the '{PROJECT_ROOT}' directory.")
    print(f"  2. Empty '__init__.py' files exist in '{os.path.join(PROJECT_ROOT, 'src')}', ")
    print(f"     '{os.path.join(PROJECT_ROOT, 'src', 'Utils')}', and '{os.path.join(PROJECT_ROOT, 'src', 'Solver')}'.")
    sys.exit(1)

# --- Global Variables / App State ---
CV_DATABASE = []
CV_DATA_LOADED = False
CV_ROOT_DIR = os.path.join(PROJECT_ROOT, "data")
CACHE_FILE_PATH = os.path.join(SCRIPT_DIR, "cv_data_cache.json")


def main(page: ft.Page):
    page.title = "Sistem ATS CV Digital"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.bgcolor = "background" # Using theme color strings

    global CV_DATABASE, CV_DATA_LOADED

    # --- SnackBar for notifications ---
    snack_bar = ft.SnackBar(content=ft.Text(""), open=False, duration=4000)
    page.overlay.append(snack_bar)

    def show_message_thread_safe(message_text, duration=4000):
        snack_bar.content = ft.Text(message_text)
        snack_bar.open = True
        snack_bar.duration = duration
        # page.update() should be called thread-safely if this function can be called from a background thread
        if page.is_main_thread():
            page.update()
        else:
            page.run_thread_safe(page.update)


    # --- UI Elements for Progress Display (part of splash screen) ---
    splash_title_text = ft.Text("Memuat data CV (pertama kali)...", size=20, weight=ft.FontWeight.BOLD, color="onPrimaryContainer")
    splash_subtitle_text = ft.Text("Proses ini mungkin memakan waktu beberapa saat.", color="onPrimaryContainer")
    splash_progress_ring = ft.ProgressRing(color="onPrimaryContainer") # Adjusted color
    splash_category_progress_text = ft.Text("Menginisialisasi...", text_align=ft.TextAlign.CENTER, size=12, italic=True, color="onPrimaryContainer")

    # --- UI Elements ---
    title_text = ft.Text("Sistem ATS CV Digital (Pengangguran Search Engine)", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    keyword_input = ft.TextField(
        label="Kata Kunci (pisahkan dengan koma, contoh: python, react, sql)",
        width=600,
        border_radius=10,
    )
    algo_selector = ft.RadioGroup(
        content=ft.Row(
            [
                ft.Radio(value="KMP", label="KMP"),
                ft.Radio(value="BM", label="Boyer-Moore"),
            ],
            spacing=20,
        ),
        value="KMP",
    )
    top_n_selector = ft.Dropdown(
        label="Top Matches",
        width=180,
        border_radius=10,
        options=[ft.dropdown.Option(str(i)) for i in [5, 10, 15, 20, 25, 50, 100]],
        value="10",
    )
    search_button = ft.ElevatedButton(
        text="Cari Kandidat",
        icon="search", 
        on_click=None,
        width=200,
        height=40,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        disabled=True
    )
    
    loading_indicator = ft.ProgressRing(width=20, height=20, visible=False)
    time_summary_text = ft.Text("", italic=True, size=12, text_align=ft.TextAlign.CENTER)
    results_info_text = ft.Text("Memuat data CV...", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    
    results_container = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    # --- Dialog for CV Summary ---
    cv_summary_dialog_content = ft.Column(
        controls=[], 
        scroll=ft.ScrollMode.ADAPTIVE, 
        height=page.height * 0.6 if page.height else 400,
        width=page.width * 0.8 if page.width else 500,
        spacing=10
    )
    cv_summary_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Ringkasan CV Kandidat"),
        content=cv_summary_dialog_content,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Tutup", on_click=lambda e: close_dialog(cv_summary_dialog), style=ft.ButtonStyle(color="blueAccent")) # String color
        ],
    )
    page.dialog = cv_summary_dialog
    
    # --- Functions ---
    def close_dialog(dialog_instance):
        dialog_instance.open = False
        page.update()

    def show_cv_summary(e, cv_item):
        details = cv_item['extracted_details']
        summary_controls = [
            ft.Text(f"Nama: {details.get('name', 'N/A')}", weight=ft.FontWeight.BOLD, size=16),
            ft.Text(f"Email: {', '.join(details.get('emails', ['N/A']))}"),
            ft.Text(f"Telepon: {', '.join(details.get('phones', ['N/A']))}"),
            ft.Divider(height=5, color="black12"),
        ]
        # ... (rest of show_cv_summary remains the same)
        if details.get('summary_overview'):
            summary_controls.extend([
                ft.Text("Ringkasan/Overview:", weight=ft.FontWeight.W_600),
                ft.Text(details['summary_overview'], selectable=True),
                ft.Divider(height=5, color="black12"),
            ])
        if details.get('skills_list'):
            summary_controls.extend([
                ft.Text("Keahlian (Skills):", weight=ft.FontWeight.W_600),
                ft.Text(", ".join(details['skills_list']) if details['skills_list'] else "N/A", selectable=True),
                ft.Divider(height=5, color="black12"),
            ])
        if details.get('experience_section'):
            summary_controls.extend([
                ft.Text("Pengalaman Kerja:", weight=ft.FontWeight.W_600),
                ft.Text(details['experience_section'], selectable=True),
                ft.Divider(height=5, color="black12"),
            ])
        if details.get('education_section'):
            summary_controls.extend([
                ft.Text("Riwayat Pendidikan:", weight=ft.FontWeight.W_600),
                ft.Text(details['education_section'], selectable=True),
            ])
        cv_summary_dialog_content.controls = summary_controls
        cv_summary_dialog.open = True
        page.update()


    def view_cv_file(e, filepath):
        try:
            abs_filepath = os.path.realpath(filepath)
            page.launch_url(f"file://{abs_filepath}")
        except Exception as ex:
            print(f"Error opening file {filepath}: {ex}")
            show_message_thread_safe(f"Gagal membuka file: {filepath}")

    def perform_search_async(e):
        if not CV_DATA_LOADED:
            show_message_thread_safe("Data CV belum termuat. Mohon tunggu atau restart aplikasi jika masalah berlanjut.")
            return
        # ... (rest of perform_search_async remains the same)
        keywords_str = keyword_input.value 
        if not keywords_str:
            show_message_thread_safe("Mohon masukkan kata kunci.")
            results_container.controls.clear()
            time_summary_text.value = ""
            results_info_text.value = "Masukkan kata kunci untuk memulai pencarian."
            page.update()
            return

        keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
        if not keywords:
            show_message_thread_safe("Kata kunci tidak valid.")
            results_container.controls.clear()
            time_summary_text.value = ""
            results_info_text.value = "Kata kunci tidak valid."
            page.update()
            return

        selected_algo_str = algo_selector.value
        top_n = int(top_n_selector.value)

        search_button.disabled = True
        loading_indicator.visible = True
        results_container.controls.clear()
        time_summary_text.value = "Memproses pencarian..."
        results_info_text.value = ""
        page.update()
        
        search_algo_func = kmp.KMP if selected_algo_str == "KMP" else BM.BM
        
        start_exact_time = time.time()
        cv_match_details = []
        globally_exact_found_keywords = set()

        for cv_doc in CV_DATABASE:
            doc_match_info = {
                'doc': cv_doc,
                'keyword_matches': {kw: {'exact_count': 0, 'fuzzy_count': 0} for kw in keywords},
                'total_score': 0
            }
            cv_text_lower = cv_doc['text_content'].lower()
            for keyword in keywords: 
                matches = search_algo_func(cv_text_lower, keyword)
                count = len(matches)
                if count > 0:
                    doc_match_info['keyword_matches'][keyword]['exact_count'] = count
                    globally_exact_found_keywords.add(keyword)
            cv_match_details.append(doc_match_info)
        exact_time_taken = (time.time() - start_exact_time) * 1000

        start_fuzzy_time = time.time()
        keywords_for_fuzzy_search = [kw for kw in keywords if kw not in globally_exact_found_keywords]
        fuzzy_matches_performed = False

        if keywords_for_fuzzy_search:
            fuzzy_matches_performed = True
            for item in cv_match_details:
                cv_text_words = item['doc']['text_content'].lower().split()
                cv_text_words_filtered = [word for word in cv_text_words if len(word) > 2]
                for keyword_fz in keywords_for_fuzzy_search: 
                    fuzzy_hit_count = 0
                    for word_in_cv in cv_text_words_filtered:
                        if utils.is_similar(keyword_fz, word_in_cv, threshold=utils.SIMILARITY_THRESHOLD):
                            fuzzy_hit_count += 1 
                    item['keyword_matches'][keyword_fz]['fuzzy_count'] = fuzzy_hit_count
        fuzzy_time_taken = (time.time() - start_fuzzy_time) * 1000 if fuzzy_matches_performed else 0

        for item in cv_match_details:
            score = 0
            for keyword in keywords:
                score += item['keyword_matches'][keyword]['exact_count']
                score += item['keyword_matches'][keyword]['fuzzy_count']
            item['total_score'] = score
        
        ranked_cvs = sorted(
            [item for item in cv_match_details if item['total_score'] > 0],
            key=lambda x: x['total_score'],
            reverse=True
        )
        
        time_msg = f"Exact Match ({selected_algo_str}): {len(CV_DATABASE)} CVs dipindai dalam {exact_time_taken:.2f} ms."
        if fuzzy_matches_performed and keywords_for_fuzzy_search:
            time_msg += f"\nFuzzy Match (Levenshtein untuk '{', '.join(keywords_for_fuzzy_search)}'): {len(CV_DATABASE)} CVs dipindai dalam {fuzzy_time_taken:.2f} ms."
        time_summary_text.value = time_msg

        results_container.controls.clear()
        if not ranked_cvs:
            results_info_text.value = "Tidak ada CV yang cocok dengan kriteria pencarian Anda."
        else:
            results_info_text.value = f"Menampilkan {min(top_n, len(ranked_cvs))} dari {len(ranked_cvs)} CV yang cocok:"
            for i, item_data in enumerate(ranked_cvs[:top_n]):
                cv_info = item_data['doc']
                keyword_display_parts = []
                for kw, counts in item_data['keyword_matches'].items():
                    parts = []
                    if counts['exact_count'] > 0:
                        parts.append(f"exact: {counts['exact_count']}")
                    if counts['fuzzy_count'] > 0:
                        parts.append(f"fuzzy: {counts['fuzzy_count']}")
                    if parts:
                         keyword_display_parts.append(f"{kw} ({', '.join(parts)})")
                matched_keywords_str = "; ".join(keyword_display_parts) if keyword_display_parts else "N/A"
                card = ft.Card(
                    elevation=2,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"{i+1}. {cv_info.get('display_name', cv_info['id'])}", weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(f"Kategori: {cv_info['category']}", size=12, italic=True),
                                ft.Text(f"Total Skor Kecocokan: {item_data['total_score']}", size=14),
                                ft.Text(f"Keyword Cocok: {matched_keywords_str}", size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row(
                                    [
                                        ft.ElevatedButton("Lihat Ringkasan", icon="description", on_click=lambda e, item=cv_info: show_cv_summary(e, item), height=35, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))), 
                                        ft.ElevatedButton("Lihat CV Asli", icon="picture_as_pdf", on_click=lambda e, path=cv_info['filepath']: view_cv_file(e, path), height=35, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))), 
                                    ],
                                    alignment=ft.MainAxisAlignment.END, spacing=10,
                                )
                            ], spacing=5,
                        ),
                        width=580, padding=15, border_radius=10, ink=True,
                    )
                )
                results_container.controls.append(card)
        search_button.disabled = False
        loading_indicator.visible = False
        page.update()

    search_button.on_click = perform_search_async

    def ui_progress_callback(current_index, total_items, item_name, is_error=False, is_complete=False, category_skipped=False):
        def _update_splash_text_safely():
            if is_error and category_skipped:
                 splash_category_progress_text.value = f"Error: Gagal proses '{item_name}'. Lanjut... ({current_index}/{total_items})"
            elif is_error:
                splash_category_progress_text.value = f"Error: {item_name}"
            elif is_complete:
                splash_category_progress_text.value = f"Selesai memproses {total_items} kategori. Menyimpan cache..."
            else:
                splash_category_progress_text.value = f"Memproses kategori: {item_name} ({current_index + 1}/{total_items})..."
            if page.splash and page.splash.visible:
                page.update()
        page.run_thread_safe(_update_splash_text_safely)

    def _perform_data_loading_and_caching(): # This will run in the new, dedicated background thread
        global CV_DATABASE, CV_DATA_LOADED
        print(f"[Main.py THREAD] Starting background data processing from: {CV_ROOT_DIR}")
        
        CV_DATABASE = utils.load_cv_data(
            cv_root_dir=CV_ROOT_DIR,
            max_files_per_category=20,
            progress_callback=ui_progress_callback
        )
        
        print(f"[Main.py THREAD] PDF processing complete. Number of CVs loaded: {len(CV_DATABASE)}")

        if CV_DATABASE:
            try:
                print(f"[Main.py THREAD] Attempting to save {len(CV_DATABASE)} CV entries to cache: {CACHE_FILE_PATH}")
                os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
                with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(CV_DATABASE, f, indent=2)
                print(f"[Main.py THREAD] Cache file saved successfully to {CACHE_FILE_PATH}")
                show_message_thread_safe("Cache data CV berhasil disimpan!") # Already thread-safe
            except Exception as exc:
                print(f"[Main.py THREAD] FATAL CACHE SAVING ERROR: {exc}")
                show_message_thread_safe(f"Error: Gagal menyimpan cache: {exc}", 5000)
        else:
            print("[Main.py THREAD] CV_DATABASE is empty after processing. Cache file will not be created/updated.")
            if os.path.exists(CACHE_FILE_PATH):
                try:
                    os.remove(CACHE_FILE_PATH)
                    print(f"[Main.py THREAD] Removed empty/old cache file: {CACHE_FILE_PATH}")
                except OSError as oe:
                    print(f"[Main.py THREAD] Error removing empty/old cache file {CACHE_FILE_PATH}: {oe}")

        CV_DATA_LOADED = True
        
        def _finalize_ui_from_thread():
            page.splash = None
            search_button.disabled = False
            if not CV_DATABASE:
                results_info_text.value = "Gagal memuat atau memproses data CV. Periksa konsol."
            else:
                results_info_text.value = f"{len(CV_DATABASE)} CV berhasil diproses. Siap untuk pencarian."
            splash_category_progress_text.value = "" 
            page.update()
        
        page.run_thread_safe(_finalize_ui_from_thread)


    def load_initial_data(): # This function is the target of page.on_load (runs in Flet's worker thread)
        global CV_DATABASE, CV_DATA_LOADED
        
        def _update_ui_for_cache_load_safely():
            search_button.disabled = False 
            results_info_text.value = f"{len(CV_DATABASE)} CV berhasil dimuat dari cache. Siap untuk pencarian."
            page.update()

        if os.path.exists(CACHE_FILE_PATH):
            print(f"[Main.py ON_LOAD] Cache file found. Loading from cache...")
            try:
                with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
                    CV_DATABASE = json.load(f)
                CV_DATA_LOADED = True
                print(f"[Main.py ON_LOAD] Successfully loaded {len(CV_DATABASE)} CVs from cache.")
                page.run_thread_safe(_update_ui_for_cache_load_safely)
                return 
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"[Main.py ON_LOAD] Error reading cache file: {e}. Deleting corrupt cache.")
                try:
                    os.remove(CACHE_FILE_PATH)
                    print(f"[Main.py ON_LOAD] Corrupt cache file {CACHE_FILE_PATH} deleted.")
                except OSError as oe:
                    print(f"[Main.py ON_LOAD] Error deleting corrupt cache file {CACHE_FILE_PATH}: {oe}")
        
        # --- No Cache: Setup splash, then launch dedicated thread for heavy work ---
        print("[Main.py ON_LOAD] No valid cache. Setting up splash screen.")
        page.splash = ft.Container(
            content=ft.Column(
                [
                    splash_title_text,
                    splash_subtitle_text,
                    splash_progress_ring,
                    splash_category_progress_text,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True, spacing=20,
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.colors.with_opacity(0.95, "surfaceVariant"), # String color
        )
        results_info_text.value = "Memproses CV untuk pertama kalinya (bisa lama)..."
        
        # Schedule the splash screen to be shown
        # This page.update() is called from the page.on_load thread, so it needs to be thread-safe.
        page.run_thread_safe(page.update) 
        
        # Give Flet a moment to render the splash screen
        # This sleep happens in the page.on_load thread, not blocking the main UI thread.
        time.sleep(0.5) # Increased delay slightly

        # Now, start the actual data loading in a new, dedicated thread.
        # The target function _perform_data_loading_and_caching will handle its own UI updates via page.run_thread_safe.
        print("[Main.py ON_LOAD] Starting dedicated thread for data loading and caching.")
        data_thread = threading.Thread(target=_perform_data_loading_and_caching, daemon=True)
        data_thread.start()
    
    page.on_load = load_initial_data

    page.add(
        ft.Container(
            # ... (rest of the page.add content remains the same) ...
            content=ft.Column(
                [
                    title_text, ft.Divider(height=10, color="transparent"),
                    keyword_input,
                    ft.Row(
                        [
                            ft.Column([ft.Text("Algoritma Pencarian:", weight=ft.FontWeight.W_600), algo_selector]),
                            ft.Column([ft.Text("Jumlah Hasil:", weight=ft.FontWeight.W_600), top_n_selector]),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.END, width=600,
                    ),
                    ft.Row([search_button, loading_indicator], alignment=ft.MainAxisAlignment.CENTER, width=600),
                    ft.Divider(height=10), time_summary_text, results_info_text,
                    ft.Divider(height=5),
                    results_container,
                ],
                alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
            ), padding=20, alignment=ft.alignment.top_center, expand=True,
        )
    )

if __name__ == "__main__":
    DATA_DIR_CHECK = os.path.join(PROJECT_ROOT, "data")
    if not os.path.exists(DATA_DIR_CHECK):
        print(f"FATAL ERROR: Data directory '{DATA_DIR_CHECK}' not found.")
        try:
            os.makedirs(os.path.join(DATA_DIR_CHECK, "SAMPLE_CATEGORY"))
            print(f"Created dummy directory {os.path.join(DATA_DIR_CHECK, 'SAMPLE_CATEGORY')} for testing.")
        except Exception as e_mkdir:
            print(f"Could not create dummy data directory: {e_mkdir}")
    
    ft.app(target=main, assets_dir=os.path.join(PROJECT_ROOT, "assets") if os.path.exists(os.path.join(PROJECT_ROOT, "assets")) else None)
