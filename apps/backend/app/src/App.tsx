import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { CaptureProvider } from '@/components/CaptureModal';
import { ToastProvider } from '@/components/Toast';
import { ApiActivityIndicator } from '@/components/ApiActivity';

const HomePage = lazy(() => import('@/pages/HomePage'));
const ProjectPage = lazy(() => import('@/pages/ProjectPage'));
const ProjectEditPage = lazy(() => import('@/pages/ProjectEditPage'));
const NotePage = lazy(() => import('@/pages/NotePage'));
const NoteEditPage = lazy(() => import('@/pages/NoteEditPage'));
const DeadlinesPage = lazy(() => import('@/pages/DeadlinesPage'));
const JournalPage = lazy(() => import('@/pages/JournalPage'));
const HistoryPage = lazy(() => import('@/pages/HistoryPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));

export default function App() {
  return (
    <ToastProvider>
      <CaptureProvider>
        <ApiActivityIndicator />
        <Suspense fallback={<div className="p-8 text-center text-ink-4">Loading…</div>}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/projects/:slug" element={<ProjectPage />} />
              <Route path="/projects/:slug/edit" element={<ProjectEditPage />} />
              <Route path="/notes/:id" element={<NotePage />} />
              <Route path="/notes/:id/edit" element={<NoteEditPage />} />
              <Route path="/deadlines" element={<DeadlinesPage />} />
              <Route path="/journal" element={<JournalPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </CaptureProvider>
    </ToastProvider>
  );
}

function NotFound() {
  return (
    <div className="py-16 text-center text-ink-4">
      <span className="material-icons text-5xl text-ink-4">help_outline</span>
      <p className="mt-3">We could not find that page.</p>
    </div>
  );
}
