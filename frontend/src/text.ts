const dotBelowMap: Record<string, string> = {
  e: 'ẹ',
  E: 'Ẹ',
  o: 'ọ',
  O: 'Ọ',
  s: 'ṣ',
  S: 'Ṣ',
};

export function applyCombiningMark(value: string, mark: string): string {
  if (!value) return value;
  return `${value}${mark}`.normalize('NFC');
}

export function applyDotBelow(value: string): string {
  if (!value) return value;
  const chars = Array.from(value);
  for (let index = chars.length - 1; index >= 0; index -= 1) {
    const replacement = dotBelowMap[chars[index]];
    if (replacement) {
      chars[index] = replacement;
      return chars.join('');
    }
  }
  return value;
}
