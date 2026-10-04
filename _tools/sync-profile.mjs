/** Fetch public profile metadata. Never execute repository/Scholar content. */
import { load } from 'cheerio';
import { readFile, writeFile, rename, appendFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const PAGE_SIZE = 100;
const MAX_PAGES = 10;
const clean = (value, limit = 2000) => String(value ?? '').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, limit);
export const titleKey = value => clean(value).normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
const repoKey = value => String(value).toLowerCase().replace(/\/$/, '');
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export function emptyState() {
  return { version: 1, github_baseline_ids: null, scholar_baseline_ids: null, projects: [], publications: [], sources: {} };
}

class SourceError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

async function request(url, { fetchImpl = fetch, headers = {}, json = true } = {}) {
  let response;
  try {
    response = await fetchImpl(url, {
      headers: { 'User-Agent': 'utoprey-profile-sync/1.0 (+https://utoprey.github.io/)', ...headers },
      signal: AbortSignal.timeout(25000),
      redirect: 'error',
    });
  } catch {
    // Do not log a request URL: third-party API URLs can contain credentials.
    throw new SourceError('error', 'Network request failed or timed out.');
  }
  if (!response.ok) {
    throw new SourceError([403, 429].includes(response.status) ? 'blocked' : 'error', `Source returned HTTP ${response.status}.`);
  }
  const body = await response.text();
  if (body.length > 4_000_000) throw new SourceError('error', 'Source response is unexpectedly large.');
  if (!json) return body;
  try { return JSON.parse(body); }
  catch { throw new SourceError('error', 'Source did not return valid JSON.'); }
}

export async function fetchRepositories(config, options = {}) {
  const records = [];
  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = `https://api.github.com/users/${encodeURIComponent(config.username)}/repos?type=owner&sort=full_name&per_page=${PAGE_SIZE}&page=${page}`;
    const rows = await request(url, { ...options, headers: {
      Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
      ...(options.githubToken ? { Authorization: `Bearer ${options.githubToken}` } : {}),
    } });
    if (!Array.isArray(rows) || rows.some(row => !Number.isSafeInteger(row.id) || !row.name || !row.owner?.login)) {
      throw new SourceError('error', 'GitHub response has an unexpected format.');
    }
    records.push(...rows);
    if (rows.length < PAGE_SIZE) return records;
  }
  throw new SourceError('error', 'GitHub pagination limit reached; previous snapshot retained.');
}

function verifyScholarName(name, config) {
  if (!config.profile_names.some(expected => titleKey(name) === titleKey(expected))) {
    throw new SourceError('error', 'Scholar profile identity did not match the configured author.');
  }
}

function scholarRecord(row, config) {
  const citationId = clean(row.citation_id, 160);
  if (!citationId.startsWith(`${config.author_id}:`) || !/^[\w-]+:[\w-]+$/.test(citationId) || !clean(row.title)) {
    throw new SourceError('error', 'Scholar article is missing a valid title or author citation ID.');
  }
  const yearText = clean(row.year);
  const year = /^\d{4}$/.test(yearText) && Number(yearText) >= 1900 && Number(yearText) <= 2200 ? Number(yearText) : null;
  return {
    id: `scholar-${citationId.split(':')[1]}`, source_id: citationId,
    title: clean(row.title, 1000), authors: clean(row.authors),
    venue: clean(row.publication), year,
    url: `https://scholar.google.com/citations?view_op=view_citation&user=${config.author_id}&citation_for_view=${encodeURIComponent(citationId)}`,
  };
}

export function parseScholar(html, config) {
  const $ = load(html);
  const name = $('#gsc_prf_in').text().trim();
  if (!name || /unusual traffic|not a robot|automated queries/i.test($('body').text())) {
    throw new SourceError('blocked', 'Scholar did not provide a public profile. Add SERPAPI_KEY to GitHub Actions secrets for the API provider.');
  }
  verifyScholarName(name, config);
  const rows = [];
  $('.gsc_a_tr').each((_, el) => {
    const title = $(el).find('.gsc_a_at');
    if (!title.length) return;
    let citationId;
    try { citationId = new URL(title.attr('href'), 'https://scholar.google.com').searchParams.get('citation_for_view'); }
    catch { throw new SourceError('error', 'Scholar citation link is malformed.'); }
    const lines = $(el).find('.gs_gray');
    rows.push(scholarRecord({ citation_id: citationId, title: title.text(), authors: lines.eq(0).text(), publication: lines.eq(1).text(), year: $(el).find('.gsc_a_y').text() }, config));
  });
  if (!rows.length) throw new SourceError('error', 'Scholar returned no readable articles; previous snapshot retained.');
  return rows;
}

