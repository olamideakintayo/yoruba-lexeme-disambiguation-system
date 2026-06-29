import { describe, expect, it } from 'vitest';
import { applyCombiningMark, applyDotBelow } from './text';

describe('Yoruba text helpers', () => {
  it('applies tone marks to the current value', () => {
    expect(applyCombiningMark('owo', '\u0301')).toBe('owó');
  });

  it('applies dot below to the nearest supported character', () => {
    expect(applyDotBelow('owo')).toBe('ow\u1ecd');
    expect(applyDotBelow('ase')).toBe('asẹ');
  });
});
