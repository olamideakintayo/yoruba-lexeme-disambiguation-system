import { Search } from 'lucide-react';
import { KeyboardEvent, useEffect, useMemo, useState } from 'react';
import { getKeyboard, searchLexemes } from './api';
import { CustomEntries } from './components/CustomEntries';
import { ManageWords } from './components/ManageWords';
import { Results } from './components/Results';
import { Scene } from './components/Scene';
import { YorubaKeyboard } from './components/YorubaKeyboard';
import { applyCombiningMark, applyDotBelow } from './text';
import type { KeyboardResponse, SearchResponse } from './types';

function App() {
  const [view, setView] = useState<'search' | 'manage' | 'custom'>('search');
  const [query, setQuery] = useState('');
  const [keyboard, setKeyboard] = useState<KeyboardResponse | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    getKeyboard().then(setKeyboard).catch(() => setKeyboard(null));
  }, []);

  useEffect(() => {
    function stopUnexpectedSubmit(event: SubmitEvent) {
      event.preventDefault();
      event.stopPropagation();
    }

    window.addEventListener('submit', stopUnexpectedSubmit, true);
    return () => window.removeEventListener('submit', stopUnexpectedSubmit, true);
  }, []);

  const suggestions = useMemo(() => response?.suggestions ?? [], [response]);

  async function runSearch(nextQuery: string) {
    const trimmed = nextQuery.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchLexemes(trimmed);
      setResponse(data);
      setRecent((items) => [trimmed, ...items.filter((item) => item !== trimmed)].slice(0, 6));
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    void runSearch(query);
  }

  function handleAction(action: string) {
    if (action === 'backspace') setQuery((value) => Array.from(value).slice(0, -1).join(''));
    if (action === 'space') setQuery((value) => `${value} `);
    if (action === 'nasalN') setQuery((value) => `${value}n`);
    if (action === 'dotBelow') setQuery((value) => applyDotBelow(value));
  }

  return (
    <main>
      <Scene />
      <section className="app-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Yoruba Lexeme Disambiguation</p>
            <h1>Search Yoruba words, tones, and meanings</h1>
          </div>
          <span className="status">PostgreSQL · FastAPI · React</span>
        </header>

        <nav className="menu-bar" aria-label="Primary">
          <button className={view === 'search' ? 'active' : ''} type="button" onClick={() => setView('search')}>
            Search
          </button>
          <button className={view === 'manage' ? 'active' : ''} type="button" onClick={() => setView('manage')}>
            Add Word
          </button>
          <button className={view === 'custom' ? 'active' : ''} type="button" onClick={() => setView('custom')}>
            Custom Entries
          </button>
        </nav>

        {view === 'search' ? (
          <section className="workspace">
            <div className="search-panel">
              <div className="search-form">
                <label htmlFor="search">Yoruba word</label>
                <div className="search-row">
                  <input
                    id="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    onKeyDown={onSearchKeyDown}
                    placeholder="owo, owó, ọwọ, àpá..."
                    autoComplete="off"
                  />
                  <button type="button" aria-label="Search" onClick={() => void runSearch(query)}>
                    <Search size={20} />
                  </button>
                </div>
              </div>

              <YorubaKeyboard
                keyboard={keyboard}
                onInsert={(value) => setQuery((current) => `${current}${value}`)}
                onTone={(mark) => setQuery((current) => applyCombiningMark(current, mark))}
                onAction={handleAction}
              />

              <div className="quick-lists">
                <div>
                  <h2>Suggestions</h2>
                  <div className="chips">
                    {suggestions.map((item) => (
                      <button type="button" key={item} onClick={() => void runSearch(item)}>
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <h2>Recent</h2>
                  <div className="chips">
                    {recent.map((item) => (
                      <button type="button" key={item} onClick={() => void runSearch(item)}>
                        {item}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {error ? <p className="error">{error}</p> : null}
            </div>

            <Results results={response?.results ?? []} query={response?.query ?? query} loading={loading} error={error} />
          </section>
        ) : view === 'manage' ? (
          <ManageWords keyboard={keyboard} />
        ) : (
          <CustomEntries />
        )}
      </section>
    </main>
  );
}

export default App;
