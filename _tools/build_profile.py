"""Refresh the EN/RU profile sections and the public CV from one content file.

Run with Python (beautifulsoup4) and XeLaTeX installed. Generated HTML and PDF
are committed so GitHub Pages needs no custom build configuration.
"""
import json
import subprocess
import tempfile
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / '_data/profile.json').read_text())
LABELS = {
    'en': {
        'accepted': 'Accepted papers · 2026',
        'published': 'Published papers',
        'preprint': 'Preprints',
        'status': {'accepted': 'Accepted for publication', 'published': 'Published', 'preprint': 'Preprint · not peer reviewed'},
        'intro': 'Papers, accepted contributions, and preprints. Posters and talks are listed below.',
        'scholar': 'Google Scholar', 'rg': 'ResearchGate',
        'cv': 'Academic CV · PDF · September 2026',
        'updated': 'Profile and CV updated September 2026',
        'poster': 'Poster', 'view': 'View poster',
    },
    'ru': {
        'accepted': 'Принятые работы · 2026',
        'published': 'Опубликованные работы',
        'preprint': 'Препринты',
        'status': {'accepted': 'Принято к публикации', 'published': 'Опубликовано', 'preprint': 'Препринт · без рецензирования'},
        'intro': 'Опубликованные и принятые работы, а также препринты. Постеры и доклады представлены ниже.',
        'scholar': 'Google Scholar', 'rg': 'ResearchGate',
        'cv': 'Академическое CV · PDF на английском · сентябрь 2026',
        'updated': 'Профиль и CV обновлены в сентябре 2026',
        'poster': 'Постер', 'view': 'Открыть постер',
    },
}


def a(url, label, cls='paper-link'):
    extra = ' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else ''
    return f'<a class="{cls}" href="{escape(url, quote=True)}"{extra}>{escape(label)}</a>'


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def render_pages():
    for lang, file in [('en', ROOT / 'index.html'), ('ru', ROOT / 'ru/index.html')]:
        s = BeautifulSoup(file.read_text(), 'html.parser')
        labels = LABELS[lang]
        timeline = s.select_one('.timeline')
        timeline.clear()
        for row in DATA['timeline']:
            timeline.append(fragment('<div class="timeline-item fade-in">' + ''.join(
                f'<div class="{cls}">{escape(row[key][lang])}</div>'
                for key, cls in [('title', 'exp-title'), ('company', 'exp-company'),
                                 ('period', 'exp-duration'), ('description', 'exp-description')]
            ) + '</div>'))
        grid = s.select_one('.projects-grid')
        grid.clear()
        for row in DATA['projects']:
            link = f'<p class="project-kicker">{a(row["url"], row["link"][lang])}</p>' if row['url'] else ''
            grid.append(fragment(f'''<div class="project-card fade-in">
              <div class="project-header"><div>
                <div class="project-title">{escape(row['title'][lang])}</div>
                <div class="project-period">{escape(row['period'][lang])}</div>
              </div></div><div class="project-content">
                <div class="project-description">{escape(row['description'][lang])}</div>
                <div class="tech-stack">{''.join(f'<span class="tech-tag">{escape(t)}</span>' for t in row['tags'])}</div>
                {link}
              </div></div>'''))
        papers = s.select_one('#research-papers')
        heading = papers.select_one('h3').extract()
        papers.clear()
        papers.append(heading)
        papers.append(fragment(f'<p class="publications-intro">{escape(labels["intro"])}<br>'
                              f'{a("https://scholar.google.com/citations?user=7VOBHhMAAAAJ", labels["scholar"])} · '
                              f'{a("https://www.researchgate.net/profile/Ekaterina-Antipushina", labels["rg"])}</p>'))
        for status in ['accepted', 'published', 'preprint']:
            papers.append(fragment(f'<h4 class="publication-group-title">{labels[status]}</h4>'))
            for row in DATA['publications']:
                if row['status'] != status:
                    continue
                venue = row['venue']
                if lang == 'ru' and venue == 'Conference paper':
                    venue = 'Материалы конференции'
                papers.append(fragment(f'''<div class="publication-item fade-in" id="paper-{row['id']}">
                  <div class="pub-title">{a(row['url'], row['title'])}</div>
                  <div class="pub-authors">{escape(row['authors'])}</div>
                  <div class="pub-venue">{escape(venue)} · {row['year']}</div>
                  <div class="pub-note">{labels['status'][status]}</div>
                </div>'''))
        # Preserve the two existing poster thumbnails and add the missing records.
        poster_grid = s.select_one('.posters-grid')
        for card in poster_grid.select('[data-profile-poster]'):
            card.decompose()
        for row in DATA['posters'][2:]:
            poster_grid.append(fragment(f'''<div class="poster-card fade-in" data-profile-poster="true">
              <div class="poster-content"><h3>{escape(row['title'])}</h3>
              <p>{labels['poster']} · {row['year']}</p>
              {a(row['url'], labels['view'], 'poster-link')}</div></div>'''))
        s.select_one('.cv-link .download-btn').string = labels['cv']
        for link in s.select('a[href]'):
            if link['href'].split('?')[0] == '/experience/EkaterinaAntipushinaCV.pdf':
                link['href'] = '/experience/EkaterinaAntipushinaCV.pdf?v=' + DATA['updated']
        # Dates in the visible footer and structured profile refer to this update.
        for old in s.select('.profile-updated'):
            old.decompose()
        footer = s.find('footer')
        footer.append(fragment(f'<p class="profile-updated">{labels["updated"]}</p>'))
        schema_node = s.find('script', type='application/ld+json')
        schema = json.loads(schema_node.string)
        schema['dateModified'] = DATA['updated']
        schema_node.string = '\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
        for tag in s.find_all('svg'):
            if 'viewbox' in tag.attrs:
                tag['viewBox'] = tag.attrs.pop('viewbox')
        for link in s.select('a[href]'):
            if link['href'] == 'https://opennft.org/':
                link['href'] = 'https://github.com/OpenNFT/pyOpenNFT'
        file.write_text(s.prettify())


