#!/usr/bin/env python3

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from wivet_score import count_score_wivet

RESULTS_DIR = str(Path(__file__).resolve().parent.parent / 'data' / 'results')

CRAWLERS = [
    'arachni',
    'crawljax',
    'enemy-of-the-state',
    'htcap',
    'w3af',
    'wget'
]

CRNAMES = {
    'arachni': 'Arachni',
    'crawljax': 'Crawljax',
    'enemy-of-the-state': 'Enemy of the State',
    'htcap': 'Htcap',
    'w3af': 'w3af',
    'wget': 'wget'
    
}

STNAMES = {
    'dvwa': 'DVWA',
    'juice-shop': 'JuiceShop',
    'mybb' : 'MyBB',
    'web-goat': 'WebGoat',
    'wivet': 'WIVET'
    
}

STANDS = [
    'dvwa',
    'juice-shop',
    'mybb',
    'web-goat',
    'wivet'
]

SCORE_COUNTERS = {
    'wivet': count_score_wivet
}


def fmt_count(cnt, cnt_max):
    if cnt < 0:
        return 'N/A'
    if cnt == cnt_max:
        return f'[green]{cnt}[/green]'
    return str(cnt)

def fmt_count_tex(cnt, cnt_max):
    if cnt < 0:
        return 'N/A'
    if cnt == cnt_max:
        return r'\textbf{' + str(cnt) + '}'
    return str(cnt)

def analyzer_result(stand_name):
    try:
        with open(RESULTS_DIR + '/analyzer-prototype-' + stand_name + '.json') as f:
            return count_score(stand_name, json.load(f))
    except FileNotFoundError:
        return -1

def count_score(stand_name, data):
    if stand_name in SCORE_COUNTERS:
        return SCORE_COUNTERS[stand_name](data)
    return len(data)

table = Table()

table.add_column("Stand")

for cr in CRAWLERS:
    table.add_column(cr)

table.add_column('analyzer')

trows = []

for st in STANDS:
    row = [st]
    counts = []
    trows.append(counts)
    for cr in CRAWLERS:
        fname = RESULTS_DIR + '/' + cr + '-' + st + '.json'
        try:
            print(fname)
            with open(fname) as f:
                data = json.load(f)
                counts.append(count_score(st, data))
        except FileNotFoundError:
            counts.append(-1)
    counts.append(analyzer_result(st))
    cnt_max = max(counts)
    row += [fmt_count(cnt, cnt_max) for cnt in counts]
    table.add_row(*row)

print(r'''\begin{table}
    \caption{Unique endpoints per application and tool}\label{tab:analyzerscomparison2}
    \centering''')
print(r'    \begin{tabular}{|' + '|'.join(['c'] * (len(CRAWLERS) + 2)) + '|}')
print(r'       \hline')
print('       ' + ' & '.join(['Name'] + [CRNAMES[n] for n in CRAWLERS] + [r'\emph{Prototype}']) + r' \\')
print(r'       \hline\hline')
for i, r in enumerate(trows):
    print('       ' + ' & '.join([STNAMES[STANDS[i]]] + [fmt_count_tex(el, max(r)) for el in r]) + r' \\')
    print(r'       \hline')
print(r'''    \end{tabular}
\end{table}
''')


console = Console()
console.print(table)