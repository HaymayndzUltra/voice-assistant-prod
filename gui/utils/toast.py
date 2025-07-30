from __future__ import annotations

"""Simple helper functions to show non-blocking toast notifications.

Requires ttkbootstrap >= 1.5.  Falls back to tkinter.messagebox when not
available or when root does not have ttkbootstrap style.
"""
from typing import Optional

import tkinter as tk
from tkinter import messagebox

try:
    from ttkbootstrap.toast import ToastNotification  # type: ignore
except ImportError:  # ttkbootstrap not installed or older version
    ToastNotification = None  # type: ignore


def _fallback(title: str, message: str, kind: str = "info") -> None:  # noqa: D401
    if kind == "error":
        messagebox.showerror(title, message)
    elif kind == "warning":
        messagebox.showwarning(title, message)
    else:
        messagebox.showinfo(title, message)


def show_info(root: tk.Tk | tk.Toplevel, message: str, title: str = "Info") -> None:
    """Display informational toast."""
    _show(root, title, message, "primary")


def show_error(root: tk.Tk | tk.Toplevel, message: str, title: str = "Error") -> None:
    """Display error toast."""
    _show(root, title, message, "danger")


def show_warning(root: tk.Tk | tk.Toplevel, message: str, title: str = "Warning") -> None:
    """Display warning toast."""
    _show(root, title, message, "warning")


def show_warning(root: tk.Tk | tk.Toplevel, message: str, title: str = "Warning") -> None:
    """Display warning toast."""
    _show(root, title, message, "warning")


def _show(root: tk.Misc, title: str, message: str, bootstyle: str) -> None:  # noqa: D401
    if ToastNotification is None:
        _fallback(title, message, "error" if bootstyle == "danger" else "info")
        return

    try:
        toast = ToastNotification(title=title, message=message, duration=3500, bootstyle=bootstyle, position=(root.winfo_x() + 40, root.winfo_y() + 40))
        toast.show_toast()
    except Exception:
        _fallback(title, message)