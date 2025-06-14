import flet as ft
from datetime import datetime

def create_header():
    return ft.Container(
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
    )