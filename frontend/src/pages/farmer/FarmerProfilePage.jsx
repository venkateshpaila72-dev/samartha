import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { marketService } from '../../services/marketService';
import { useLanguage } from '../../context/LanguageContext';
import { UserRound, Save, RefreshCw, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';

const inputStyle = { width: '100%', boxSizing: 'border-box', padding: '11px 12px', borderRadius: '9px', border: '1px solid rgba(148,163,184,.3)', background: 'rgba(15,23,42,.75)', color: '#f8fafc' };
const labelStyle = { display: 'flex', flexDirection: 'column', gap: '7px', color: '#cbd5e1', fontSize: '.9rem' };

export default function FarmerProfilePage({ onNavigate }) {
  const { user, updateProfile } = useAuth();
  const { t } = useLanguage();
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState(null);
  const [syncResult, setSyncResult] = useState(null);
  useEffect(() => setForm({
    full_name: user?.full_name || '', phone_number: user?.phone_number || '',
    village_or_location: user?.village_or_location || '', selected_crop: user?.selected_crop || '',
    state: user?.state || '', district: user?.district || '',
  }), [user]);
  const field = (name, value) => setForm(prev => ({ ...prev, [name]: value }));
  const save = async (event) => {
    event.preventDefault(); setSaving(true); setNotice(null);
    try {
      const result = await updateProfile({
        full_name: (form.full_name || '').trim(), phone_number: (form.phone_number || '').trim() || null,
        village_or_location: (form.village_or_location || '').trim() || null,
        selected_crop: (form.selected_crop || '').trim() || null,
        state: (form.state || '').trim() || null, district: (form.district || '').trim() || null,
      });
      try {
        if (result.selected_crop) localStorage.setItem('farmshield_selected_crop', result.selected_crop);
        if (result.state) localStorage.setItem('farmshield_state', result.state);
        if (result.district) localStorage.setItem('farmshield_district', result.district);
      } catch {}
      setNotice({ ok: true, text: t('profile_saved') });
    } catch (e) { setNotice({ ok: false, text: e.message || t('profile_save_failed') }); }
    finally { setSaving(false); }
  };
  const sync = async () => {
    if (!(form.selected_crop || '').trim() || !(form.state || '').trim()) {
      setNotice({ ok: false, text: t('crop_state_required') }); return;
    }
    setSyncing(true); setNotice(null); setSyncResult(null);
    try {
      await updateProfile({
        full_name: (form.full_name || '').trim(), phone_number: (form.phone_number || '').trim() || null,
        village_or_location: (form.village_or_location || '').trim() || null,
        selected_crop: form.selected_crop.trim(), state: form.state.trim(), district: (form.district || '').trim() || null,
      });
      const result = await marketService.syncMarketPrices({ crop: form.selected_crop.trim(), state: form.state.trim(), district: (form.district || '').trim() });
      const payload = result?.data || result;
      setSyncResult(payload);
      setNotice({ ok: true, text: t('market_sync_done') });
    } catch (e) { setNotice({ ok: false, text: e.message || t('market_sync_failed') }); }
    finally { setSyncing(false); }
  };
  const fields = [
    ['full_name','full_name_label',t('full_name')], ['phone_number','phone_label',t('phone_number')],
    ['village_or_location','location_label',t('village_location')], ['selected_crop','crop_label',t('selected_crop')],
    ['state','state_label',t('state')], ['district','district_label',t('district_optional')],
  ];
  return <div style={{ display:'flex', flexDirection:'column', gap:20, minWidth:0 }}>
    <section className="glass-panel glow-border" style={{ padding:'clamp(16px,3vw,26px)' }}>
      <h1 style={{ display:'flex', alignItems:'center', gap:10, marginTop:0 }}><UserRound color="#34d399"/>{t('profile_title')}</h1>
      <p style={{ color:'#94a3b8' }}>{t('profile_description')}</p>
      <form onSubmit={save} style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,230px),1fr))', gap:16 }}>
        {fields.slice(0,3).map(([key,label,text])=><label key={key} style={labelStyle}>{text}<input style={inputStyle} value={form[key] || ''} onChange={e=>field(key,e.target.value)} required={key==='full_name'} /></label>)}
        <label style={labelStyle}>{t('email')}<input style={{...inputStyle,opacity:.7}} value={user?.email || ''} readOnly /></label>
        <button className="btn-primary" disabled={saving||syncing} type="submit" style={{display:'inline-flex',alignItems:'center',justifyContent:'center',gap:8}}><Save size={16}/>{saving?t('saving'):t('save_profile')}</button>
      </form>
    </section>
    <section className="glass-panel" style={{ padding:'clamp(16px,3vw,26px)' }}>
      <h2 style={{display:'flex',alignItems:'center',gap:10,marginTop:0}}><TrendingUp color="#34d399"/>{t('market_sync_title')}</h2>
      <p style={{color:'#94a3b8',lineHeight:1.6}}>{t('market_sync_description')}</p>
      <form onSubmit={save} style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,210px),1fr))',gap:16}}>
        {fields.slice(3).map(([key,label,text])=><label key={key} style={labelStyle}>{text}<input style={inputStyle} value={form[key] || ''} onChange={e=>field(key,e.target.value)} required={key==='selected_crop'||key==='state'} /></label>)}
        <div style={{gridColumn:'1/-1',display:'flex',gap:10,flexWrap:'wrap'}}>
          <button className="btn-secondary" type="submit" disabled={saving||syncing}><Save size={16} style={{marginRight:7}}/>{t('save_market_preferences')}</button>
          <button className="btn-primary" type="button" disabled={saving||syncing||!(form.selected_crop||'').trim()||!(form.state||'').trim()} onClick={sync}><RefreshCw size={16} style={{marginRight:7}}/>{syncing?t('syncing'):t('sync_market_now')}</button>
          <button className="btn-secondary" type="button" onClick={()=>onNavigate?.('market')}>{t('view_market_prices')}</button>
        </div>
      </form>
      {syncResult && <div style={{marginTop:16,color:'#cbd5e1',overflowWrap:'anywhere'}}>{t('sync_result')}: {JSON.stringify(syncResult)}</div>}
    </section>
    {notice && <div role="status" aria-live="polite" className="glass-panel" style={{padding:16,display:'flex',gap:9,color:notice.ok?'#6ee7b7':'#fca5a5'}}>{notice.ok?<CheckCircle2 size={18}/>:<AlertCircle size={18}/>}<span>{notice.text}</span></div>}
  </div>;
}
