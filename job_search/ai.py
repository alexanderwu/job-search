from functools import cache
from pathlib import Path

from IPython.display import Markdown, display
import lmstudio as lms

from job_search.config import P_RESUME
from job_search.resume import analyze

PROMPT_ATS = "Pretend you are an advanced Applicant Tracking System. Read the job description below and extract industry keywords and output a bulleted list. Ignore keywords about employee benefits:"
PROMPT_7 = "Summarize top seven job requirements (domain area, expertise, soft skills) and top seven nice-to-haves. Ignore details of location, compensation, travel, benefits. Format as concise bullet points:"


def load_resume(verbose=False):
    return load_md(P_RESUME, verbose)

def load_md(_md, verbose=False):
    if isinstance(_md, Path):
        with open(_md) as f:
            _md = f.read()
    if verbose:
        display(Markdown(str(_md)))
    else:
        return str(_md)

def load_resume38(verbose=False):
    resume38 = analyze(P_RESUME).iloc[3:38]['_markdown'].pipe('\n'.join)
    return load_md(resume38, verbose)

def llm_extract(_md, prompt=PROMPT_7, model="qwen/qwen3-4b-2507", verbose=False):
    _md = load_md(_md)
    _message = f"{prompt}\n\n{_md}"
    return llm_respond(_message, model=model, verbose=verbose)

def llm_respond(_md, model="qwen/qwen3-4b-2507", verbose=True):
    result = _llm_respond(_md)
    return load_md(result, verbose)


@cache
def _llm_respond(message, model="qwen/qwen3-4b-2507"):
    message = load_md(message)
    _model = lms.llm(model)
    result = _model.respond(message)
    return result
