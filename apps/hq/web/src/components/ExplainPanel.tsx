import { useId, useState } from 'react';
import { MAX_SKETCH_TEXT, sketchPoints } from '../lib/sketch';

export function ExplainPanel({ reply, readSelection, onClose }: { reply: string; readSelection: () => string; onClose: () => void }) {
  const id = useId();
  const [source, setSource] = useState('');
  const [points, setPoints] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  const sketch = (text: string) => {
    setNotice('');
    setSource(text.slice(0, MAX_SKETCH_TEXT));
    setPoints(sketchPoints(text));
  };

  return (
    <section className="sketch" aria-labelledby={id}>
      <div className="sketch__header">
        <h2 id={id}>Explain</h2>
        <button type="button" onClick={onClose}>Back to conversation</button>
      </div>
      <p>Select text in the conversation, use the latest reply, or paste an excerpt. Sketches stay in this tab.</p>
      <form onSubmit={(event) => { event.preventDefault(); sketch(source); }}>
        <label htmlFor={id + '-source'}>Text to sketch</label>
        <textarea id={id + '-source'} value={source} maxLength={MAX_SKETCH_TEXT} rows={4}
          onChange={(event) => { setSource(event.target.value); setPoints([]); setNotice(''); }} />
        <div className="sketch__actions">
          <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => {
            const text = readSelection();
            if (text) sketch(text);
            else setNotice('Select some text in the conversation first.');
          }}>Sketch selection</button>
          <button type="button" disabled={!reply} onClick={() => sketch(reply)}>
            Sketch latest reply
          </button>
          <button type="submit" disabled={!source.trim()}>Make sketch</button>
        </div>
      </form>
      {notice && <p role="status">{notice}</p>}
      {!!points.length && (
        <ol className="sketch__steps" aria-label="Sketch">
          {points.map((point, index) => <li key={index}>{point}</li>)}
        </ol>
      )}
    </section>
  );
}
