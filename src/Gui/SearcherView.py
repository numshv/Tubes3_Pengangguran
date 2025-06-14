import flet as ft
from datetime import datetime

class CVATSSearchApp:
    def __init__(self):
        self.page = None
        self.modal_open = False
        
        self.open_pos = 0.4  
        self.closed_pos = 0.8  
        self.modal_position = self.closed_pos  

        self.drag_start_y = 0
        self.modal_start_position = 0
        
        self.sample_results = [
            {
                'id': 0, 'name': 'Qodri', 'matches': 4, 'rank': 1, 'total_candidates': 99,
                'address': 'Jl. hahahahah No.69', 'phone': '+6299999999999',
                'birth_date': '09/11/2001',
                'skills': 'Lmao, lmao, lmao, lol, bruh k, wtf mann',
                'keywords': [('React', 2), ('Javascript', 3)],
                'job_history': [
                    {'title': 'CTO', 'period': '2003 - 2004', 'desc': 'jnsjagdjahgdjab sdhsajhjd jhadhjsg sdjhagdsjhaa dajdvajdha'},
                    {'title': 'Senior Developer', 'period': '2001 - 2003', 'desc': 'jnsjagdjahgdjab sdhsajhjd jhadhjsg sdjhagdsjhaa dajdvajdha'},
                ],
                'education': [
                    {'degree': 'SMA UBUBUBU', 'period': '2003 - 2004', 'desc': 'jnsjagdjahgdjab sdhsajhjd jhadhjsg sdjhagdsjhaa dajdvajdha'},
                    {'degree': 'SMP Ububub', 'period': '2003 - 2004', 'desc': 'jnsjagdjahgdjab sdhsajhjd jhadhjsg sdjhagdsjhaa dajdvajdha'},
                ]
            }
        ]
        for i in range(1, 8):
            new_candidate = self.sample_results[0].copy()
            new_candidate['id'] = i
            new_candidate['name'] = f'Candidate {i+1}'
            new_candidate['rank'] = i + 1
            self.sample_results.append(new_candidate)

    def create_result_card(self, result):
        keyword_list = [ft.Text(f"{i}. {keyword}: {count} occurrences", size=12, color='black') for i, (keyword, count) in enumerate(result['keywords'], 1)]
        
        return ft.Container(
            content=ft.Column([
                ft.Text(result['name'], size=16, weight=ft.FontWeight.BOLD, color='black'),
                ft.Text(f"{result['matches']} matches", size=12, color='black'),
                ft.Text("Matched keywords:", size=12, weight=ft.FontWeight.BOLD, color='black'),
                ft.Column(keyword_list, spacing=2),
                ft.Container(
                    content=ft.Row([
                        ft.FilledButton(
                            text="Summary",
                            style=ft.ButtonStyle(
                                bgcolor='#EACD8C',
                                color='black',
                                shape=ft.RoundedRectangleBorder(radius=5),
                                side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}
                            ),
                        ),
                        ft.FilledButton(
                            text="Show CV",
                            style=ft.ButtonStyle(
                                bgcolor='#EACD8C',
                                color='black',
                                shape=ft.RoundedRectangleBorder(radius=5),
                                side={ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK)}
                            )
                        )
                    ], spacing=10),
                    margin=ft.margin.only(top=5) 
                )
            ], spacing=8, tight=True),
            padding=15,
            border=ft.border.all(2, 'black'),
            border_radius=8,
            bgcolor='#F0EFFF',
            width=280
        )

    def create_modal_handle(self):
        return ft.Container(
            content=ft.Container(height=5, width=40, bgcolor='black', border_radius=3),
            padding=15,
            alignment=ft.alignment.center
        )

    def create_search_settings_content(self):
        return ft.Column([
            ft.Text("Search Settings", size=24, weight=ft.FontWeight.BOLD, color='black'),
            ft.Row([
                ft.Column([
                    ft.Text("Algorithm choice:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Dropdown(
                        width=200, 
                        options=[ft.dropdown.Option("choose..."), ft.dropdown.Option("Algorithm 1"), ft.dropdown.Option("Algorithm 2")], 
                        value="choose..."
                    )
                ], spacing=5),
                ft.Column([
                    ft.Text("Keywords:", size=14, weight=ft.FontWeight.BOLD),
                    ft.TextField(hint_text="Enter ...", multiline=True, min_lines=3, max_lines=8, width=400, border_color='black')
                ], spacing=5)
            ], spacing=50, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.Column([
                    ft.Text("Top choice:", size=14, weight=ft.FontWeight.BOLD),
                    ft.TextField(hint_text="Enter ...", width=200, border_color='black')
                ], spacing=5),
                ft.ElevatedButton(
                    text="🔍 search", bgcolor="#28A745", color="white",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
                    on_click=self.perform_search
                )
            ], spacing=50, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def create_draggable_modal(self):
        """Create the draggable modal"""
        return ft.Container(
            content=ft.Column([
                self.create_modal_handle(),
                ft.Container(content=self.create_search_settings_content(), padding=20, expand=True)
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#eaf4f4",
            border=ft.border.all(2, 'black'),
            border_radius=ft.border_radius.only(top_left=15, top_right=15),
        )

    def on_pan_start(self, e: ft.DragStartEvent):
        self.drag_start_y = e.global_y
        if self.page and self.page.window_height > 0:
            self.modal_start_position = self.modal_container.top / self.page.window_height
        else:
            self.modal_start_position = self.modal_position

    def on_pan_update(self, e: ft.DragUpdateEvent):
        if self.page and self.page.window_height > 0:
            delta_y = e.global_y - self.drag_start_y
            new_position = self.modal_start_position + (delta_y / self.page.window_height)
            self.modal_position = max(self.open_pos, min(self.closed_pos, new_position))
            self.update_modal_position(animate=False)

    def on_pan_end(self, e: ft.DragEndEvent):
        threshold = (self.open_pos + self.closed_pos) / 2
        if self.modal_position < threshold:
            self.modal_position = self.open_pos
            self.modal_open = True
        else:
            self.modal_position = self.closed_pos
            self.modal_open = False
        self.update_modal_position(animate=True)

    def toggle_modal(self, e):
        if self.modal_open:
            self.modal_position = self.closed_pos
            self.modal_open = False
        else:
            self.modal_position = self.open_pos
            self.modal_open = True
        self.update_modal_position(animate=True)

    def update_modal_position(self, animate=False):
        if hasattr(self, 'modal_container') and self.page:
            window_height = self.page.window_height or 800
            window_width = self.page.window_width or 1200
            
            self.modal_container.animate_position = ft.Animation(300, "decelerate") if animate else None
            self.modal_container.top = window_height * self.modal_position
            
            modal_width = window_width * 0.6  
            self.modal_container.left = (window_width - modal_width) / 2
            self.modal_container.width = modal_width
            self.page.update()

    def on_page_resize(self, e):
        self.update_modal_position(animate=False)

    def perform_search(self, e):
        print("Search performed!")

    def main(self, page: ft.Page):
        self.page = page
        page.title = "CV ATS Search"
        page.bgcolor = "#FFFFFF"
        page.padding = 0
        page.window_width = 1200
        page.window_height = 800
        page.on_resize = self.on_page_resize
        
        main_content = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("LOGO", size=20, weight=ft.FontWeight.BOLD, color="#E74C3C"),
                        ft.Container(expand=True),
                        ft.Text("CV ATS Search", size=24, weight=ft.FontWeight.BOLD, color='black'),
                        ft.Container(expand=True),
                        ft.Text(datetime.now().strftime("%H.%M"), size=20, weight=ft.FontWeight.BOLD, color='black')
                    ]),
                    padding=20,
                    bgcolor='#FFF9EB',
                    border=ft.border.only(bottom=ft.border.BorderSide(2, 'black'))
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Text("Results", size=28, weight=ft.FontWeight.BOLD, color='black'),
                            margin=ft.margin.only(bottom=20)
                        ),
                        ft.GridView(
                            expand=True,
                            runs_count=4,
                            max_extent=300,
                            child_aspect_ratio=1.2,
                            spacing=20,
                            run_spacing=20,
                            controls=[self.create_result_card(result) for result in self.sample_results]
                        )
                    ]),
                    padding=20,
                    expand=True
                )
            ]),
            expand=True
        )
        
        modal = self.create_draggable_modal()
        
        window_width = page.window_width or 1200
        window_height = page.window_height or 800
        
        modal_width = window_width * 0.6
        
        self.modal_container = ft.Container(
            content=ft.GestureDetector(
                content=modal,
                on_pan_start=self.on_pan_start,
                on_pan_update=self.on_pan_update,
                on_pan_end=self.on_pan_end,
                on_tap=self.toggle_modal,
            ),
            top=window_height * self.modal_position,
            left=(window_width - modal_width) / 2,
            width=modal_width,
            height=window_height * 0.7, 
        )
        
        page.add(
            ft.Stack([
                main_content,
                self.modal_container
            ], expand=True)
        )
        
        page.update()

def main(page: ft.Page):
    app = CVATSSearchApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main)