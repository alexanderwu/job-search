from datetime import datetime, timedelta
import importlib
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from IPython.display import HTML, Markdown, display
import pandas as pd

TZ_LA = ZoneInfo('America/Los_Angeles')


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

def tailwind_css():
    return HTML('<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>')

def display_code(code: str, language: str = 'python'):
    markdown_code = f'```{language}\n{code}\n```'
    display(Markdown(markdown_code))


def now(time=True, file=True, days=0) -> str:
    datetime_now = datetime.now() - timedelta(days=days)
    if time:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d_%H%M%S")
        return datetime_now.strftime(r"%#I:%M%p").lower()
    else:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d")
        return datetime_now.strftime(r"%#m/%#d/%y (%A)")

def paths(path=Path.cwd(), glob='*', mtime=None) -> pd.Series:
    paths_series = pd.Series([p for p in path.glob(glob)])
    if isinstance(mtime, int):
        mtime = pd.Timestamp.now() - pd.Timedelta(days=mtime)
    if mtime:
        _mtimes = paths_series.apply(lambda x: x.stat().st_mtime).pipe(pd.to_datetime, unit='s')
        _mtimes_mask = _mtimes >= pd.Timestamp(mtime)
        paths_series = paths_series[_mtimes_mask]
    return paths_series

def paths_df(path=Path.cwd(), glob='*', mtime=None) -> pd.DataFrame:
    paths_series = pd.Series([p for p in path.glob(glob)])
    paths_size = paths_series.apply(lambda x: x.stat().st_size)
    # paths_ctimes = paths_series.apply(lambda x: x.stat().st_ctime).pipe(pd.to_datetime, unit='s', tzinfo=TZ_LA)
    paths_mtimes = paths_series.apply(lambda x: x.stat().st_mtime).pipe(pd.to_datetime, unit='s', tzinfo=TZ_LA)
    df = pd.DataFrame({
        'path': paths_series,
        'size': paths_size,
        # 'ctime': paths_ctimes,
        'mtime': paths_mtimes,
    }).sort_values('mtime', ascending=False, ignore_index=True)
    if isinstance(mtime, int):
        mtime = pd.Timestamp.now() - pd.Timedelta(days=mtime)
    if mtime:
        df = df.query('mtime >= @mtime')
    return df

def path_names(path=Path.cwd(), glob='*', stem=True) -> pd.Series:
    if stem:
        return pd.Series([p.stem for p in path.glob(glob)])
    return pd.Series([p.name for p in path.glob(glob)])


def open(path):
    import subprocess
    subprocess.Popen(f'explorer "{path}"')


def is_running_wsl() -> bool:
    """
    Checks if the current Python script is running within WSL.
    """
    # if os.path.exists("/proc/version"):
    #     with open("/proc/version", mode='r') as f:
    #         version_info = f.read()
    #     return "Microsoft" in version_info
    # return False
    return os.path.exists("/proc/version")
