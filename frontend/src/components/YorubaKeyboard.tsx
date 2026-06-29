import { CornerDownLeft, Delete, Space } from 'lucide-react';
import type { KeyboardResponse } from '../types';

type Props = {
  keyboard: KeyboardResponse | null;
  onInsert: (value: string) => void;
  onTone: (mark: string) => void;
  onAction: (action: string) => void;
};

export function YorubaKeyboard({ keyboard, onInsert, onTone, onAction }: Props) {
  if (!keyboard) {
    return <div className="keyboard-placeholder">Loading keyboard...</div>;
  }

  return (
    <section className="keyboard" aria-label="Yoruba keyboard">
      <div className="key-grid alphabet-grid">
        {keyboard.alphabet.map((letter) => (
          <button className="key" type="button" key={letter} onClick={() => onInsert(letter)}>
            {letter}
          </button>
        ))}
      </div>
      <div className="key-grid tone-grid">
        {keyboard.tones.map((tone) => (
          <button className="key tone-key" type="button" key={tone.label} onClick={() => onTone(tone.mark)}>
            <span>{tone.example}</span>
            <small>{tone.label}</small>
          </button>
        ))}
        {keyboard.controls.map((control) => (
          <button className="key control-key" type="button" key={control.action} onClick={() => onAction(control.action)}>
            {control.action === 'backspace' && <Delete size={18} />}
            {control.action === 'space' && <Space size={18} />}
            {control.action === 'nasalN' && <CornerDownLeft size={18} />}
            {control.action === 'dotBelow' ? 'ẹ/ọ/ṣ' : <span>{control.label}</span>}
          </button>
        ))}
      </div>
    </section>
  );
}
