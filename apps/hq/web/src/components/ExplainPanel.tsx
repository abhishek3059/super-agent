import { useId, useState } from 'react';
import { MAX_SKETCH_TEXT, sketchPoints } from '../lib/sketch';

export function ExplainPanel({ reply, onClose }: { reply: string; onClose: () => void }) {
  const id = useId();
  const [source, setSource] = useState('');
  const [points, setPoints] = useState<string[]>([]);

  return (
    <section className="sketch" aria-labelledby={id}>
      <div className="sketch__header">
        <h2 id={id}>Explain</h2>
        <button type="button" onClick={onClose}>Back to conversation</button>
      </div>
      <p>Turn the first five points of a reply or excerpt into a sketch. The text stays in this tab.</p>
      <form onSubmit={(event) => { event.preventDefault(); setPoints(sketchPoints(source)); }}>
        <label htmlFor={id + '-source'}>Text to sketch</label>
        <textarea id={id + '-source'} value={source} maxLength={MAX_SKETCH_TEXT} rows={4}
          onChange={(event) => { setSource(event.target.value); setPoints([]); }} />
        <div className="sketch__actions">
          <button type="button" disabled={!reply} onClick={() => { setSource(reply.slice(0, MAX_SKETCH_TEXT)); setPoints(sketchPoints(reply)); }}>
            Sketch latest reply
          </button>
          <button type="submit" disabled={!source.trim()}>Make sketch</button>
        </div>
      </form>
      {!!points.length && (
        <ol className="sketch__steps" aria-label="Sketch">
          {points.map((point, index) => <li key={index}>{point}</li>)}
        </ol>
      )}
    </section>
  );
}
