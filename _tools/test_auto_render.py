"""Exercise external metadata through the real bilingual HTML builder."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
import build_profile as build


class AutoRenderTest(unittest.TestCase):
    def test_bilingual_safe_render_preserves_editorial_work_and_cv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in ['index.html', 'ru/index.html', 'sitemap.xml', 'experience/EkaterinaAntipushinaCV.pdf']:
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((build.ROOT / rel).read_bytes())
            original_cv = (root / 'experience/EkaterinaAntipushinaCV.pdf').read_bytes()
            data = copy.deepcopy(build.DATA)
            auto = {'content_updated': '2026-10-04', 'projects': [{
                'id': 'github-123', 'name': 'new-project', 'description': '<script>alert(1)</script>',
                'url': 'https://github.com/utoprey/new-project', 'tags': ['Python', '<img src=x>'],
            }], 'publications': [{
                'id': 'scholar-new', 'title': '<img src=x onerror=alert(1)> A new paper', 'authors': 'E Antipushina & A Researcher',
                'venue': 'A journal', 'year': None, 'url': 'https://scholar.google.com/citations?user=7VOBHhMAAAAJ',
            }, {
                'id': 'scholar-hidden', 'title': next(r['title'] for r in data['publications'] if not r.get('show_on_site', True)),
            }]}
            with patch.object(build, 'ROOT', root), patch.object(build, 'DATA', data), patch.object(build, 'AUTO', auto):
                build.render_pages()
                first = {lang: (root / file).read_text() for lang, file in [('en', 'index.html'), ('ru', 'ru/index.html')]}
                build.render_pages()
                for lang, file in [('en', 'index.html'), ('ru', 'ru/index.html')]:
                    s = BeautifulSoup((root / file).read_text(), 'html.parser')
                    self.assertEqual(len(s.select('.publication-item')), 8)
                    self.assertEqual(len(s.select('.auto-publication')), 1)
                    self.assertEqual(len(s.select('.auto-projects .project-card')), 1)
                    self.assertFalse(s.select('.auto-projects script, .auto-projects img, .auto-publications img'))
                    self.assertIn('<script>alert(1)</script>', s.select_one('.auto-projects').get_text())
                    self.assertIsNone(s.select_one('#scholar-hidden'))
                    schema = json.loads(s.find('script', type='application/ld+json').string)
                    self.assertEqual(schema['dateModified'], '2026-10-04')
                    self.assertEqual((root / file).read_text(), first[lang])
                self.assertEqual((root / 'experience/EkaterinaAntipushinaCV.pdf').read_bytes(), original_cv)
                self.assertIn('<lastmod>2026-10-04</lastmod>', (root / 'sitemap.xml').read_text())


if __name__ == '__main__':
    unittest.main()
