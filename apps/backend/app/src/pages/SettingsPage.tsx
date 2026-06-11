import { useEffect, useState } from 'react';
import { useMe } from '@/hooks/useMe';
import { api } from '@/api/client';
import { useToast } from '@/components/Toast';

export default function SettingsPage() {
  const { data: me, mutate } = useMe();
  const { show: toast } = useToast();

  const [localNotif, setLocalNotif] = useState<{
    in_app: boolean;
    os_popups: boolean;
    sound: 'Glass' | 'Funk' | 'Silent';
  }>({ in_app: true, os_popups: false, sound: 'Glass' });

  useEffect(() => {
    if (me?.notifications) {
      setLocalNotif({
        in_app: me.notifications.in_app,
        os_popups: me.notifications.os_popups,
        sound: me.notifications.sound,
      });
    }
  }, [me?.notifications?.in_app, me?.notifications?.os_popups, me?.notifications?.sound]); // eslint-disable-line react-hooks/exhaustive-deps

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

  async function handleSoundChange(sound: 'Glass' | 'Funk' | 'Silent') {
    const prev = localNotif;
    const next = { ...localNotif, sound };
    setLocalNotif(next);
    try {
      await api.setNotificationSettings(next);
      await mutate();
    } catch {
      setLocalNotif(prev);
      toast('Failed to save notification sound', 'error');
    }
  }

  async function handleSoundPreview(sound: 'Glass' | 'Funk' | 'Silent') {
    try {
      await api.previewNotificationSound(sound);
    } catch {
      toast('Could not preview sound', 'error');
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

  // ── Change the vault path (updates the entry in config.toml in place) ──────
  const [showChangeVault, setShowChangeVault] = useState(false);
  const [vaultPath, setVaultPath] = useState('');
  const [createVault, setCreateVault] = useState(false);
  const [changeBusy, setChangeBusy] = useState(false);
  const [changeError, setChangeError] = useState<string | null>(null);

  function openChangeVault() {
    setVaultPath(me?.active_workspace?.path ?? '');
    setCreateVault(false);
    setChangeError(null);
    setShowChangeVault(true);
  }

  async function handleChangeVault() {
    const path = vaultPath.trim();
    if (!path || !me?.active_workspace) return;
    setChangeBusy(true);
    setChangeError(null);
    try {
      await api.setVaultConfig({ name: me.active_workspace.name, path, create: createVault });
      window.location.reload();
    } catch (e) {
      setChangeError(e instanceof Error ? e.message : 'Could not change the vault.');
      setChangeBusy(false);
    }
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

            <div className="pt-3 border-t border-hairline">
              {!showChangeVault ? (
                <button type="button" onClick={openChangeVault} className="btn inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold rounded-lg bg-surface">
                  <span className="material-icons text-base">drive_file_move</span>
                  Change vault
                </button>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-ink-2">Change vault</p>
                  <div className="text-sm">
                    <span className="eyebrow">New path</span>
                    <input
                      type="text"
                      value={vaultPath}
                      onChange={(e) => setVaultPath(e.target.value)}
                      placeholder="~/my-vault"
                      className="mt-0.5 w-full block px-3 py-2 border border-hairline rounded-lg bg-surface font-mono text-xs focus:border-accent focus:ring-0 outline-none placeholder-ink-4"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm text-ink-2">
                    <input
                      type="checkbox"
                      checked={createVault}
                      onChange={(e) => setCreateVault(e.target.checked)}
                      className="accent-[var(--color-accent)]"
                    />
                    Create the folder (with the Squirrel structure) if it doesn’t exist
                  </label>
                  {changeError && <p className="text-sm text-critical">{changeError}</p>}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleChangeVault}
                      disabled={
                        changeBusy ||
                        !vaultPath.trim() ||
                        vaultPath.trim() === me.active_workspace.path
                      }
                      className="btn btn-primary inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold rounded-lg bg-surface disabled:opacity-50"
                    >
                      {changeBusy ? 'Changing…' : 'Change vault'}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowChangeVault(false); setChangeError(null); }}
                      disabled={changeBusy}
                      className="btn inline-flex items-center px-3 py-1.5 text-sm font-semibold rounded-lg bg-surface"
                    >
                      Cancel
                    </button>
                  </div>
                  <p className="text-xs text-ink-3">
                    Squirrel switches to reading and writing the new folder, and the page reloads.
                    Nothing in the current folder is moved or deleted — to bring its content along,
                    copy the folder yourself first, or run /sq-migrate-vault in your agent.
                  </p>
                </div>
              )}
            </div>
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
          <div className="pt-4 border-t border-hairline">
            <p className="text-sm font-medium text-ink-2 mb-3">Notification sound</p>
            <div className="space-y-2">
              {(['Glass', 'Funk', 'Silent'] as const).map((s) => (
                <SoundRow
                  key={s}
                  sound={s}
                  selected={localNotif.sound === s}
                  onSelect={() => handleSoundChange(s)}
                  onPreview={() => handleSoundPreview(s)}
                />
              ))}
            </div>
          </div>
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

function SoundRow({
  sound,
  selected,
  onSelect,
  onPreview,
}: {
  sound: 'Glass' | 'Funk' | 'Silent';
  selected: boolean;
  onSelect: () => void;
  onPreview: () => void;
}) {
  const icon = sound === 'Silent' ? 'volume_off' : 'music_note';
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors border ${
          selected
            ? 'bg-focus-tint text-accent border-accent/40'
            : 'text-ink-2 hover:bg-surface-2 border-transparent'
        }`}
      >
        <span className="material-icons text-base">{icon}</span>
        <span>{sound}</span>
        {selected && <span className="ml-auto material-icons text-base">check</span>}
      </button>
      <button
        type="button"
        onClick={onPreview}
        disabled={sound === 'Silent'}
        title={sound === 'Silent' ? 'Silent has no preview' : `Preview ${sound}`}
        aria-label={`Preview ${sound}`}
        className="w-9 h-9 inline-flex items-center justify-center rounded-lg text-ink-3 hover:text-accent hover:bg-surface-2 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <span className="material-icons text-base">volume_up</span>
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
