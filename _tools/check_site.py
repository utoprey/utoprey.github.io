"""Validate generated pages before automatic publication; no network requests."""
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def check_site(root=ROOT):
    data = json.loads((root / '_data/profile.json').read_text())
    expected = {f'paper-{r["id"]}' for r in data['publications'] if r.get('show_on_site', True)}
    hidden = {f'paper-{r["id"]}' for r in data['publications'] if not r.get('show_on_site', True)}
    for file in [root / 'index.html', root / 'ru/index.html']:
        soup = BeautifulSoup(file.read_text(), 'html.parser')
        ids = [tag['id'] for tag in soup.select('[id]')]
        assert len(ids) == len(set(ids)), f'Duplicate HTML IDs: {file}'
        assert {r['id'] for r in soup.select('.publication-item')} == expected
        assert not hidden.intersection(ids), 'Hidden publications reappeared'
        for tag in soup.select('a[href], img[src], link[href]'):
            url = urlsplit(tag.get('src', tag.get('href', '')))
            assert url.scheme in ('', 'https', 'http', 'mailto', 'data'), 'Unsafe URL scheme'
            if url.scheme or url.netloc:
                continue
            if url.path.startswith('/'):
                path = root / unquote(url.path).lstrip('/')
                assert path.exists(), f'Missing file: {url.path}'
            elif not url.path and url.fragment:
                assert url.fragment in ids, f'Missing anchor: {url.fragment}'
        schema = json.loads(soup.find('script', type='application/ld+json').string)
        assert schema['mainEntity']['@type'] == 'Person'
        assert soup.select_one('meta[name="google-site-verification"]')
        print(f'Validated {file.relative_to(root)}')
    assert (root / 'experience/EkaterinaAntipushinaCV.pdf').is_file()
    assert (root / 'google39fa2f8eb4e57bc5.html').is_file()


if __name__ == '__main__':
    check_site()
