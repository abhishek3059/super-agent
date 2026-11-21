export const MAX_SKETCH_TEXT = 4000;
const sentences = typeof Intl.Segmenter === 'function' ? new Intl.Segmenter(undefined, { granularity: 'sentence' }) : null;

/** Extract the leading points verbatim. The caller displays the result only as text. */
export function sketchPoints(source: string): string[] {
  return source.slice(0, MAX_SKETCH_TEXT).split(/\r?\n/).flatMap((line) => {
    const cleaned = line.replace(/^\s*(?:(?:[-*•]|#{1,6}|\d+[.)])\s+)?/, '').trim();
    if (!cleaned) return [];
    return sentences ? Array.from(sentences.segment(cleaned), ({ segment }) => segment.trim()) : [cleaned];
  }).slice(0, 5);
}
