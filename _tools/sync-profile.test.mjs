import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyState, fetchRepositories, fetchScholar, parseScholar, selectProjects, selectPublications, synchronize } from './sync-profile.mjs';

const config = {
  github: { username: 'utoprey', exclude_repositories: ['neuroacquire', 'utoprey.github.io'], exclude_topics: ['website-hide'], include_existing_repositories: [] },
  scholar: { author_id: '7VOBHhMAAAAJ', profile_names: ['Ekaterina Antipushina'], exclude_titles: [], exclude_title_fragments: ['NeuroAcquire'], exclude_citation_ids: [] },
};
const profile = { projects: [{ id: 'curated', title: { en: 'Curated', ru: 'Проект' }, url: 'https://github.com/utoprey/curated' }],
  publications: [{ id: 'hidden', title: 'A hidden publication', show_on_site: false }], posters: [{ title: 'A conference poster' }] };
const repo = (id, name, extra = {}) => ({ id, name, owner: { login: 'utoprey' }, private: false, visibility: 'public', fork: false, archived: false,
  disabled: false, size: 10, topics: [], created_at: '2026-10-04T00:00:00Z', language: 'Python', description: 'An original research project', ...extra });
const article = (id, title, year = 2026) => ({ id: `scholar-${id}`, source_id: `7VOBHhMAAAAJ:${id}`, title, authors: 'E Antipushina', venue: 'A venue', year, url: 'https://scholar.google.com/citations?user=7VOBHhMAAAAJ' });
const html = `<div id="gsc_prf_in">Ekaterina Antipushina</div><table><tr class="gsc_a_tr"><td>
  <a class="gsc_a_at" href="/citations?view_op=view_citation&amp;citation_for_view=7VOBHhMAAAAJ:abc-123">Neural &amp; visual representations</a>
  <div class="gs_gray">E Antipushina, A Researcher</div><div class="gs_gray">Conference, 2026</div></td><td class="gsc_a_y"><span>2026</span></td></tr></table>`;
const response = value => new Response(typeof value === 'string' ? value : JSON.stringify(value));
const now = new Date('2026-10-04T12:00:00Z');

test('Scholar HTML extracts metadata/entities and constructs an author-specific link', () => {
  const rows = parseScholar(html, config.scholar);
  assert.equal(rows[0].title, 'Neural & visual representations');
  assert.equal(rows[0].year, 2026);
  assert.equal(rows[0].source_id, '7VOBHhMAAAAJ:abc-123');
  assert.equal(new URL(rows[0].url).searchParams.get('user'), config.scholar.author_id);
  assert.equal(rows[0].status, undefined); // Inclusion on Scholar is not publication/peer-review status.
});

test('CAPTCHA, empty pages, other authors and malformed article identity are rejected', () => {
  for (const bad of ['<html>Our systems have detected unusual traffic</html>', '<div id="gsc_prf_in">Ekaterina Antipushina</div>',
    html.replace('Ekaterina Antipushina', 'Someone Else'), html.replace('7VOBHhMAAAAJ:abc-123', 'SomeoneElse:abc-123')]) {
    assert.throws(() => parseScholar(bad, config.scholar));
  }
});

test('public Scholar fetch respects the allowed profile URL and does not paginate cstart', async () => {
  await fetchScholar(config.scholar, { fetchImpl: async url => {
    assert.ok(url.startsWith('https://scholar.google.com/citations?user='));
    assert.equal(new URL(url).searchParams.has('cstart'), false);
    return response(html);
  } });
});

test('API pagination keeps requests on SerpApi even if a next-link points elsewhere', async () => {
  const urls = [];
  const rows = await fetchScholar(config.scholar, { serpApiKey: 'test-key', fetchImpl: async url => {
    urls.push(url);
    return response({ author: { name: 'Ekaterina Antipushina' }, articles: [{ citation_id: `7VOBHhMAAAAJ:page${urls.length}`, title: `Paper ${urls.length}`, authors: 'E Antipushina', publication: 'Journal', year: '2026' }],
      ...(urls.length === 1 ? { serpapi_pagination: { next: 'https://untrusted.example/?api_key=stolen' } } : {}) });
  } });
  assert.equal(rows.length, 2);
  assert.ok(urls.every(url => new URL(url).hostname === 'serpapi.com'));
  assert.equal(new URL(urls[1]).searchParams.get('start'), '100');
});

test('provider failures never echo secret-bearing response bodies or request URLs', async () => {
  await assert.rejects(fetchScholar(config.scholar, { serpApiKey: 'DO-NOT-LOG', fetchImpl: async () => response({ error: 'invalid DO-NOT-LOG key' }) }),
    error => !error.message.includes('DO-NOT-LOG'));
});

test('GitHub fetch paginates completely before reporting success', async () => {
  const urls = [];
  const rows = await fetchRepositories(config.github, { fetchImpl: async url => {
    urls.push(url); return response(urls.length === 1 ? Array.from({ length: 100 }, (_, i) => repo(i, `repo${i}`)) : [repo(101, 'last')]);
  } });
  assert.equal(rows.length, 101);
  assert.equal(new URL(urls[1]).searchParams.get('page'), '2');
});