export async function fetchScholar(config, options = {}) {
  if (!options.serpApiKey) {
    // robots.txt allows the public profile, but disallows cstart pagination.
    // Fetch only the latest page; retained history is never erased by this view.
    const url = `https://scholar.google.com/citations?user=${encodeURIComponent(config.author_id)}&hl=en&sortby=pubdate&pagesize=${PAGE_SIZE}`;
    return parseScholar(await request(url, { ...options, json: false }), config);
  }
  const rows = [];
  for (let page = 0; page < MAX_PAGES; page++) {
    const params = new URLSearchParams({ engine: 'google_scholar_author', author_id: config.author_id,
      hl: 'en', sort: 'pubdate', num: String(PAGE_SIZE), start: String(page * PAGE_SIZE), api_key: options.serpApiKey });
    const result = await request(`https://serpapi.com/search.json?${params}`, options);
    if (result.error || result.search_metadata?.status === 'Error' || !Array.isArray(result.articles)) {
      throw new SourceError('error', 'Scholar API provider returned an error. Check the API key and quota.');
    }
    if (page === 0) verifyScholarName(result.author?.name, config);
    rows.push(...result.articles.map(row => scholarRecord(row, config)));
    if (!result.serpapi_pagination?.next) {
      if (!rows.length) throw new SourceError('error', 'Scholar API returned no articles; previous snapshot retained.');
      return rows;
    }
  }
  throw new SourceError('error', 'Scholar API pagination limit reached; previous snapshot retained.');
}

function projectAllowed(row, profile, config) {
  const excluded = new Set(config.exclude_repositories.map(repoKey));
  const curatedUrls = new Set(profile.projects.map(row => repoKey(row.url)));
  const curatedNames = new Set(profile.projects.flatMap(row => [titleKey(row.title.en), titleKey(row.title.ru), titleKey(row.id)]));
  return !excluded.has(repoKey(row.name)) && !(row.tags ?? row.topics ?? []).some(topic => config.exclude_topics.includes(topic)) &&
    !curatedUrls.has(repoKey(`https://github.com/${config.username}/${row.name}`)) && !curatedNames.has(titleKey(row.name));
}

export function selectProjects(repositories, baselineIds, profile, config) {
  const baseline = new Set(baselineIds);
  const included = new Set(config.include_existing_repositories.map(repoKey));
  return repositories.filter(row =>
    row.owner.login.toLowerCase() === config.username.toLowerCase() && row.private === false && row.visibility === 'public' &&
    !row.fork && !row.archived && !row.disabled && row.size > 0 &&
    projectAllowed(row, profile, config) &&
    (!baseline.has(row.id) || included.has(repoKey(row.name))) &&
    Boolean(row.name)
  ).map(row => ({
    id: `github-${row.id}`, source_id: row.id, name: clean(row.name, 200),
    url: `https://github.com/${encodeURIComponent(config.username)}/${encodeURIComponent(row.name)}`,
    description: clean(row.description, 1500),
    created_at: /^\d{4}-\d{2}-\d{2}T/.test(row.created_at) ? row.created_at.slice(0, 10) : '',
    tags: [...new Set([row.language, ...(row.topics ?? [])].filter(Boolean).map(t => clean(t, 60)))].slice(0, 6),
  })).sort((a, b) => b.created_at.localeCompare(a.created_at) || a.id.localeCompare(b.id));
}

export function selectPublications(previous, incoming, profile, config) {
  const known = [...profile.publications, ...profile.posters].map(row => titleKey(row.title));
  const excludedIds = new Set(config.exclude_citation_ids);
  const excludedTitles = new Set(config.exclude_titles.map(titleKey));
  const excludedFragments = config.exclude_title_fragments.map(titleKey);
  const byId = new Map([...previous, ...incoming].map(row => [row.source_id, row]));
  const result = [];
  const seen = new Set();
  for (const row of byId.values()) {
    const key = titleKey(row.title);
    // Allow punctuation changes and title prefixes/suffixes without reviving a hidden paper.
    const matchesCurated = known.some(k => k === key || (Math.min(k.length, key.length) > 60 && (k.includes(key) || key.includes(k))));
    if (matchesCurated || excludedIds.has(row.source_id) || excludedTitles.has(key) || excludedFragments.some(k => key.includes(k)) || seen.has(key)) continue;
    result.push(row); seen.add(key);
  }
  return result.sort((a, b) => (b.year ?? 0) - (a.year ?? 0) || a.title.localeCompare(b.title, 'en'));
}

