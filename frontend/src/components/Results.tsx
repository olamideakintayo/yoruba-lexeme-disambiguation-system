import { BookOpen } from 'lucide-react';
import type { SearchResult } from '../types';

type Props = {
  results: SearchResult[];
  query: string;
  loading: boolean;
  error?: string | null;
};

export function Results({ results, query, loading, error }: Props) {
  if (loading) {
    return <section className="results-state">Searching Yoruba words...</section>;
  }

  if (error) {
    return <section className="results-state results-error">{error}</section>;
  }

  if (!query) {
    return <section className="results-state">Enter a Yoruba word to see its tonal meanings.</section>;
  }

  if (results.length === 0) {
    return <section className="results-state">No Yoruba dictionary entry found for this spelling.</section>;
  }

  return (
    <section className="results-list" aria-label="Search results">
      {results.map((result) => {
        const meanings = result.meanings?.length ? result.meanings : result.meaning ? [result.meaning] : [];
        const examples = result.examples ?? [];

        return (
          <article className="result-card" key={result.word}>
            <div className="result-heading">
              <div>
                <h2>{result.word}</h2>
                <p>normalized as {result.normalized_form}</p>
              </div>
              <BookOpen aria-hidden="true" />
            </div>

            <dl className="variant-details">
              <div>
                <dt>Tone</dt>
                <dd>{result.tone_label}</dd>
              </div>
              {result.part_of_speech ? (
                <div>
                  <dt>Part of speech</dt>
                  <dd>{result.part_of_speech}</dd>
                </div>
              ) : null}
              <div>
                <dt>Meaning</dt>
                <dd>
                  <ul className="meaning-list">
                    {meanings.map((meaning) => (
                      <li key={meaning}>{meaning}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            </dl>

            {examples.length > 0 ? (
              <div className="examples">
                {examples.map((example, index) => (
                  <blockquote key={`${result.word}-${index}`}>
                    {example.text}
                    {example.english ? <cite>{example.english}</cite> : null}
                  </blockquote>
                ))}
              </div>
            ) : null}

            {result.source ? <p className="source-label">{result.source}</p> : null}
          </article>
        );
      })}
    </section>
  );
}
