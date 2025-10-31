import importlib
import sys

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
