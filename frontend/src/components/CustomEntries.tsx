import { RefreshCw, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { deleteCustomEntry, getCustomEntries } from '../api';
import type { CustomEntry } from '../types';
import { tokenStorageKey } from './ManageWords';

export function CustomEntries() {
  const [token, setToken] = useState(() => sessionStorage.getItem(tokenStorageKey) ?? '');
  const [entries, setEntries] = useState<CustomEntry[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) sessionStorage.setItem(tokenStorageKey, token);
    else sessionStorage.removeItem(tokenStorageKey);
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void loadEntries();
  }, [token]);

  async function loadEntries() {
    if (!token) {
      setError('Enter the admin token first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setEntries(await getCustomEntries(token));
    } catch (err) {
      setEntries([]);
      setError(err instanceof Error ? err.message : 'Could not load custom entries');
    } finally {
      setLoading(false);
    }
  }

  async function removeEntry(entry: CustomEntry) {
    setError(null);
    setStatus(null);
    try {
      await deleteCustomEntry(entry.id, token);
      setStatus(`${entry.word} deleted.`);
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete custom word');
    }
  }

  return (
    <section className="custom-page">
      <div className="manage-panel">
        <div className="list-heading">
          <div>
            <h2>Custom entries</h2>
            <p className="muted">Added words live here and can be deleted without touching the dictionary.</p>
          </div>
          <button type="button" onClick={() => void loadEntries()}>
            <RefreshCw size={17} />
            Refresh
          </button>
        </div>

        <label>
          Admin token
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            type="password"
            autoComplete="off"
            placeholder="Shared admin token"
          />
        </label>

        {loading ? <p className="muted">Loading custom entries...</p> : null}
        {status ? <p className="success">{status}</p> : null}
        {error ? <p className="error">{error}</p> : null}

        {entries.length === 0 && !loading ? (
          <p className="muted">No custom entries loaded.</p>
        ) : (
          <div className="custom-entry-list">
            {entries.map((entry) => (
              <article className="custom-entry" key={entry.id}>
                <div>
                  <h3>{entry.word}</h3>
                  <p>
                    {entry.tone_label} · {entry.normalized_form}
                    {entry.part_of_speech ? ` · ${entry.part_of_speech}` : ''}
                  </p>
                  <p>{entry.meaning}</p>
                </div>
                <button type="button" aria-label={`Delete ${entry.word}`} onClick={() => void removeEntry(entry)}>
                  <Trash2 size={18} />
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
