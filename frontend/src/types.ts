export type Source = {
  name: string;
  url?: string | null;
  license?: string | null;
};

export type WordForm = {
  id: string;
  surface_form: string;
  normalized_form: string;
  tone_pattern: string;
  diacritics: Record<string, boolean>;
};

export type Sense = {
  id: string;
  part_of_speech?: string | null;
  definition: string;
  examples: Array<Record<string, string>>;
  domain?: string | null;
};

export type Lexeme = {
  id: string;
  canonical_form: string;
  normalized_form: string;
  language_code: string;
  source?: Source | null;
  word_forms: WordForm[];
  senses: Sense[];
};

export type SearchResult = {
  word: string;
  normalized_form: string;
  tone_pattern: string;
  tone_label: string;
  meaning: string;
  meanings: string[];
  part_of_speech?: string | null;
  examples: Array<Record<string, string>>;
  source?: string | null;
};

export type SearchResponse = {
  query: string;
  normalized_query: string;
  results: SearchResult[];
  suggestions: string[];
  error?: string | null;
};

export type KeyboardResponse = {
  alphabet: string[];
  tones: Array<{ label: string; mark: string; example: string }>;
  controls: Array<{ label: string; action: string }>;
};
