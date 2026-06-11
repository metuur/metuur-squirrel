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
          // Vault content is user-authored but still must not smuggle
          // javascript:/data: URLs into a live anchor. Anything that is not
          // an absolute http(s)/mailto URL renders as plain text.
          let safe = false;
          try {
            safe = ['http:', 'https:', 'mailto:'].includes(new URL(target).protocol);
          } catch {
            // relative or malformed — not a resolvable web link here
          }
          if (!safe) {
            return <span>{children}</span>;
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
