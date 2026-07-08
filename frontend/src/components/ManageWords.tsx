import { Plus, Sparkles } from 'lucide-react';
import { KeyboardEvent, useEffect, useState } from 'react';
import { createCustomEntry, validateCustomWord } from '../api';
import { applyCombiningMark, applyDotBelow } from '../text';
import type { KeyboardResponse, WordValidationResponse } from '../types';
import { YorubaKeyboard } from './YorubaKeyboard';

type Props = {
  keyboard: KeyboardResponse | null;
};

export const tokenStorageKey = 'yoruba-admin-token';

export function ManageWords({ keyboard }: Props) {
  const [token, setToken] = useState(() => sessionStorage.getItem(tokenStorageKey) ?? '');
  const [word, setWord] = useState('');
  const [tonePattern, setTonePattern] = useState('');
  const [partOfSpeech, setPartOfSpeech] = useState('');
  const [meaning, setMeaning] = useState('');
  const [exampleText, setExampleText] = useState('');
  const [exampleEnglish, setExampleEnglish] = useState('');
  const [allowOverride, setAllowOverride] = useState(false);
  const [validation, setValidation] = useState<WordValidationResponse | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (token) sessionStorage.setItem(tokenStorageKey, token);
    else sessionStorage.removeItem(tokenStorageKey);
  }, [token]);

  async function runValidation(nextWord = word) {
    const trimmed = nextWord.trim();
    setValidation(null);
    if (!trimmed || !token) return;
    try {
      setValidation(await validateCustomWord(trimmed, token));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not validate word');
    }
  }

  async function saveEntry() {
    if (!token) {
      setError('Enter the admin token first.');
      return;
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await createCustomEntry(
        {
          word: word.trim(),
          tone_pattern: tonePattern.trim() || null,
          part_of_speech: partOfSpeech.trim() || null,
          meaning: meaning.trim(),
          example_text: exampleText.trim() || null,
          example_english: exampleEnglish.trim() || null,
          allow_override: allowOverride,
        },
        token,
      );
      setWord('');
      setTonePattern('');
      setPartOfSpeech('');
      setMeaning('');
      setExampleText('');
      setExampleEnglish('');
      setAllowOverride(false);
      setValidation(null);
      setStatus('Custom word added with the applied tone pattern. Open Custom Entries to view or delete it.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add custom word');
    } finally {
      setBusy(false);
    }
  }

  function handleAction(action: string) {
    if (action === 'backspace') setWord((value) => Array.from(value).slice(0, -1).join(''));
    if (action === 'space') setWord((value) => `${value} `);
    if (action === 'nasalN') setWord((value) => `${value}n`);
    if (action === 'dotBelow') setWord((value) => applyDotBelow(value));
  }

  function onWordKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    void runValidation();
  }

  const needsOverride = validation && validation.is_valid_yoruba && !validation.can_save_without_override;
  const appliedTonePreview = tonePattern.trim() || validation?.tone_label || 'mid-high';

  return (
    <section className="manage-layout">
      <div className="manage-panel add-panel">
        <h2>Add custom word</h2>
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

        <label>
          Yoruba word
          <input
            value={word}
            onChange={(event) => setWord(event.target.value)}
            onBlur={() => void runValidation()}
            onKeyDown={onWordKeyDown}
            placeholder="ọ́rẹ́"
          />
        </label>

        <YorubaKeyboard
          keyboard={keyboard}
          onInsert={(value) => setWord((current) => `${current}${value}`)}
          onTone={(mark) => setWord((current) => applyCombiningMark(current, mark))}
          onAction={handleAction}
        />

        {validation ? (
          <div className={validation.warning ? 'validation-box warning' : 'validation-box'}>
            <strong>{validation.word}</strong>
            <span>normalized as {validation.normalized_form}</span>
            <span>detected tone: {validation.tone_label}</span>
            <span>applied tone: {appliedTonePreview}</span>
            <span>related dictionary entries: {validation.related_dictionary_entries}</span>
            {validation.warning ? <p>{validation.warning}</p> : null}
          </div>
        ) : null}

        {needsOverride ? (
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={allowOverride}
              onChange={(event) => setAllowOverride(event.target.checked)}
            />
            Save with admin override
          </label>
        ) : null}

        <label>
          Tone pattern to apply
          <input
            value={tonePattern}
            onChange={(event) => setTonePattern(event.target.value)}
            placeholder={validation?.tone_label ?? 'mid-high'}
          />
        </label>

        <label>
          Part of speech
          <input value={partOfSpeech} onChange={(event) => setPartOfSpeech(event.target.value)} placeholder="noun" />
        </label>

        <label>
          Meaning
          <textarea value={meaning} onChange={(event) => setMeaning(event.target.value)} placeholder="Meaning in English" />
        </label>

        <label>
          Yoruba example
          <input value={exampleText} onChange={(event) => setExampleText(event.target.value)} placeholder="Optional" />
        </label>

        <label>
          English example
          <input value={exampleEnglish} onChange={(event) => setExampleEnglish(event.target.value)} placeholder="Optional" />
        </label>

        <button className="primary-action" type="button" disabled={busy} onClick={() => void saveEntry()}>
          <Plus size={18} />
          Add word with tone
        </button>

        {status ? <p className="success">{status}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </div>

      <aside className="manage-visual" aria-hidden="true">
        <div className="tone-orbit">
          <span>à</span>
          <span>ā</span>
          <span>á</span>
          <span>ẹ</span>
          <span>ọ</span>
          <span>ṣ</span>
        </div>
        <div className="tone-card">
          <Sparkles size={20} />
          <strong>detected tone stays visible</strong>
          <p>{appliedTonePreview}</p>
        </div>
      </aside>
    </section>
  );
}
