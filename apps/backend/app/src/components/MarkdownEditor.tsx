import { useEffect, useRef } from 'react';
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

export function MarkdownEditor({ value, onChange, disabled, placeholder, minHeight = '8rem', showSourceToggle = false }: Props) {
  const editorRef = useRef<MDXEditorMethods>(null);

  // Sync EXTERNAL value changes (async load, programmatic reset) into the
  // editor via its imperative API — without remounting. Typing never triggers
  // this branch because `value` then equals what the editor just emitted, so
  // the comparison short-circuits. (Previously a `key` toggled on the empty→
  // non-empty transition, remounting the editor on the first keystroke and
  // stealing focus.)
  useEffect(() => {
    if (editorRef.current && value !== editorRef.current.getMarkdown()) {
      editorRef.current.setMarkdown(value);
    }
  }, [value]);

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
        markdown={value}
        onChange={onChange}
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
