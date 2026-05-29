import {
  MDXEditor,
  headingsPlugin,
  listsPlugin,
  quotePlugin,
  thematicBreakPlugin,
  markdownShortcutPlugin,
  toolbarPlugin,
  BoldItalicUnderlineToggles,
  UndoRedo,
  BlockTypeSelect,
  Separator,
} from '@mdxeditor/editor';
import '@mdxeditor/editor/style.css';

interface Props {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  placeholder?: string;
  minHeight?: string;
}

export function MarkdownEditor({ value, onChange, disabled, placeholder, minHeight = '8rem' }: Props) {
  return (
    <div
      className="border border-slate-300 dark:border-slate-600 rounded-md overflow-hidden bg-white dark:bg-slate-800"
      style={{ '--mdxeditor-min-height': minHeight } as React.CSSProperties}
    >
      <MDXEditor
        key={value === '' ? 'empty' : undefined}
        markdown={value}
        onChange={onChange}
        readOnly={disabled}
        placeholder={placeholder}
        contentEditableClassName="prose prose-sm dark:prose-invert max-w-none px-3 py-2 outline-none min-h-[var(--mdxeditor-min-height,8rem)]"
        plugins={[
          headingsPlugin(),
          listsPlugin(),
          quotePlugin(),
          thematicBreakPlugin(),
          markdownShortcutPlugin(),
          toolbarPlugin({
            toolbarContents: () => (
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
