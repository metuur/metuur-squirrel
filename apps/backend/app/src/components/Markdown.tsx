import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link } from 'react-router-dom';
import type { ComponentProps } from 'react';

type Props = { children: string };

export function Markdown({ children }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children, ...rest }: ComponentProps<'a'>) => {
          const target = href ?? '';
          const isInternal = target.startsWith('/') || target.startsWith('#');
          if (isInternal) {
            return <Link to={target}>{children}</Link>;
          }
          return (
            <a href={target} target="_blank" rel="noreferrer" {...rest}>
              {children}
            </a>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
