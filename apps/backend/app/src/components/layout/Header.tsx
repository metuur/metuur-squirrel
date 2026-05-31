import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api, type SearchHit } from '@/api/client';
import { useMe } from '@/hooks/useMe';
import { useCapture } from '@/components/CaptureModal';

export type ViewMode = 'List' | 'Board';

interface HeaderProps {
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
}

export function Header({ viewMode, setViewMode, isDarkMode, toggleDarkMode }: HeaderProps) {
  const { data: me, mutate } = useMe();
  const navigate = useNavigate();
  const location = useLocation();
  const { open: openCapture } = useCapture();
  const showViewToggle = location.pathname === '/';
  const [q, setQ] = useState('');
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const inflight = useRef(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (!q.trim()) { setResults([]); setShowResults(false); return; }
    const id = ++inflight.current;
    setSearching(true);
    const t = window.setTimeout(async () => {
      try {
        const hits = await api.search(q.trim());
        if (id === inflight.current) { setResults(hits); setShowResults(true); }
      } catch {
        if (id === inflight.current) setResults([]);
      } finally {
        if (id === inflight.current) setSearching(false);
      }
    }, 200);
    return () => window.clearTimeout(t);
  }, [q]);

  async function switchWorkspace(name: string) {
    await api.setVault(name);
    await mutate();
    window.location.reload();
  }

  return (
    <div className="flex flex-col sticky top-0 z-20">
      <header className="h-14 border-b border-hairline bg-surface flex items-center px-6 gap-10">
        <div className="flex items-center gap-6 shrink-0">
          <Link
            to="/"
            className="flex items-center gap-2 font-bold text-ink hover:opacity-80 transition-opacity cursor-pointer"
          >
            <img src="/squirrel.svg" alt="" aria-hidden="true" className="w-8 h-8" />
            <span className="tracking-tight">Squirrel</span>
          </Link>

          <div className={`${showViewToggle ? 'hidden md:flex' : 'hidden'} bg-surface-2 p-0.5 rounded border border-hairline`}>
            <button
              onClick={() => setViewMode('List')}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                viewMode === 'List'
                  ? 'text-accent bg-surface shadow-sm'
                  : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('Board')}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                viewMode === 'Board'
                  ? 'text-accent bg-surface shadow-sm'
                  : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              Board
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-1">
          {me?.multi_vault && (
            <div className="relative">
              <select
                value={me.active_workspace.name}
                onChange={(e) => switchWorkspace(e.target.value)}
                className="appearance-none flex items-center gap-2 pl-9 pr-8 py-1.5 border border-hairline rounded bg-surface text-sm font-medium text-ink-2 cursor-pointer hover:border-ink-4 transition-all outline-none focus:ring-1 focus:ring-accent"
              >
                {me.workspaces.map((w) => (
                  <option key={w.name} value={w.name}>{w.name}</option>
                ))}
              </select>
              <span className="material-icons text-ink-4 text-lg absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none">folder_open</span>
              <span className="material-icons text-ink-4 text-lg absolute right-1 top-1/2 -translate-y-1/2 pointer-events-none">arrow_drop_down</span>
            </div>
          )}

          <div className="relative w-full max-w-sm group">
            <span className="material-icons absolute left-3 top-[7px] text-ink-4 text-lg pointer-events-none group-focus-within:text-accent transition-colors">search</span>
            <input
              ref={searchRef}
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onFocus={() => results.length && setShowResults(true)}
              onBlur={() => setTimeout(() => setShowResults(false), 150)}
              className="w-full pl-10 pr-10 py-1.5 text-sm border border-hairline rounded-md bg-surface text-ink focus:border-accent focus:ring-0 outline-none transition-all placeholder-ink-4"
              placeholder="Search notes... (Cmd+K)"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-hairline border-t-accent rounded-full animate-spin" />
            )}
            {showResults && results.length > 0 && (
              <div className="panel absolute top-full left-0 right-0 mt-1 max-h-80 overflow-auto z-50">
                {results.slice(0, 12).map((h) => (
                  <Link
                    key={h.id}
                    to={`/notes/${h.id}`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { setShowResults(false); setQ(''); }}
                    className="block border-b border-hairline-2 last:border-0 px-3 py-2 text-sm hover:bg-surface-2"
                  >
                    <div className="truncate font-medium text-ink">{h.title}</div>
                    {h.snippet_lines[0] && (
                      <div className="truncate text-xs text-ink-3">{h.snippet_lines[0]}</div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 ml-2">
            <button
              onClick={() => openCapture()}
              className="btn btn-primary text-sm font-semibold px-4 py-1.5 flex items-center gap-1"
            >
              <span className="material-icons text-lg">add</span>
              Add a note
            </button>

            <button
              onClick={toggleDarkMode}
              className="w-9 h-9 flex items-center justify-center rounded-full border-2 border-accent text-accent hover:bg-accent hover:text-surface transition-all"
              title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              <span className="material-icons text-xl">{isDarkMode ? 'light_mode' : 'dark_mode'}</span>
            </button>
          </div>
        </div>
      </header>
    </div>
  );
}
