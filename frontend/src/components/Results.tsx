import { BookOpen, ExternalLink } from 'lucide-react';
import type { SearchResult } from '../types';

type Props = {
  results: SearchResult[];
  query: string;
  loading: boolean;
};

function uniqueBy<T>(items: T[], getKey: (item: T) => string): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = getKey(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function Results({ results, query, loading }: Props) {
  if (loading) {
    return <section className="results-state">Searching Yoruba forms...</section>;
  }

  if (!query) {
    return <section className="results-state">Enter a Yoruba word to see its tonal forms and meanings.</section>;
  }

  if (results.length === 0) {
    return <section className="results-state">No entries found yet. Try another spelling or import a larger dictionary.</section>;
  }

  return (
    <section className="results-list" aria-label="Search results">
      {results.map(({ lexeme, match_type }) => {
        const forms = uniqueBy(lexeme.word_forms, (form) => form.surface_form);

        return (
          <article className="result-card" key={lexeme.id}>
            <div className="result-heading">
              <div>
                <h2>{lexeme.canonical_form}</h2>
                <p>{match_type} match · normalized as {lexeme.normalized_form}</p>
              </div>
              <BookOpen aria-hidden="true" />
            </div>

            <div className="entry-row">
              <span>forms</span>
              <div className="forms">
                {forms.map((form) => (
                  <span className="form-pill" key={form.id}>
                    <strong>{form.surface_form}</strong>
                    <small>{form.tone_pattern}</small>
                  </span>
                ))}
              </div>
            </div>

            <div className="senses">
              {lexeme.senses.map((sense) => (
                <div className="sense" key={sense.id}>
                  <span>{sense.part_of_speech ?? 'word'}</span>
                  <p>{sense.definition}</p>
                  {sense.examples.map((example, index) => (
                    <blockquote key={`${sense.id}-${index}`}>
                      {example.text}
                      {example.english ? <cite>{example.english}</cite> : null}
                    </blockquote>
                  ))}
                </div>
              ))}
            </div>

            {lexeme.source ? (
              <a
                className="source-link"
                href={lexeme.source.url ?? '#'}
                target={lexeme.source.url ? '_blank' : undefined}
                rel="noreferrer"
              >
                {lexeme.source.name}
                {lexeme.source.url ? <ExternalLink size={14} /> : null}
              </a>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
