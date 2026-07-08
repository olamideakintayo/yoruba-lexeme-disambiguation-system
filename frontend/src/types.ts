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

export type CustomEntry = {
  id: string;
  word: string;
  normalized_form: string;
  tone_pattern: string;
  tone_label: string;
  meaning: string;
  part_of_speech?: string | null;
  examples: Array<Record<string, string>>;
};

export type CustomEntryInput = {
  word: string;
  meaning: string;
  tone_pattern?: string | null;
  part_of_speech?: string | null;
  example_text?: string | null;
  example_english?: string | null;
  allow_override: boolean;
};

export type WordValidationResponse = {
  word: string;
  normalized_form: string;
  tone_pattern: string;
  tone_label: string;
  is_valid_yoruba: boolean;
  related_dictionary_entries: number;
  can_save_without_override: boolean;
  warning?: string | null;
};
