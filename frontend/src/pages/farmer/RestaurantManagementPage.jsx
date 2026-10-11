import React, { useEffect, useState } from 'react';
import { apiRequest } from '../../services/apiClient';
import { ClipboardList, Utensils, Package, RefreshCw, Plus, Trash2 } from 'lucide-react';

const sections = [{id:'menu',label:'Menu',icon:Utensils},{id:'orders',label:'Orders',icon:ClipboardList},{id:'inventory',label:'Inventory',icon:Package}];
const empty = {name:'',category:'',quantity:'',unit:'',price:'',status:'active',customer:'',notes:''};
export default function RestaurantManagementPage() {
 const [section,setSection]=useState('menu'), [records,setRecords]=useState([]), [form,setForm]=useState(empty), [busy,setBusy]=useState(false), [error,setError]=useState('');
 async function load(){setBusy(true);setError('');try{const r=await apiRequest('/restaurant/'+section);setRecords(r.data||[])}catch(e){setError(e.message||'Could not load records.')}finally{setBusy(false)}}
 useEffect(()=>{load()},[section]);
 async function add(e){e.preventDefault();setError('');try{const payload={...form,quantity:form.quantity===''?null:Number(form.quantity),price:form.price===''?null:Number(form.price)};const r=await apiRequest('/restaurant/'+section,{method:'POST',body:JSON.stringify(payload)});setRecords(old=>[r.data,...old]);setForm(empty)}catch(e){setError(e.message||'Could not save record.')}}
 async function remove(id){try{await apiRequest('/restaurant/'+section+'/'+id,{method:'DELETE'});setRecords(old=>old.filter(x=>x.record_id!==id))}catch(e){setError(e.message||'Could not delete record.')}}
 const input={padding:10,border:'1px solid #cbd5e1',borderRadius:9,width:'100%',boxSizing:'border-box'};
 return <section style={{display:'grid',gap:18}}><header><h1>Restaurant Management</h1><p>Manage menu items, orders, and inventory in one place.</p></header>
 <nav style={{display:'flex',gap:8,flexWrap:'wrap'}}>{sections.map(s=>{const I=s.icon;return <button key={s.id} onClick={()=>setSection(s.id)} style={{padding:10,border:0,borderRadius:9,background:section===s.id?'#047857':'#e2e8f0',color:section===s.id?'white':'#0f172a'}}><I size={16} style={{verticalAlign:'middle',marginRight:6}}/>{s.label}</button>})}<button onClick={load} disabled={busy} aria-label="Refresh"><RefreshCw size={16}/></button></nav>
 {error&&<p role="alert" style={{color:'#b91c1c'}}>{error}</p>}
 <form onSubmit={add} style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(170px,1fr))',gap:10,padding:16,border:'1px solid #e2e8f0',borderRadius:14}}>
 <input required aria-label="Name" placeholder="Name / order number" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} style={input}/>
 <input aria-label="Category" placeholder="Category / item" value={form.category} onChange={e=>setForm({...form,category:e.target.value})} style={input}/>
 <input aria-label="Quantity" type="number" min="0" step="any" placeholder="Quantity" value={form.quantity} onChange={e=>setForm({...form,quantity:e.target.value})} style={input}/>
 <input aria-label="Unit" placeholder="Unit (kg, pieces)" value={form.unit} onChange={e=>setForm({...form,unit:e.target.value})} style={input}/>
 <input aria-label="Price" type="number" min="0" step="any" placeholder="Price / amount ₹" value={form.price} onChange={e=>setForm({...form,price:e.target.value})} style={input}/>
 <input aria-label="Customer" placeholder="Customer (optional)" value={form.customer} onChange={e=>setForm({...form,customer:e.target.value})} style={input}/>
 <input aria-label="Notes" placeholder="Notes" value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} style={input}/>
 <button type="submit" style={{background:'#047857',color:'white',border:0,borderRadius:9,padding:11}}><Plus size={16} style={{verticalAlign:'middle',marginRight:5}}/>Add record</button></form>
 <div style={{display:'grid',gap:10}}>{busy?<p>Loading…</p>:records.length===0?<p>No {section} records yet.</p>:records.map(r=><article key={r.record_id} style={{display:'flex',justifyContent:'space-between',gap:12,padding:14,border:'1px solid #e2e8f0',borderRadius:12}}><div><strong>{r.name}</strong><p>{[r.category,r.quantity!=null?String(r.quantity)+' '+(r.unit||''):'',r.price!=null?'₹'+r.price:'',r.customer,r.notes].filter(Boolean).join(' · ')}</p><small>Status: {r.status||'active'} · {r.created_at?new Date(r.created_at).toLocaleDateString():''}</small></div><button aria-label="Delete record" onClick={()=>remove(r.record_id)}><Trash2 size={16}/></button></article>)}</div></section>;
}
