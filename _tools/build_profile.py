"""Refresh EN/RU profile sections without overwriting the selected public CV.

Run with Python and beautifulsoup4. XeLaTeX is only needed for --cv-draft.
Generated HTML is committed so GitHub Pages needs no custom build configuration.
"""
import argparse
import json
import re
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
        'updated': 'Profile updated October 2026',
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
        'updated': 'Профиль обновлён в октябре 2026',
        'poster': 'Постер', 'view': 'Открыть постер',
    },
}


def a(url, label, cls='paper-link'):
    extra = ' target="_blank" rel="noopener noreferrer"' if url.startswith('https://') else ''
    return f'<a class="{cls}" href="{escape(url, quote=True)}"{extra}>{escape(label)}</a>'


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def resource_link(url, label, lang):
    labels = {'Paper': 'Статья', 'Code': 'Код', 'Event': 'Анонс',
              'Slides': 'Слайды', 'Recording': 'Запись'}
    return a(url, labels.get(label, label) if lang == 'ru' else label, 'research-link')


def research_media(row, lang, url):
    """Use the author's paper figure, or an honest typographic cover."""
    title = row['title']
    if row.get('image'):
        content = (f'<img src="{escape(row["image"], quote=True)}" alt="" '
                   f'loading="lazy" decoding="async" width="{row.get("image_width", 600)}" '
                   f'height="{row.get("image_height", 360)}">')
        cls = 'research-media'
    else:
        cover = row['cover']
        year = row.get('year', row.get('date', '')[:4])
        content = (f'<span class="cover-venue">{escape(cover["venue"])}</span>'
                   f'<span class="cover-topic">{escape(cover["topic"])}</span>'
                   f'<span class="cover-year">{year}</span>')
        cls = 'research-media research-cover'
    label = ('Открыть: ' if lang == 'ru' else 'Open: ') + title
    return (f'<a class="{cls}" href="{escape(url, quote=True)}" '
            f'aria-label="{escape(label, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{content}</a>')


def render_research(s, lang):
    papers = s.select_one('#research-papers')
    papers['class'] = ['research-section', 'research-list']
    papers.clear()
    title = 'Publications' if lang == 'en' else 'Публикации'
    intro = ('Journal and conference papers, accepted work, and preprints.' if lang == 'en'
             else 'Журнальные статьи, материалы конференций, принятые работы и препринты.')
    cv = '/experience/EkaterinaAntipushinaCV.pdf?v=' + DATA['updated']
    papers.append(fragment(f'<h3 class="section-title">{title}</h3><p class="publications-intro">{intro}</p>'
                           '<div class="research-resources">' +
                           a('https://scholar.google.com/citations?user=7VOBHhMAAAAJ', 'Google Scholar', 'research-link') +
                           a(cv, 'CV · PDF', 'research-link') + '</div>'))
    visible_papers = [p for p in DATA['publications'] if p.get('show_on_site', True)]
    for year in sorted({p['year'] for p in visible_papers}, reverse=True):
        group = fragment(f'<section class="publication-year" aria-labelledby="papers-{year}">'
                         f'<h4 class="publication-group-title" id="papers-{year}">{year}</h4>'
                         '<div class="publication-list"></div></section>')
        for row in (p for p in visible_papers if p['year'] == year):
            authors = escape(row['authors']).replace('Antipushina E.', '<strong>Antipushina E.</strong>')
            venue = row['venue']
            if lang == 'ru' and venue == 'Conference paper':
                venue = 'Материалы конференции'
            status = ''
            if row['status'] != 'published':
                text = {'accepted': ('Accepted', 'Принято'), 'preprint': ('Preprint', 'Препринт')}[row['status']][lang == 'ru']
                status = f'<span class="pub-status">{text}</span>'
            main_label = 'OpenReview' if 'openreview.net' in row['url'] else 'Paper'
            links = resource_link(row['url'], main_label, lang)
            links += ''.join(resource_link(l['url'], l['label'], lang) for l in row.get('links', []))
            group.select_one('.publication-list').append(fragment(f'''<article class="publication-item research-row" id="paper-{row['id']}">
              {research_media(row, lang, row['url'])}
              <div class="research-row-content">
                <h5 class="pub-title">{a(row['url'], row['title'])}</h5>
                <p class="pub-authors">{authors}</p>
                <p class="pub-venue"><cite>{escape(venue)}</cite>, {row['year']} {status}</p>
                <div class="research-resources">{links}</div>
              </div></article>'''))
        papers.append(group)

    talks = s.select_one('#research-talks')
    talks['class'] = ['research-section', 'research-list']
    talks.clear()
    heading = 'Invited talks & presentations' if lang == 'en' else 'Приглашённые доклады и выступления'
    talks.append(fragment(f'<h3 class="section-title">{escape(heading)}</h3>'))
    for row in DATA['talks']:
        label = ('Invited talk' if lang == 'en' else 'Приглашённый доклад') if row['invited'] else ('Conference talk' if lang == 'en' else 'Доклад на конференции')
        links = ''.join(resource_link(l['url'], l['label'], lang) for l in row['links'])
        summary = 'About the talk' if lang == 'en' else 'О докладе'
        talks.append(fragment(f'''<article class="talk-item research-row" id="talk-{row['id']}">
          {research_media(row, lang, row['links'][0]['url'])}
          <div class="research-row-content">
            <p class="talk-kind">{label}</p>
            <h4 class="talk-title">{a(row['links'][0]['url'], row['title'])}</h4>
            <p class="talk-venue">{escape(row['venue'][lang])}</p>
            <p class="talk-date"><time datetime="{row['date']}">{row['date_label'][lang]}</time></p>
            <div class="research-resources">{links}</div>
            <details class="talk-abstract"><summary>{summary}</summary><p>{escape(row['description'][lang])}</p></details>
          </div></article>'''))
    render_posters(s, lang)
    s.select_one('.research-nav-btn[href="#research-talks"]').string = 'Talks' if lang == 'en' else 'Доклады'
    s.select_one('link[rel="stylesheet"][href^="/assets/site.css"]')['href'] = '/assets/site.css?v=' + DATA.get('assets_version', DATA['page_updated'])
    schema_node = s.find('script', type='application/ld+json')
    schema = json.loads(schema_node.string)
    schema['dateModified'] = DATA['page_updated']
    schema_node.string = '\n' + json.dumps(schema, ensure_ascii=False, indent=2) + '\n'
    # Keep punctuation next to inline author names and venue citations.
    for tag in s.select('.pub-authors, .pub-venue'):
        tag.preserve_whitespace_tags = {'p'}
    for tag in s.select('.bio-section .section-content > p'):
        # Collapse formatting whitespace while retaining linked/bold prose.
        markup = ' '.join(tag.decode_contents().split())
        markup = re.sub(r'(<(?:strong|a)\b[^>]*>)\s+', r'\1', markup)
        markup = re.sub(r'\s+(</(?:strong|a)>)', r'\1', markup)
        markup = re.sub(r'\s+([,.;:])', r'\1', markup)
        tag.clear()
        tag.append(fragment(markup))
        tag.preserve_whitespace_tags = {'p'}