export async function synchronize({ previous, profile, config, now = new Date(), ...options }) {
  const next = structuredClone(previous);
  if (next.version !== 1) throw new Error('Unsupported auto-profile schema version.');
  const day = now.toISOString().slice(0, 10);
  const results = await Promise.allSettled([
    fetchRepositories(config.github, options), fetchScholar(config.scholar, options),
  ]);
  for (const [i, source] of ['github', 'scholar'].entries()) {
    const result = results[i];
    const oldStatus = previous.sources[source] ?? {};
    if (result.status === 'fulfilled') {
      next.sources[source] = { status: 'ok', checked_at: day, last_success: day, records: result.value.length,
        provider: source === 'github' ? 'github-api' : options.serpApiKey ? 'serpapi' : 'public-profile' };
    } else {
      next.sources[source] = { ...oldStatus, status: result.reason.code ?? 'error', checked_at: day,
        message: result.reason instanceof SourceError ? result.reason.message : 'Unexpected source error; previous snapshot retained.' };
    }
  }
  if (results[0].status === 'fulfilled') {
    const repos = results[0].value;
    if (next.github_baseline_ids === null) next.github_baseline_ids = repos.map(row => row.id).sort((a, b) => a - b);
    next.projects = selectProjects(repos, next.github_baseline_ids, profile, config.github);
  }
  next.projects = next.projects.filter(row => projectAllowed(row, profile, config.github));
  let incoming = [];
  if (results[1].status === 'fulfilled') {
    const articles = results[1].value;
    if (next.scholar_baseline_ids == null) next.scholar_baseline_ids = articles.map(row => row.source_id).sort();
    const baseline = new Set(next.scholar_baseline_ids);
    const included = new Set(config.scholar.include_existing_citation_ids ?? []);
    incoming = articles.filter(row => !baseline.has(row.source_id) || included.has(row.source_id));
  }
  // Even during outages, apply newly added editorial exclusions to cached publications.
  next.publications = selectPublications(previous.publications, incoming, profile, config.scholar);
  if (!same(previous.projects, next.projects) || !same(previous.publications, next.publications)) next.content_updated = day;
  return next;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.some(arg => arg !== '--dry-run')) throw new Error('Usage: node _tools/sync-profile.mjs [--dry-run]');
  const readJson = async path => JSON.parse(await readFile(resolve(ROOT, path), 'utf8'));
  const profile = await readJson('_data/profile.json');
  const config = await readJson('_data/sync-config.json');
  let previous;
  try { previous = await readJson('_data/auto-profile.json'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; previous = emptyState(); }
  const next = await synchronize({ previous, profile, config, githubToken: process.env.GITHUB_TOKEN, serpApiKey: process.env.SERPAPI_KEY });
  const summary = ['Profile synchronization', ...Object.entries(next.sources).map(([name, s]) => `${name}: ${s.status}; ${s.records ?? 0} source records${s.message ? '; ' + s.message : ''}`),
    `Automatic entries: ${next.projects.length} GitHub projects, ${next.publications.length} Scholar records.`];
  console.log(summary.join('\n'));
  if (process.env.GITHUB_STEP_SUMMARY) await appendFile(process.env.GITHUB_STEP_SUMMARY, summary.map(s => s + '\n').join('\n'));
  for (const [name, status] of Object.entries(next.sources)) {
    if (status.status !== 'ok' && process.env.GITHUB_ACTIONS) console.log(`::warning title=${name} sync::${status.message}`);
  }
  if (!args.includes('--dry-run') && !same(previous, next)) {
    const path = resolve(ROOT, '_data/auto-profile.json');
    await writeFile(path + '.tmp', JSON.stringify(next, null, 2) + '\n');
    await rename(path + '.tmp', path);
  }
  if (Object.values(next.sources).every(s => s.status !== 'ok')) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(() => { console.error('Profile synchronization failed. No credentials or source response bodies are logged.'); process.exitCode = 1; });
}
