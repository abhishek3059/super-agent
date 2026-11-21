import { memo, useId } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { parseSketch } from '@shared/sketch';
import type { MessageBody } from '@shared/types';

const components: Components = {
  a: ({ node: _n, ...props }) => <a {...props} target="_blank" rel="noreferrer noopener" />,
  table: ({ node: _n, ...props }) => (
    <div className="md-table"><table {...props} /></div>
  ),
};

/** Assistant message markdown: paragraphs, lists, blockquotes, inline code, code blocks (screen 02), tables. */
export const Markdown = memo(function Markdown({ text, streaming, format }: Pick<MessageBody, 'text' | 'streaming' | 'format'>) {
  const titleId = useId();
  const sketch = format === 'sketch' && !streaming && parseSketch(text);
  if (sketch) {
    return (
      <section className="sketch" aria-labelledby={titleId}>
        <h3 className="sketch__title" id={titleId}>{sketch.title}</h3>
        <ol className="sketch__steps">
          {sketch.steps.map(({ heading, detail }, index) => (
            <li key={index} className="sketch__step">
              <h4 className="sketch__heading">{heading}</h4>
              <p className="sketch__detail">{detail}</p>
            </li>
          ))}
        </ol>
      </section>
    );
  }
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{text}</ReactMarkdown>
    </div>
  );
});
