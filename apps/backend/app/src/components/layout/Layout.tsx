import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header, type ViewMode } from './Header';
import { Sidebar } from './Sidebar';
import { useMe } from '@/hooks/useMe';
import { asVaultRecovery } from '@/api/client';
import { VaultRecovery } from '@/components/VaultRecovery';

export function Layout() {
  const { data: me, error, mutate } = useMe();
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

  // Vault configured but unusable (moved / emptied / not a Squirrel vault):
  // take over the whole surface with a guided recovery flow instead of
  // rendering an app shell full of failing widgets.
  const recovery = asVaultRecovery(error);
  if (recovery) {
    return (
      <div className="h-full overflow-auto bg-surface-2">
        <VaultRecovery info={recovery} onRecovered={mutate} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[300] focus:top-3 focus:left-3 focus:px-3 focus:py-2 focus:rounded-md focus:bg-accent focus:text-surface focus:text-sm focus:font-semibold focus:shadow-lg"
      >
        Skip to content
      </a>
      <Header
        viewMode={viewMode}
        setViewMode={setViewMode}
        isDarkMode={isDarkMode}
        toggleDarkMode={toggleDark}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-auto p-6">
          <Outlet context={{ viewMode, setViewMode }} />
        </main>
      </div>
    </div>
  );
}
