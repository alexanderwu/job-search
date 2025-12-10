# %%
from pathlib import Path
import job_search.dataset as dat
import job_search.config as conf
from job_search.config import P_DATE, P_QUERIES

# %%
P_query = P_QUERIES / ('DS_NorCal_Remote.txt')
P_save = dat.main0(P_query, overwrite=False)
jdf = dat.load_jdf(P_save)
jdf
# %%
with open(P_save, encoding='utf-8') as f:
    html_string = f.read()

# %%
import lxml.html
_CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
tree = lxml.html.fromstring(html_string)
_title_elem = tree.xpath('head/title')
if _title_elem:
    company_ = f"{_title_elem[0].text}_"
all_cards = tree.xpath(_CLASS)
len(all_cards)
# %%
card = all_cards[0]
print(lxml.html.tostring(card).decode())
card.xpath('div/div/span')

# %%
def tailwind_css():
    return HTML('<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>')

# %%
tailwind_css()
# %%
from IPython.display import HTML
HTML(lxml.html.tostring(card).decode())