def tex(text):
    chars = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
             '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(chars.get(c, c) for c in str(text))


def href(url, label):
    if url.startswith('/'):
        url = 'https://utoprey.github.io' + url
    return r'\href{' + url + '}{' + tex(label) + '}'


def render_cv():
    header = r'''\documentclass[10pt,a4paper]{article}
\usepackage{fontspec}
\setmainfont{Arial}
\usepackage[a4paper,left=17mm,right=17mm,top=16mm,bottom=17mm]{geometry}
\usepackage{titlesec,enumitem,xcolor,tabularx,array,fancyhdr,hyperref}
\definecolor{accent}{HTML}{174A63}
\definecolor{muted}{HTML}{52616B}
\hypersetup{colorlinks=true,urlcolor=accent,pdftitle={Ekaterina Antipushina | Academic CV},pdfauthor={Ekaterina Antipushina}}
\urlstyle{same}
\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\fancyfoot[L]{\scriptsize\color{muted}Ekaterina Antipushina · NeuroAI \& Embodied AI}
\fancyfoot[R]{\scriptsize\color{muted}September 2026 · \thepage}
\setlength{\footskip}{22pt}\setlength{\parindent}{0pt}\setlength{\tabcolsep}{0pt}
\setlength{\emergencystretch}{2em}\raggedright
\titleformat{\section}{\large\bfseries\color{accent}}{}{0pt}{}[\vspace{-2pt}\titlerule]
\titlespacing*{\section}{0pt}{9pt}{5pt}
\setlist[enumerate]{leftmargin=15pt,itemsep=5pt,topsep=4pt,parsep=0pt}
\newcommand{\entry}[3]{\vspace{4pt}\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}X r@{}}\textbf{#1}&{\small\color{muted}#2}\\\end{tabularx}\par{\small\color{muted}#3}\par\vspace{2pt}}
\begin{document}\fontsize{10.5}{12.6}\selectfont
{\fontsize{25}{29}\selectfont\bfseries Ekaterina Antipushina}\par\vspace{4pt}
{\large\color{accent}NeuroAI \& Embodied AI · ML Research \& Engineering}\par\vspace{6pt}
\href{mailto:ekantipushina@gmail.com}{ekantipushina@gmail.com} · Moscow, Russia\par
\href{https://utoprey.github.io/}{Website} · \href{https://scholar.google.com/citations?user=7VOBHhMAAAAJ}{Google Scholar} · \href{https://orcid.org/0009-0009-9708-440X}{ORCID} · \href{https://github.com/utoprey}{GitHub} · \href{https://www.linkedin.com/in/katherine-antipushina/}{LinkedIn}\par
\section{Research profile}
Researcher and machine-learning engineer working on multimodal learning for neural signals, medical images, and 3D scenes. Research spans representation learning, generative modeling, real-time neurofeedback, and spatial reasoning with vision-language models. PhD student at Skoltech and ML Engineer at the Spatial Intelligence Lab, Applied AI Institute.
\section{Research and engineering experience}
'''
    out = [header]
    for row in DATA['timeline']:
        if row['kind'] != 'work':
            continue
        out.append(r'\entry{' + tex(row['title']['en']) + '}{' + tex(row['period']['en']) + '}{' + tex(row['company']['en']) + '}\n')
        out.append(tex(row['description']['en']) + '\\par\n')
    out.append(r'\section{Education}' + '\n')
    for row in DATA['timeline']:
        if row['kind'] != 'education':
            continue
        out.append(r'\textbf{' + tex(row['title']['en']) + '} · ' + tex(row['company']['en']) + ' · ' + tex(row['period']['en']) + r'\par\vspace{3pt}' + '\n')
    out.append(r'\section{Methods and tools}' + '\n')
    out.append('Python, PyTorch, TensorFlow, scikit-learn, NumPy/pandas; Transformers, VAE/GAN, optimal transport; multimodal fusion, statistical modeling, subject-wise validation; FastAPI, multiprocessing, Docker, Git, Linux, GPU computing.\\par\n')
    out.append(r'\newpage\section{Publications and preprints}' + '\n')
    out.append(r'\begingroup\fontsize{10.2}{12.5}\selectfont' + '\n')
    for status in ['accepted', 'published', 'preprint']:
        out.append(r'\subsection*{' + LABELS['en'][status] + '}\n')
        out.append(r'\begin{enumerate}' + '\n')
        for row in DATA['publications']:
            if row['status'] != status:
                continue
            link_label = row['url'].split('doi.org/')[-1] if 'doi.org/' in row['url'] else ('OpenReview' if 'openreview.net' in row['url'] else 'Publication record')
            out.append(r'\item ' + tex(row['authors']) + ' ' + r'\textit{' + tex(row['title']) + '}. ' + tex(row['venue']) + ', ' + str(row['year']) + '. ' + href(row['url'], link_label) + '.\n')
        out.append(r'\end{enumerate}' + '\n')
    out.append(r'\endgroup\newpage\section{Research and software projects}' + '\n')
    out.append(r'\begingroup\fontsize{10.2}{12.5}\selectfont' + '\n')
    for row in DATA['projects']:
        title = href(row['url'], row['title']['en']) if row['url'] and not row['url'].startswith('#') else tex(row['title']['en'])
        out.append(r'\textbf{' + title + r'}\par ' + tex(row['description']['en']) + r'\par\vspace{5pt}' + '\n')
    out.append(r'\section{Posters}' + '\n')
    for row in DATA['posters']:
        out.append(href(row['url'], row['title']) + '. ' + tex(row['venue']) + ', ' + str(row['year']) + r'.\par\vspace{4pt}' + '\n')
    out.append(r'\section{Research talks}' + '\n')
    out.append('Universal Brain Encoder: The Evolution of Models for Neural Signals. NeuroTalk, MISIS University, April 2026.\\par\\vspace{4pt}\n')
    out.append('Bridge Between Time and Space: How Generative AI Turns EEG into fMRI. DataFest (ODS), March 2025.\\par\n')
    out.append(r'\endgroup\end{document}' + '\n')
    source = ROOT / '_cv/academic.tex'
    source.parent.mkdir(exist_ok=True)
    source.write_text(''.join(out))
    with tempfile.TemporaryDirectory(prefix='utoprey-cv-build-') as tmp:
        for _ in range(2):
            result = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', '-output-directory', tmp, str(source)], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout[-6000:] + result.stderr)
        log = (Path(tmp) / 'academic.log').read_text()
        if 'Overfull' in log:
            print('Layout warnings:', '\n'.join(l for l in log.splitlines() if 'Overfull' in l))
        (ROOT / 'experience/EkaterinaAntipushinaCV.pdf').write_bytes((Path(tmp) / 'academic.pdf').read_bytes())


if __name__ == '__main__':
    render_pages()
    render_cv()
    print('Updated English and Russian profiles and academic CV.')
