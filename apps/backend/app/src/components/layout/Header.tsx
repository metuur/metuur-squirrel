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

  // Cmd+K focuses the search box
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

  // Debounced search
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
    <div className="flex flex-col sticky top-0 z-20 shadow-sm">
      <header className="h-14 border-b border-border-light dark:border-border-dark bg-white dark:bg-surface-dark flex items-center px-6 gap-10 transition-colors duration-200">
        <div className="flex items-center gap-6 shrink-0">
          <Link
            to="/"
            className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100 hover:opacity-80 transition-opacity cursor-pointer"
          >
            <img src="/squirrel.svg" alt="" aria-hidden="true" className="w-8 h-8" />
            <span className="tracking-tight">Squirrel</span>
          </Link>

          <div className={`${showViewToggle ? 'hidden md:flex' : 'hidden'} bg-slate-100 dark:bg-slate-800 p-0.5 rounded border border-border-light dark:border-border-dark`}>
            <button
              onClick={() => setViewMode('List')}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                viewMode === 'List'
                  ? 'text-primary bg-white dark:bg-slate-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('Board')}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                viewMode === 'Board'
                  ? 'text-primary bg-white dark:bg-slate-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
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
                className="appearance-none flex items-center gap-2 pl-9 pr-8 py-1.5 border border-border-light dark:border-border-dark rounded bg-white dark:bg-slate-800 text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer hover:border-slate-300 dark:hover:border-slate-600 transition-all shadow-sm outline-none focus:ring-1 focus:ring-primary"
              >
                {me.workspaces.map((w) => (
                  <option key={w.name} value={w.name}>{w.name}</option>
                ))}
              </select>
              <span className="material-icons text-slate-400 text-lg absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none">folder_open</span>
              <span className="material-icons text-slate-400 text-lg absolute right-1 top-1/2 -translate-y-1/2 pointer-events-none">arrow_drop_down</span>
            </div>
          )}

          <div className="relative w-full max-w-sm group">
            <span className="material-icons absolute left-3 top-[7px] text-slate-400 text-lg pointer-events-none group-focus-within:text-primary transition-colors">search</span>
            <input
              ref={searchRef}
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onFocus={() => results.length && setShowResults(true)}
              onBlur={() => setTimeout(() => setShowResults(false), 150)}
              className="w-full pl-10 pr-10 py-1.5 text-sm border-2 border-slate-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:border-primary focus:ring-0 outline-none transition-all placeholder-slate-400 shadow-sm"
              placeholder="Search notes... (Cmd+K)"
            />
            {searching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-slate-300 border-t-primary rounded-full animate-spin" />
            )}
            {showResults && results.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 max-h-80 overflow-auto rounded-md border border-border-light dark:border-border-dark bg-white dark:bg-surface-dark shadow-lg z-50">
                {results.slice(0, 12).map((h) => (
                  <Link
                    key={h.id}
                    to={`/notes/${h.id}`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { setShowResults(false); setQ(''); }}
                    className="block border-b border-border-light dark:border-border-dark last:border-0 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-700/50"
                  >
                    <div className="truncate font-medium text-slate-900 dark:text-slate-100">{h.title}</div>
                    {h.snippet_lines[0] && (
                      <div className="truncate text-xs text-slate-500 dark:text-slate-400">{h.snippet_lines[0]}</div>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 ml-2">
            <button
              onClick={() => openCapture()}
              className="bg-primary hover:bg-primary-dark text-white text-sm font-semibold px-4 py-1.5 rounded shadow-sm flex items-center gap-1 transition-all"
            >
              <span className="material-icons text-lg">add</span>
              Add a note
            </button>

            <button
              onClick={toggleDarkMode}
              className="w-9 h-9 flex items-center justify-center rounded-full border-2 border-primary text-primary hover:bg-primary hover:text-white transition-all"
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
