import React, { useCallback, useEffect, useState } from 'react';
import { apiRequest } from '../../services/apiClient';
import { ClipboardList, Leaf, Utensils, Package, Sprout, CalendarDays, Plus, Trash2, RefreshCw } from 'lucide-react';

const sections = [
  { id: 'menu', label: 'Menu Management', group: 'Restaurant', icon: Utensils, hint: 'Dishes, prices and availability' },
  { id: 'orders', label: 'Order Tracking', group: 'Restaurant', icon: ClipboardList, hint: 'Track orders from received to completed' },
  { id: 'inventory', label: 'Restaurant Inventory', group: 'Restaurant', icon: Package, hint: 'Ingredients and stock levels' },
  { id: 'plots', label: 'Orchard Plots', group: 'Orchard', icon: Sprout, hint: 'Variety, area and plot status' },
  { id: 'activities', label: 'Orchard Activities', group: 'Orchard', icon: CalendarDays, hint: 'Pruning, irrigation, fertilizing and spraying' },
  { id: 'observations', label: 'Observations', group: 'Orchard', icon: Leaf, hint: 'Tree health, pests, weather and field notes' },
  { id: 'harvests', label: 'Harvest Records', group: 'Orchard', icon: ClipboardList, hint: 'Harvest date, crop, quantity and unit' },
];
const emptyForm = { title: '', status: 'planned', notes: '', quantity: '', unit: '', scheduled_date: '', category: '', extra: {} };
const styles = {
  card: { background: 'rgba(15,23,42,.72)', border: '1px solid rgba(148,163,184,.18)', borderRadius: 16, padding: 18 },
  input: { width: '100%', boxSizing: 'border-box', background: '#0b1220', color: '#e2e8f0', border: '1px solid #334155', borderRadius: 9, padding: '10px 12px', marginTop: 6 },
  button: { border: 0, borderRadius: 9, padding: '10px 14px', background: '#059669', color: 'white', cursor: 'pointer', fontWeight: 700 },
};
export default function OperationsPage() {
  const [section, setSection] = useState('menu');
  const [records, setRecords] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const active = sections.find((item) => item.id === section) || sections[0];

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const response = await apiRequest('/operations/' + section);
      setRecords(response?.data || []);
    } catch (err) {
      setError(err.message || 'Could not load records.');
      setRecords([]);
    } finally { setLoading(false); }
  }, [section]);
  useEffect(() => { load(); }, [load]);

  const save = async (event) => {
    event.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true); setError('');
    try {
      await apiRequest('/operations/' + section, {
        method: 'POST',
        body: JSON.stringify({ ...form, quantity: form.quantity === '' ? null : Number(form.quantity) }),
      });
      setForm(emptyForm);
      await load();
    } catch (err) { setError(err.message || 'Could not save record.'); }
    finally { setSaving(false); }
  };
  const remove = async (recordId) => {
    if (!window.confirm('Delete this record?')) return;
    try { await apiRequest('/operations/' + section + '/' + recordId, { method: 'DELETE' }); await load(); }
    catch (err) { setError(err.message || 'Could not delete record.'); }
  };

  return <div style={{ color: '#e2e8f0', padding: '4px 0 28px' }}>
    <header style={{ marginBottom: 22 }}>
      <div style={{ color: '#34d399', fontSize: 12, fontWeight: 800, letterSpacing: 2, textTransform: 'uppercase' }}>Operations workspace</div>
      <h1 style={{ margin: '8px 0', fontSize: 28 }}>Restaurant & Orchard Management</h1>
      <p style={{ color: '#94a3b8', margin: 0 }}>Manage restaurant workflows and orchard field records in one place. Records are stored per signed-in user.</p>
    </header>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10, marginBottom: 20 }}>
      {sections.map(item => { const Icon = item.icon; return <button key={item.id} onClick={() => { setSection(item.id); setForm(emptyForm); }} style={{ ...styles.card, cursor: 'pointer', textAlign: 'left', borderColor: section === item.id ? '#10b981' : 'rgba(148,163,184,.18)', background: section === item.id ? 'rgba(5,150,105,.13)' : styles.card.background }}>
        <Icon size={20} color={section === item.id ? '#34d399' : '#94a3b8'} />
        <div style={{ fontWeight: 750, marginTop: 9 }}>{item.label}</div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 5 }}>{item.hint}</div>
      </button>; })}
    </div>
    {error && <div role="alert" style={{ ...styles.card, borderColor: '#b45309', color: '#fbbf24', marginBottom: 14 }}>{error}</div>}
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, .85fr) minmax(300px, 1.4fr)', gap: 16 }}>
      <form onSubmit={save} style={styles.card}>
        <h2 style={{ fontSize: 18, marginTop: 0 }}>Add {active.label.replace(/s$/, '')}</h2>
        <label style={{ display: 'block', color: '#cbd5e1', fontSize: 13 }}>Name / title *<input required maxLength={160} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder={section === 'orders' ? 'Order # or customer name' : section === 'plots' ? 'Plot A — mango' : 'Enter a clear title'} style={styles.input} /></label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
          <label style={{ color: '#cbd5e1', fontSize: 13 }}>Status<select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} style={styles.input}>{(section === 'orders' ? ['received','preparing','ready','completed','cancelled'] : section === 'menu' ? ['available','unavailable'] : section === 'harvests' ? ['planned','in_progress','completed'] : ['planned','in_progress','completed','needs_attention']).map(s => <option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select></label>
          <label style={{ color: '#cbd5e1', fontSize: 13 }}>Category<input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder={section === 'activities' ? 'Irrigation' : 'Type'} style={styles.input} /></label>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
          <label style={{ color: '#cbd5e1', fontSize: 13 }}>Quantity<input type="number" min="0" step="any" value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })} style={styles.input} /></label>
          <label style={{ color: '#cbd5e1', fontSize: 13 }}>Unit<input value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} placeholder="kg, items, acres..." style={styles.input} /></label>
        </div>
        <label style={{ display: 'block', color: '#cbd5e1', fontSize: 13, marginTop: 12 }}>Date<input type="date" value={form.scheduled_date} onChange={e => setForm({ ...form, scheduled_date: e.target.value })} style={styles.input} /></label>
        <label style={{ display: 'block', color: '#cbd5e1', fontSize: 13, marginTop: 12 }}>Notes<textarea rows={3} maxLength={4000} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Add useful details..." style={{ ...styles.input, resize: 'vertical' }} /></label>
        <button disabled={saving} type="submit" style={{ ...styles.button, marginTop: 16, opacity: saving ? .65 : 1 }}><Plus size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />{saving ? 'Saving…' : 'Save record'}</button>
      </form>
      <section style={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
          <div><h2 style={{ margin: 0, fontSize: 18 }}>{active.label}</h2><p style={{ color: '#94a3b8', fontSize: 13, margin: '5px 0 0' }}>{records.length} record{records.length === 1 ? '' : 's'}</p></div>
          <button onClick={load} type="button" aria-label="Refresh records" style={{ ...styles.button, background: '#1e293b' }}><RefreshCw size={16} /></button>
        </div>
        {loading ? <p style={{ color: '#94a3b8', padding: 20 }}>Loading records…</p> : records.length === 0 ? <div style={{ textAlign: 'center', padding: '38px 10px', color: '#94a3b8' }}><ClipboardList size={30} /><p>No records yet. Use the form to add your first one.</p></div> :
          <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>{records.map(record => <article key={record.record_id} style={{ background: '#0b1220', border: '1px solid #263449', borderRadius: 12, padding: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 10 }}>
              <div><div style={{ fontWeight: 750 }}>{record.title}</div><div style={{ color: '#34d399', fontSize: 12, marginTop: 5 }}>{record.status?.replaceAll('_',' ')}{record.category ? ' · ' + record.category : ''}</div></div>
              <button type="button" onClick={() => remove(record.record_id)} aria-label={'Delete ' + record.title} style={{ background: 'transparent', color: '#f87171', border: 0, cursor: 'pointer' }}><Trash2 size={17} /></button>
            </div>
            {(record.quantity !== null && record.quantity !== undefined) || record.unit ? <div style={{ color: '#cbd5e1', fontSize: 13, marginTop: 8 }}>Quantity: {record.quantity ?? '—'} {record.unit}</div> : null}
            {record.scheduled_date && <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 5 }}>Date: {record.scheduled_date}</div>}
            {record.notes && <p style={{ color: '#cbd5e1', fontSize: 13, whiteSpace: 'pre-wrap', marginBottom: 0 }}>{record.notes}</p>}
          </article>)}</div>}
      </section>
    </div>
    <style>{'@media(max-width:760px){.page-wrapper div[style*="minmax(260px"]{grid-template-columns:1fr!important}}'}</style>
  </div>;
}
