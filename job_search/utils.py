from pathlib import Path
import importlib
import sys

import pandas as pd
from IPython.display import HTML


def reload(module=None):
    """Reload module (for use in Jupyter Notebook)

    Args:
        module (types.ModuleType, optional): module to reload
    """
    importlib.reload(module or sys.modules[__name__])


def jupyter_css_style():
    css_style = HTML("""
        <!-- https://stackoverflow.com/questions/71534901/make-tqdm-bar-dark-in-vscode-jupyter-notebook -->
        <style>
        .cell-output-ipywidget-background {
            background-color: transparent !important;
        }
        :root {
            --jp-widgets-color: var(--vscode-editor-foreground);
            --jp-widgets-font-size: var(--vscode-editor-font-size);
        }
        </style>
    """)
    return css_style


def display_code(code: str, language: str = 'python'):
    from IPython.display import display, Markdown
    markdown_code = f'```{language}\n{code}\n```'
    display(Markdown(markdown_code))


def now(time=True, file=True) -> str:
    from datetime import datetime
    datetime_now = datetime.now()
    if time:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d_%H%M%S")
        return datetime_now.strftime(r"%#I:%M%p").lower()
    else:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d")
        return datetime_now.strftime(r"%#m/%#d/%y (%A)")

def path_names(path: Path, glob='*', stem=True) -> pd.Series:
    if stem:
        return pd.Series([p.stem for p in path.glob(glob)])
    return pd.Series([p.name for p in path.glob(glob)])


def open(path):
    import subprocess
    subprocess.Popen(f'explorer "{path}"')


def is_wsl() -> bool:
    """
    Checks if the current Python script is running within WSL.
    """
    import os
    if os.path.exists("/proc/version"):
        with open("/proc/version", 'r') as f:
            version_info = f.read()
        return "Microsoft" in version_info
    return False
