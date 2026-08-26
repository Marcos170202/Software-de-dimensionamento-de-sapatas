"""
tema.py
-------
Paleta escura e configuração do ttk.Style, compartilhadas por toda a
interface do escopo amplo. Não há cálculo aqui — só cor e geometria de
widget.

A paleta reaproveita as mesmas cores dos desenhos do núcleo
(`calc_core.sapata_isolada.visual2d`/`visual3d`), para que o entorno em
Tkinter e os canvases de desenho não briguem visualmente.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FUNDO = "#1a2026"
FUNDO_PAINEL = "#20262d"
FUNDO_CAMPO = "#262d34"
FUNDO_TILE = "#242b32"
BORDA = "#38434d"
TEXTO = "#e6eaec"
TEXTO_FRACO = "#8b96a0"
DESTAQUE = "#39c2dc"
LARANJA = "#f0873c"
VERDE = "#3ec97a"
VERMELHO = "#e2564f"
AMARELO = "#e2b53f"

FONTE = ("Segoe UI", 9)
FONTE_TITULO = ("Segoe UI Semibold", 14)
FONTE_SUBTITULO = ("Segoe UI", 9)
FONTE_SECAO = ("Segoe UI Semibold", 9)
FONTE_MONO = ("Consolas", 9)


def aplicar_tema(root: tk.Tk) -> ttk.Style:
    """Configura um `ttk.Style` escuro sobre o tema base 'clam'."""
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=FUNDO)

    style.configure(".", background=FUNDO, foreground=TEXTO, font=FONTE,
                     fieldbackground=FUNDO_CAMPO, bordercolor=BORDA,
                     lightcolor=FUNDO_PAINEL, darkcolor=FUNDO_PAINEL)
    style.configure("TFrame", background=FUNDO)
    style.configure("Painel.TFrame", background=FUNDO_PAINEL)
    style.configure("Tile.TFrame", background=FUNDO_TILE, relief="flat")
    style.configure("TLabel", background=FUNDO, foreground=TEXTO)
    style.configure("Painel.TLabel", background=FUNDO_PAINEL, foreground=TEXTO)
    style.configure("Tile.TLabel", background=FUNDO_TILE, foreground=TEXTO)
    style.configure("Fraco.TLabel", background=FUNDO, foreground=TEXTO_FRACO)
    style.configure("PainelFraco.TLabel", background=FUNDO_PAINEL,
                     foreground=TEXTO_FRACO)
    style.configure("Secao.TLabel", background=FUNDO_PAINEL, foreground=DESTAQUE,
                     font=FONTE_SECAO)
    style.configure("Titulo.TLabel", background=FUNDO, foreground=TEXTO,
                     font=FONTE_TITULO)
    style.configure("Subtitulo.TLabel", background=FUNDO, foreground=TEXTO_FRACO,
                     font=FONTE_SUBTITULO)

    style.configure("TEntry", fieldbackground=FUNDO_CAMPO, foreground=TEXTO,
                     insertcolor=TEXTO, bordercolor=BORDA)
    style.configure("TCombobox", fieldbackground=FUNDO_CAMPO, foreground=TEXTO,
                     background=FUNDO_CAMPO, arrowcolor=TEXTO)
    style.map("TCombobox", fieldbackground=[("readonly", FUNDO_CAMPO)],
              foreground=[("readonly", TEXTO)])
    style.configure("TCheckbutton", background=FUNDO_PAINEL, foreground=TEXTO)
    style.map("TCheckbutton", background=[("active", FUNDO_PAINEL)])

    style.configure("TButton", background=FUNDO_CAMPO, foreground=TEXTO,
                     bordercolor=BORDA, padding=(8, 4))
    style.map("TButton", background=[("active", "#2f3841")])
    style.configure("Acento.TButton", background=DESTAQUE, foreground="#06232a",
                     bordercolor=DESTAQUE, padding=(10, 5), font=FONTE_SECAO)
    style.map("Acento.TButton", background=[("active", "#4fd0e8")])
    style.configure("Pdf.TButton", background=LARANJA, foreground="#2a1500",
                     bordercolor=LARANJA, padding=(10, 5), font=FONTE_SECAO)
    style.map("Pdf.TButton", background=[("active", "#f4a06a")])

    style.configure("TNotebook", background=FUNDO, bordercolor=BORDA)
    style.configure("TNotebook.Tab", background=FUNDO_PAINEL, foreground=TEXTO_FRACO,
                     padding=(10, 5))
    style.map("TNotebook.Tab", background=[("selected", FUNDO_CAMPO)],
              foreground=[("selected", TEXTO)])

    style.configure("Treeview", background=FUNDO_CAMPO, fieldbackground=FUNDO_CAMPO,
                     foreground=TEXTO, bordercolor=BORDA, rowheight=22)
    style.configure("Treeview.Heading", background=FUNDO_PAINEL, foreground=DESTAQUE,
                     relief="flat")
    style.map("Treeview", background=[("selected", "#2c5560")])

    style.configure("TLabelframe", background=FUNDO_PAINEL, bordercolor=BORDA,
                     relief="groove")
    style.configure("TLabelframe.Label", background=FUNDO_PAINEL, foreground=DESTAQUE,
                     font=FONTE_SECAO)

    style.configure("TPanedwindow", background=FUNDO)
    style.configure("TScrollbar", background=FUNDO_PAINEL, bordercolor=FUNDO,
                     arrowcolor=TEXTO_FRACO, troughcolor=FUNDO)

    style.configure("StatusOk.TLabel", background=VERDE, foreground="#06280f",
                     font=FONTE_SECAO, padding=(10, 4))
    style.configure("StatusErro.TLabel", background=VERMELHO, foreground="#2a0705",
                     font=FONTE_SECAO, padding=(10, 4))
    style.configure("Banner.TLabel", background="#3a2a10", foreground=AMARELO,
                     font=("Segoe UI", 8))
    style.configure("Rodape.TLabel", background=FUNDO_PAINEL, foreground=TEXTO_FRACO,
                     font=("Segoe UI", 8))
    return style


def cor_status(ok: bool) -> str:
    return VERDE if ok else VERMELHO