test('only new original public repositories are imported; curated and hidden projects stay untouched', () => {
  const rows = [repo(1, 'old'), repo(2, 'new'), repo(3, 'fork', { fork: true }), repo(4, 'private', { private: true, visibility: 'private' }),
    repo(5, 'archived', { archived: true }), repo(6, 'neuroacquire'), repo(7, 'curated'), repo(8, 'hidden', { topics: ['website-hide'] }),
    repo(9, 'empty', { size: 0 }), repo(10, 'foreign', { owner: { login: 'other' } })];
  assert.deepEqual(selectProjects(rows, [1], profile, config.github).map(r => r.name), ['new']);
  assert.deepEqual(selectProjects([repo(1, 'old')], [1], profile, { ...config.github, include_existing_repositories: ['old'] }).map(r => r.name), ['old']);
});

test('hidden papers, existing posters, duplicates and excluded research cannot reappear', () => {
  const rows = [article('hidden', 'A hidden publication!'), article('poster', 'A conference poster'), article('new', 'A genuinely new paper'),
    article('duplicate', 'A genuinely new paper.'), article('excluded', 'NeuroAcquire: new experiment')];
  assert.deepEqual(selectPublications([], rows, profile, config.scholar).map(r => r.source_id), ['7VOBHhMAAAAJ:new']);
});

test('a public-profile window cannot erase older cached papers; metadata updates by stable citation ID', () => {
  const old = [article('old', 'An older paper', 2022), article('new', 'Working title', 2025)];
  const rows = selectPublications(old, [article('new', 'Final title')], profile, config.scholar);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].title, 'Final title');
  assert.equal(rows[1].title, 'An older paper');
});

test('first run baselines existing GitHub repos; subsequent additions render and repeat runs are stable', async () => {
  let repositories = [repo(1, 'old')];
  const fetchImpl = async url => response(url.startsWith('https://api.github.com') ? repositories : html);
  const baseline = await synchronize({ previous: emptyState(), profile, config, now, fetchImpl });
  assert.deepEqual(baseline.github_baseline_ids, [1]);
  assert.equal(baseline.projects.length, 0);
  repositories = [...repositories, repo(2, 'new')];
  const next = await synchronize({ previous: baseline, profile, config, now, fetchImpl });
  assert.equal(next.projects[0].name, 'new');
  assert.equal(next.publications.length, 0);
  assert.deepEqual(await synchronize({ previous: next, profile, config, now, fetchImpl }), next);
  repositories = [repo(1, 'old')];
  assert.equal((await synchronize({ previous: next, profile, config, now, fetchImpl })).projects.length, 0);
});

test('Scholar first run is a baseline, later citations are added without importing older records', async () => {
  let body = html;
  const fetchImpl = async url => response(url.startsWith('https://api.github.com') ? [] : body);
  const baseline = await synchronize({ previous: emptyState(), profile, config, now, fetchImpl });
  assert.deepEqual(baseline.scholar_baseline_ids, ['7VOBHhMAAAAJ:abc-123']);
  assert.equal(baseline.publications.length, 0);
  body = html.replace('abc-123', 'fresh').replace('Neural &amp; visual representations', 'New neural representations');
  const next = await synchronize({ previous: baseline, profile, config, now, fetchImpl });
  assert.equal(next.publications[0].source_id, '7VOBHhMAAAAJ:fresh');
  assert.equal(next.publications.length, 1);
});

test('a Scholar outage preserves cached papers and allows GitHub updates', async () => {
  const previous = { ...emptyState(), github_baseline_ids: [1], publications: [article('old', 'Keep this publication')] };
  const result = await synchronize({ previous, profile, config, now, fetchImpl: async url => url.startsWith('https://api.github.com') ? response([repo(2, 'new')]) : new Response('blocked', { status: 429 }) });
  assert.equal(result.sources.scholar.status, 'blocked');
  assert.equal(result.sources.github.status, 'ok');
  assert.deepEqual(result.publications, previous.publications);
  assert.equal(result.projects[0].name, 'new');
});

test('partial GitHub pagination failure preserves all cached projects and does not seed a baseline', async () => {
  let calls = 0;
  const previous = { ...emptyState(), projects: [{ name: 'kept' }] };
  const result = await synchronize({ previous, profile, config, now, fetchImpl: async url => {
    if (!url.startsWith('https://api.github.com')) return response(html);
    calls++;
    return calls === 1 ? response(Array.from({ length: 100 }, (_, i) => repo(i, `repo${i}`))) : new Response('rate limited', { status: 403 });
  } });
  assert.equal(result.sources.github.status, 'blocked');
  assert.equal(result.github_baseline_ids, null);
  assert.deepEqual(result.projects, previous.projects);
});
