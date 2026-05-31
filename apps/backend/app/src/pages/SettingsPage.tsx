import { useEffect, useState } from 'react';
import { useMe } from '@/hooks/useMe';
import { api } from '@/api/client';
import { useToast } from '@/components/Toast';

export default function SettingsPage() {
  const { data: me, mutate } = useMe();
  const { show: toast } = useToast();

  const [localNotif, setLocalNotif] = useState({ in_app: true, os_popups: false });

  useEffect(() => {
    if (me?.notifications) {
      setLocalNotif({ in_app: me.notifications.in_app, os_popups: me.notifications.os_popups });
    }
  }, [me?.notifications?.in_app, me?.notifications?.os_popups]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleNotifToggle(field: 'in_app' | 'os_popups', value: boolean) {
    const prev = localNotif;
    const next = { ...localNotif, [field]: value };
    setLocalNotif(next);
    try {
      await api.setNotificationSettings(next);
      await mutate();
    } catch {
      setLocalNotif(prev);
      toast('Failed to save notification settings', 'error');
    }
  }

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
      <h1 className="title">Settings</h1>

      <SettingsSection icon="palette" title="Appearance" subtitle="Pick how Squirrel looks">
        <div className="inline-flex bg-surface-2 p-0.5 rounded-full border border-hairline">
          {(['auto', 'light', 'dark'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`px-3 py-1.5 text-sm font-semibold rounded-full inline-flex items-center gap-1 transition-all ${
                me?.theme === t
                  ? 'text-accent bg-surface shadow-sm'
                  : 'text-ink-3 hover:text-ink-2'
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
                className="w-64 px-3 py-2 border border-hairline rounded-lg bg-surface text-sm focus:border-accent focus:ring-0 outline-none"
              >
                {me.workspaces.map((w) => (
                  <option key={w.name} value={w.name}>{w.name}</option>
                ))}
              </select>
            ) : (
              <div className="text-sm">
                <span className="eyebrow">Name</span>
                <p className="font-semibold text-ink mt-0.5">{me.active_workspace.name}</p>
              </div>
            )}
            <div className="text-sm">
              <span className="eyebrow">Path</span>
              <p className="font-mono text-xs break-all text-ink-2 mt-0.5 px-3 py-2 rounded-lg bg-surface-2 border border-hairline">
                {me.active_workspace.path}
              </p>
            </div>
            {me.multi_vault && (
              <p className="text-xs text-ink-3">Switching reloads the page so every view shows the new vault.</p>
            )}
          </div>
        </SettingsSection>
      )}

      <SettingsSection icon="notifications" title="Notifications" subtitle="Control how Squirrel surfaces alerts">
        <div className="space-y-4">
          <ToggleRow
            label="In-app notifications"
            value={localNotif.in_app}
            onChange={(v) => handleNotifToggle('in_app', v)}
          />
          <ToggleRow
            label="OS notifications"
            value={localNotif.os_popups}
            onChange={(v) => handleNotifToggle('os_popups', v)}
            disabled={!localNotif.in_app}
          />
        </div>
      </SettingsSection>

      <SettingsSection icon="info" title="About" subtitle="What you're running">
        <div className="text-sm text-ink-2">
          <p>Squirrel <strong>{me?.version ?? '?'}</strong></p>
          <p className="mt-1 text-ink-3">This is the browser interface. The command line keeps working as before.</p>
        </div>
      </SettingsSection>
    </div>
  );
}

function ToggleRow({
  label,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className={`flex items-center justify-between gap-4 ${disabled ? 'opacity-40' : ''}`}>
      <span className="text-sm font-medium text-ink-2">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        disabled={disabled}
        onClick={() => onChange(!value)}
        className={`relative h-6 w-10 rounded-full transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:cursor-not-allowed ${
          value ? 'bg-accent' : 'bg-ink-4'
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-surface shadow transition-transform duration-200 ${
            value ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
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
    <section className="panel overflow-hidden">
      <div className="px-6 py-4 border-b border-hairline-2 bg-focus-tint/40 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-focus-tint flex items-center justify-center shrink-0">
          <span className="material-icons text-accent">{icon}</span>
        </div>
        <div className="min-w-0">
          <h2 className="font-bold text-ink leading-tight">{title}</h2>
          {subtitle && <p className="text-xs text-ink-3 mt-0.5">{subtitle}</p>}
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