def render_posters(s, lang):
    grid = s.select_one('.posters-grid')
    grid.clear()
    for row in DATA['posters']:
        label = ('Открыть: ' if lang == 'ru' else 'Open: ') + row['title']
        note = row.get('image_note', {}).get(lang, '')
        caption = f'<figcaption>{escape(note)}</figcaption>' if note else ''
        link_label = ('Publication record' if lang == 'en' else 'Страница работы') if row.get('record_only') else LABELS[lang]['view']
        grid.append(fragment(f'''<article class="poster-card fade-in" id="poster-{row['id']}">
          <figure class="poster-preview">
            <a class="poster-image" href="{escape(row['url'], quote=True)}" aria-label="{escape(label, quote=True)}" target="_blank" rel="noopener noreferrer">
              <img src="{escape(row['image'], quote=True)}" alt="" loading="lazy" decoding="async" width="{row['image_width']}" height="{row['image_height']}">
            </a>{caption}
          </figure>
          <div class="poster-content"><h4>{escape(row['title'])}</h4>
            <p class="poster-venue">{escape(row['venue'])} · {row['year']}</p>
            {a(row['url'], link_label, 'poster-link')}
          </div></article>'''))


def render_research_pages():
    for lang, file in [('en', ROOT / 'index.html'), ('ru', ROOT / 'ru/index.html')]:
        s = BeautifulSoup(file.read_text(), 'html.parser')
        render_research(s, lang)
        for tag in s.find_all('svg'):
            if 'viewbox' in tag.attrs:
                tag['viewBox'] = tag.attrs.pop('viewbox')
        file.write_text(s.prettify())


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
        render_research(s, lang)
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
        schema['dateModified'] = DATA.get('page_updated', DATA['updated'])
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
        (ROOT / '_cv/academic-draft.pdf').write_bytes((Path(tmp) / 'academic.pdf').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research-only', action='store_true', help='Render publications, posters and talks only.')
    parser.add_argument('--cv-draft', action='store_true', help='Also generate _cv/academic-draft.pdf; never replace the selected public CV.')
    args = parser.parse_args()
    if args.research_only:
        render_research_pages()
        print('Updated English and Russian publications, posters and talks.')
    else:
        render_pages()
        print('Updated English and Russian profiles; public CV preserved.')
    if args.cv_draft:
        render_cv()
        print('Generated _cv/academic-draft.pdf for review.')
