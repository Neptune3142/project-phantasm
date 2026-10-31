import { useEffect, useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import AccountsPage from './pages/AccountsPage';
import ThreatFeedPage from './pages/ThreatFeedPage';
import PipelinePage from './pages/PipelinePage';
import EpitaphsPage from './pages/EpitaphsPage';
import ScenariosPage from './pages/ScenariosPage';
import SettingsPage from './pages/SettingsPage';
import { getIntegrationStatus, updateCredential } from './services/api';

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [simMode, setSimMode] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const s = await getIntegrationStatus();
        setSimMode(s.simulation_mode);
      } catch (e) { /* backend unavailable */ }
    })();
  }, []);

  async function toggleSim() {
    const next = !simMode;
    setSimMode(next);
    try {
      await updateCredential('SIMULATION_MODE', String(next));
    } catch (e) { /* ignore */ }
  }

  function renderPage() {
    switch (page) {
      case 'dashboard': return <DashboardPage />;
      case 'accounts':  return <AccountsPage simMode={simMode} />;
      case 'threat':    return <ThreatFeedPage />;
      case 'pipeline':  return <PipelinePage />;
      case 'epitaphs':  return <EpitaphsPage />;
      case 'scenarios': return <ScenariosPage />;
      case 'settings':  return <SettingsPage />;
      default:           return <DashboardPage />;
    }
  }

  return (
    <div className="min-h-screen flex flex-col fog">
      <Header simMode={simMode} onToggleSim={toggleSim} />
      <div className="flex flex-1">
        <Sidebar active={page} onSelect={setPage} />
        <main className="flex-1 p-6 max-w-[1400px] mx-auto w-full">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
