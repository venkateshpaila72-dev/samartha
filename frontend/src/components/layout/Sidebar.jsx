import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import TranslatedText from '../TranslatedText';
import {
  LayoutDashboard, Sprout, Activity, BookOpen, MessageSquare, AlertTriangle,
  CloudSun, TrendingUp, Scroll, ShieldAlert, UserRound,
} from 'lucide-react';

export default function Sidebar({ currentTab, onSelectTab }) {
  const { user } = useAuth();
  const { t } = useLanguage();

  const farmerNavItems = [
    { id: 'dashboard', label: t('dashboard'), icon: LayoutDashboard },
    { id: 'onboarding', label: t('onboarding'), icon: Sprout },
    { id: 'batches', label: t('my_batches'), icon: Sprout },
    { id: 'monitoring', label: t('monitoring'), icon: Activity },
    { id: 'diary', label: t('diary'), icon: BookOpen },
    { id: 'chatbot', label: t('ai_assistant'), icon: MessageSquare },
    { id: 'alerts', label: t('alerts'), icon: AlertTriangle },
    { id: 'weather', label: t('weather'), icon: CloudSun },
    { id: 'market', label: t('market'), icon: TrendingUp },
    { id: 'profile', label: t('profile'), icon: UserRound },
    { id: 'traditional', label: t('traditional'), icon: Scroll },
  ];

  return (
    <aside className="sidebar-nav" style={{ padding: '24px 16px' }}>
      <div style={{ marginBottom: '24px', padding: '0 8px' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: '#64748b', letterSpacing: '0.08em' }}>
          {t('navigation')}
        </span>
      </div>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {farmerNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button key={item.id} onClick={() => onSelectTab(item.id)} style={{
              display: 'flex', alignItems: 'center', gap: '12px', padding: '11px 14px',
              borderRadius: '10px', border: 'none',
              background: isActive ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.15) 100%)' : 'transparent',
              color: isActive ? '#34d399' : '#94a3b8', fontWeight: isActive ? '700' : '500',
              fontSize: '0.92rem', cursor: 'pointer', textAlign: 'left',
              transition: 'all 0.15s ease', borderLeft: isActive ? '3px solid #10b981' : '3px solid transparent'
            }}>
              <Icon size={19} color={isActive ? '#10b981' : '#64748b'} />
              <span>{item.label}</span>
            </button>
          );
        })}
        {user?.role === 'admin' && (
          <>
            <div style={{ marginTop: '24px', marginBottom: '8px', padding: '0 8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: '#f59e0b', letterSpacing: '0.08em' }}>
                {t('system_admin')}
              </span>
            </div>
            <button onClick={() => onSelectTab('admin')} style={{
              display: 'flex', alignItems: 'center', gap: '12px', padding: '11px 14px',
              borderRadius: '10px', border: 'none',
              background: currentTab === 'admin' ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              color: currentTab === 'admin' ? '#fbbf24' : '#94a3b8',
              fontWeight: currentTab === 'admin' ? '700' : '500', fontSize: '0.92rem',
              cursor: 'pointer', borderLeft: currentTab === 'admin' ? '3px solid #f59e0b' : '3px solid transparent'
            }}>
              <ShieldAlert size={19} color={currentTab === 'admin' ? '#f59e0b' : '#64748b'} />
              <span>{t('admin_management')}</span>
            </button>
          </>
        )}
      </nav>
      <div style={{ marginTop: 'auto', padding: '16px 8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <div style={{ fontSize: '0.78rem', color: '#64748b' }}>FarmShield Core v1.0</div>
        <div style={{ fontSize: '0.72rem', color: '#10b981', marginTop: '2px' }}>
          <TranslatedText text="Verified Scientific ICAR Data" />
        </div>
      </div>
    </aside>
  );
}
