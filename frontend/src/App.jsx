import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { storageBatchService } from './services/cropService';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import AuthPages from './pages/public/AuthPages';
import FarmerDashboard from './pages/farmer/FarmerDashboard';
import CropOnboardingPage from './pages/farmer/CropOnboardingPage';
import StorageBatchesPage from './pages/farmer/StorageBatchesPage';
import MonitoringPage from './pages/farmer/MonitoringPage';
import DiaryPage from './pages/farmer/DiaryPage';
import ChatbotPage from './pages/farmer/ChatbotPage';
import AlertsPage from './pages/farmer/AlertsPage';
import WeatherPage from './pages/farmer/WeatherPage';
import MarketPricesPage from './pages/farmer/MarketPricesPage';
import TraditionalGuidancePage from './pages/farmer/TraditionalGuidancePage';
import AdminDashboard from './pages/admin/AdminDashboard';
import FarmerProfilePage from './pages/farmer/FarmerProfilePage';

export default function App() {
  const { user, loading } = useAuth();
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [batches, setBatches] = useState([]);
  const [activeBatch, setActiveBatch] = useState(null);
  const [batchesLoading, setBatchesLoading] = useState(false);

  const fetchBatches = async () => {
    if (!user) return;

    setBatchesLoading(true);

    try {
      const data = await storageBatchService.getBatches();

      setBatches(data || []);

      if (data && data.length > 0) {
        setActiveBatch((previousBatch) => {
          if (
            previousBatch &&
            data.some((batch) => batch.batch_id === previousBatch.batch_id)
          ) {
            return data.find(
              (batch) => batch.batch_id === previousBatch.batch_id
            );
          }

          return data[0];
        });
      } else {
        setActiveBatch(null);
      }
    } catch (error) {
      console.error('Error fetching storage batches:', error);
    } finally {
      setBatchesLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== 'admin') {
      fetchBatches();
    }
  }, [user]);

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#090d16',
          color: '#10b981',
          fontSize: '1.2rem',
          fontWeight: '700',
        }}
      >
        Loading FarmShield...
      </div>
    );
  }

  if (!user) {
    return <AuthPages />;
  }

  if (user.role === 'admin') {
    return (
      <div className="app-container">
        <Sidebar
          currentTab="admin"
          onSelectTab={() => setCurrentTab('admin')}
        />

        <div className="main-content">
          <Navbar
            activeBatch={null}
            batches={[]}
            onSelectBatch={() => {}}
            activeAlertsCount={0}
          />

          <main className="page-wrapper">
            <AdminDashboard />
          </main>
        </div>
      </div>
    );
  }

  const handleBatchCreated = (newBatch) => {
    setBatches((previousBatches) => [newBatch, ...previousBatches]);
    setActiveBatch(newBatch);
    setCurrentTab('dashboard');
  };

  return (
    <div className="app-container">
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
      />

      <div className="main-content">
        <Navbar
          activeBatch={activeBatch}
          batches={batches}
          onSelectBatch={setActiveBatch}
          activeAlertsCount={activeBatch?.active_alerts_count || 0}
        />

        <main className="page-wrapper">
          {currentTab === 'dashboard' && (
            <FarmerDashboard
              activeBatch={activeBatch}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'onboarding' && (
            <CropOnboardingPage onBatchCreated={handleBatchCreated} />
          )}

          {currentTab === 'batches' && (
            <StorageBatchesPage
              batches={batches}
              activeBatch={activeBatch}
              onSelectBatch={setActiveBatch}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'monitoring' && (
            <MonitoringPage activeBatch={activeBatch} />
          )}

          {currentTab === 'diary' && (
            <DiaryPage activeBatch={activeBatch} />
          )}

          {currentTab === 'chatbot' && (
            <ChatbotPage activeBatch={activeBatch} />
          )}

          {currentTab === 'alerts' && (
            <AlertsPage activeBatch={activeBatch} />
          )}

          {currentTab === 'weather' && (
            <WeatherPage activeBatch={activeBatch} />
          )}

          {currentTab === 'market' && (
            <MarketPricesPage activeBatch={activeBatch} />
          )}

          {currentTab === 'traditional' && (
            <TraditionalGuidancePage />
          )}

          {currentTab === 'profile' && (
            <FarmerProfilePage />
          )}

          {currentTab === 'admin' && (
            <AdminDashboard />
          )}
        </main>
      </div>
    </div>
  );
}