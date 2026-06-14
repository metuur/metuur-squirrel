import { useEffect, useRef, useState } from 'react';
import {
  MDXEditor,
  type MDXEditorMethods,
  headingsPlugin,
  listsPlugin,
  quotePlugin,
  thematicBreakPlugin,
  markdownShortcutPlugin,
  diffSourcePlugin,
  toolbarPlugin,
  BoldItalicUnderlineToggles,
  UndoRedo,
  BlockTypeSelect,
  DiffSourceToggleWrapper,
  Separator,
} from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css';

interface Props {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  placeholder?: string;
  minHeight?: string;
  showSourceToggle?: boolean;
}

// MDXEditor parses the body as MDX, so a literal tag-like placeholder (e.g. the
// template's `[[<OTHER-TAG>]]`, autolinks, `<!-- … -->`) is read as JSX and the
// rich view silently drops to raw source. We escape the `<` that STARTS a tag so
// MDX renders it as literal text instead. Only `<` is touched — blockquote `>`
// and prose are left alone. The backslash form matches what MDXEditor emits when
// it serializes a literal `<`, so load↔save round-trips cleanly.
function escapeForEditor(md: string): string {
  return md.replace(/<(?=[A-Za-z/!?])/g, '\\<');
}
// Reverse it on the way out, accepting either escaping MDXEditor might produce
// (backslash or HTML entity) so the saved file restores the original `<…>`.
function unescapeFromEditor(md: string): string {
  return md.replace(/\\([<>])/g, '$1').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
}

export function MarkdownEditor({ value, onChange, disabled, placeholder, minHeight = '8rem', showSourceToggle = false }: Props) {
  const editorRef = useRef<MDXEditorMethods>(null);
  // The rich editor parses content as MDX, so a literal angle-bracket
  // placeholder in the body (e.g. the template's `[[<OTHER-TAG>]]`) is read as
  // an unclosed JSX tag and the whole editor errors out — blocking edits AND
  // the surrounding Save. When that happens we drop to a plain-text editor so
  // the note (and any deadline above it) stays fully editable and saveable.
  const [rawFallback, setRawFallback] = useState(false);

  // Sync EXTERNAL value changes (async load, programmatic reset) into the
  // editor via its imperative API — without remounting. Typing never triggers
  // this branch because `value` then equals what the editor just emitted, so
  // the comparison short-circuits. (Previously a `key` toggled on the empty→
  // non-empty transition, remounting the editor on the first keystroke and
  // stealing focus.) No-op in fallback mode, where editorRef is null.
  useEffect(() => {
    // Compare the UNESCAPED editor content against `value` (which is already in
    // unescaped form): after a keystroke they're equal, so this never re-pushes
    // and steals the cursor; it only fires for genuine external value changes.
    if (editorRef.current && value !== unescapeFromEditor(editorRef.current.getMarkdown())) {
      editorRef.current.setMarkdown(escapeForEditor(value));
    }
  }, [value]);

  if (rawFallback) {
    return (
      <div
        className="border border-hairline rounded-md overflow-hidden bg-surface"
        style={{ '--mdxeditor-min-height': minHeight } as React.CSSProperties}
      >
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          spellCheck={false}
          className="w-full font-mono text-sm px-3 py-2 outline-none bg-surface text-ink resize-y min-h-[var(--mdxeditor-min-height,8rem)]"
        />
        <div className="px-3 py-1.5 text-[11px] text-ink-4 border-t border-hairline-2 bg-surface-2">
          Plain-text mode — this note contains markup the rich editor can't render (e.g. <code>&lt;PLACEHOLDER&gt;</code>).
        </div>
      </div>
    );
  }

  const basePlugins = [
    headingsPlugin(),
    listsPlugin(),
    quotePlugin(),
    thematicBreakPlugin(),
    markdownShortcutPlugin(),
  ];

  return (
    <div
      className="border border-hairline rounded-md overflow-hidden bg-surface"
      style={{ '--mdxeditor-min-height': minHeight } as React.CSSProperties}
    >
      <MDXEditor
        ref={editorRef}
        markdown={escapeForEditor(value)}
        onChange={(md) => onChange(unescapeFromEditor(md))}
        onError={() => setRawFallback(true)}
        readOnly={disabled}
        placeholder={placeholder}
        contentEditableClassName="prose prose-sm max-w-none px-3 py-2 outline-none min-h-[var(--mdxeditor-min-height,8rem)]"
        plugins={[
          ...basePlugins,
          ...(showSourceToggle ? [diffSourcePlugin({ viewMode: 'rich-text' })] : []),
          toolbarPlugin({
            toolbarContents: () =>
              showSourceToggle ? (
                <DiffSourceToggleWrapper>
                  <UndoRedo />
                  <Separator />
                  <BoldItalicUnderlineToggles />
                  <Separator />
                  <BlockTypeSelect />
                </DiffSourceToggleWrapper>
              ) : (
                <>
                  <UndoRedo />
                  <Separator />
                  <BoldItalicUnderlineToggles />
                  <Separator />
                  <BlockTypeSelect />
                </>
              ),
          }),
        ]}
      />
    </div>
  );
}
