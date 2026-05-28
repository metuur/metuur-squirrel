import { useMe } from '@/hooks/useMe';
import { api } from '@/api/client';

export default function SettingsPage() {
  const { data: me, mutate } = useMe();

  async function setTheme(theme: 'auto' | 'light' | 'dark') {
    await api.setTheme(theme);
    applyThemeClass(theme);
    await mutate();
  }

  async function setWorkspace(name: string) {
    await api.setVault(name);
    await mutate();
    window.location.reload();
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Settings</h1>

      <SettingsSection icon="palette" title="Appearance" subtitle="Pick how Squirrel looks">
        <div className="inline-flex bg-slate-100 dark:bg-slate-800 p-0.5 rounded-full border border-border-light dark:border-border-dark">
          {(['auto', 'light', 'dark'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`px-3 py-1.5 text-sm font-semibold rounded-full inline-flex items-center gap-1 transition-all ${
                me?.theme === t
                  ? 'text-primary bg-white dark:bg-slate-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <span className="material-icons text-base">
                {t === 'auto' ? 'devices' : t === 'light' ? 'light_mode' : 'dark_mode'}
              </span>
              {t === 'auto' ? 'Match my device' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </SettingsSection>

      {me?.active_workspace && (
        <SettingsSection icon="folder_open" title="Obsidian Vault" subtitle="The Markdown folder Squirrel reads">
          <div className="space-y-3">
            {me.multi_vault ? (
              <select
                value={me.active_workspace.name}
                onChange={(e) => setWorkspace(e.target.value)}
                className="w-64 px-3 py-2 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-sm focus:border-primary focus:ring-0 outline-none"
              >
                {me.workspaces.map((w) => (
                  <option key={w.name} value={w.name}>{w.name}</option>
                ))}
              </select>
            ) : (
              <div className="text-sm">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Name</span>
                <p className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5">{me.active_workspace.name}</p>
              </div>
            )}
            <div className="text-sm">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Path</span>
              <p className="font-mono text-xs break-all text-slate-700 dark:text-slate-300 mt-0.5 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                {me.active_workspace.path}
              </p>
            </div>
            {me.multi_vault && (
              <p className="text-xs text-slate-500">Switching reloads the page so every view shows the new vault.</p>
            )}
          </div>
        </SettingsSection>
      )}

      <SettingsSection icon="info" title="About" subtitle="What you're running">
        <div className="text-sm text-slate-700 dark:text-slate-300">
          <p>Squirrel <strong>{me?.version ?? '?'}</strong></p>
          <p className="mt-1 text-slate-500">This is the browser interface. The command line keeps working as before.</p>
        </div>
      </SettingsSection>
    </div>
  );
}

function SettingsSection({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-br from-primary/5 via-transparent to-transparent border-b border-border-light dark:border-border-dark flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center shrink-0">
          <span className="material-icons text-primary">{icon}</span>
        </div>
        <div className="min-w-0">
          <h2 className="font-bold text-slate-900 dark:text-slate-100 leading-tight">{title}</h2>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="px-6 py-5">{children}</div>
    </section>
  );
}

function applyThemeClass(theme: 'auto' | 'light' | 'dark') {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else if (theme === 'light') root.classList.remove('dark');
  else {
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (dark) root.classList.add('dark');
    else root.classList.remove('dark');
  }
}
