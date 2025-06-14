import flet as ft
from .HeaderView import create_header

def SummaryView(candidate: dict) -> ft.View:
    """Builds the detailed summary view for a specific candidate."""

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
        content=ft.Column([
            ft.Text("Skills", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(candidate['skills'], size=16),
        ])
    )
    job_history_card = ft.Container(
        padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#E8DAEF", expand=True,
        content=ft.Column([
            ft.Text("Job History", size=24, weight=ft.FontWeight.BOLD),
            ft.Column(
                controls=[
                    ft.Column([
                        ft.Text(f"● {job['title']}", weight=ft.FontWeight.BOLD),
                        ft.Text(job['period'], size=12, italic=True),
                        ft.Text(job['desc'], size=14),
                    ], spacing=2) for job in candidate['job_history']
                ], spacing=15, scroll=ft.ScrollMode.AUTO
            )
        ])
    )
    education_card = ft.Container(
        padding=20, border=ft.border.all(2, 'black'), border_radius=8, bgcolor="#D4E6F1",
        content=ft.Column([
            ft.Text("Education", size=24, weight=ft.FontWeight.BOLD),
            ft.Column(
                 controls=[
                    ft.Column([
                        ft.Text(f"● {edu['degree']}", weight=ft.FontWeight.BOLD),
                        ft.Text(edu['period'], size=12, italic=True),
                        ft.Text(edu['desc'], size=14),
                    ], spacing=2) for edu in candidate['education']
                ], spacing=15, scroll=ft.ScrollMode.AUTO
            )
        ])
    )
    back_button = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, color='white'), ft.Text("Back", color='white', size=20, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor='black', padding=15, border_radius=8, on_click=lambda e: e.page.go("/"), tooltip="Go back to results"
    )
    
    layout = ft.Column([
        create_header(),
        ft.Container(
            padding=20, expand=True,
            content=ft.Row([
                ft.Column([intro_card, ft.Row([rank_card, birth_card], spacing=20, expand=True), skills_card], spacing=20, expand=2),
                ft.Column([job_history_card], expand=2),
                ft.Column([education_card, back_button], spacing=20, expand=2),
            ], spacing=20, expand=True)
        )
    ], expand=True)

    return ft.View(f"/summary/{candidate['id']}", [layout], padding=0, bgcolor="#FFFFFF")