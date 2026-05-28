import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header, type ViewMode } from './Header';
import { Sidebar } from './Sidebar';
import { useMe } from '@/hooks/useMe';

export function Layout() {
  const { data: me } = useMe();
  const [viewMode, setViewMode] = useState<ViewMode>('Board');
  const [isDarkMode, setDarkMode] = useState(false);

  // Apply persisted theme
  useEffect(() => {
    if (!me) return;
    if (me.theme === 'dark') { setDarkMode(true); document.documentElement.classList.add('dark'); }
    else if (me.theme === 'light') { setDarkMode(false); document.documentElement.classList.remove('dark'); }
    else {
      const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setDarkMode(dark);
      if (dark) document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    }
  }, [me?.theme]);

  function toggleDark() {
    const next = !isDarkMode;
    setDarkMode(next);
    if (next) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        viewMode={viewMode}
        setViewMode={setViewMode}
        isDarkMode={isDarkMode}
        toggleDarkMode={toggleDark}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet context={{ viewMode, setViewMode }} />
        </main>
      </div>
    </div>
  );
}
