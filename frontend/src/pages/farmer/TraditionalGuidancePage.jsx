import React from 'react';
import { Scroll, ShieldCheck, Leaf, Layers, Wind, Droplets } from 'lucide-react';

const TRADITIONAL_PRACTICES = [
  {
    title: 'Neem Leaf & Seed Kernel Admixture',
    crop: 'Paddy, Wheat, Millets, Pulses',
    icon: Leaf,
    color: '#10b981',
    description: 'Mixing sun-dried Azadirachta indica (Neem) leaves at 1.5% to 2.0% w/w ratio into dry stored grain. The active limonoid azadirachtin acts as an antifeedant, growth disruptor, and insect repellent against rice weevil and grain moths.',
    steps: [
      'Ensure neem leaves are crisp and completely sun-dried (green leaves introduce moisture).',
      'Mix evenly throughout the grain bulk during bin loading.',
      'Place muslin packets filled with dried neem seed kernel powder in corner pockets.'
    ],
    source: 'ICAR-IIRR Indigenous Technical Knowledge (ITK) & CFTRI Mysore'
  },
  {
    title: 'Vegetable Oil Smearing Against Pulse Beetles',
    crop: 'Chickpea (Chana), Red Gram (Arhar), Green Gram (Moong)',
    icon: Droplets,
    color: '#f59e0b',
    description: 'Coating pulse seeds with edible non-drying oils (mustard, castor, or coconut oil) at 3 to 5 ml per kg seed creates a physical barrier that blocks beetle spiracles and prevents egg hatching of Callosobruchus.',
    steps: [
      'Sun-dry pulses to below 10% moisture before coating.',
      'Smear 3-5 ml of edible vegetable oil per kg of grain until glossy.',
      'Grain remains edible after routine washing and boiling.'
    ],
    source: 'ICAR Indian Institute of Pulses Research (IIPR) Kanpur'
  },
  {
    title: 'Pusa Bin Hermetic Earthen Granary',
    crop: 'Wheat, Maize, Paddy, Millets',
    icon: Layers,
    color: '#60a5fa',
    description: 'An improved earthen kothi developed by IARI using an inner and outer brick wall sandwiching a 700-gauge polyethylene film barrier. Sealed hermetically, grain respiration depletes oxygen to zero, naturally suffocating insects without chemical fumigation.',
    steps: [
      'Construct double brick or mud walls with plastic film embedded continuously.',
      'Ensure grain is below 12% moisture before loading.',
      'Seal the top hatch airtight with mud plaster.'
    ],
    source: 'Indian Agricultural Research Institute (IARI), New Delhi'
  },
  {
    title: 'Ventilated Bamboo Thatched Chawl (Medha System)',
    crop: 'Rabi Onion Bulbs',
    icon: Wind,
    color: '#a855f7',
    description: 'Two-tier bottom-ventilated bamboo structures built on raised platforms 50-60 cm above ground. Natural buoyancy draws cool ground air upward through onion stacks, keeping humidity below 72% and preventing black mold and sprouting.',
    steps: [
      'Orient structure perpendicular to prevailing summer breeze.',
      'Thoroughly field-cure and shade-cure onions for 10-15 days until necks are tight and papery dry.',
      'Limit heap depth to no more than 80 cm.'
    ],
    source: 'ICAR Directorate of Onion and Garlic Research (DOGR), Rajgurunagar'
  },
  {
    title: 'Zero Energy Cool Chamber (ZECC) Evaporative Storage',
    crop: 'Tomatoes, Mangoes, Bananas, Fresh Vegetables',
    icon: Wind,
    color: '#ec4899',
    description: 'An evaporative cooling chamber constructed with double-brick walls filled with wet river sand. Natural evaporation drops internal chamber temperatures by 8-12°C below outdoor ambient and maintains high relative humidity (85-92%) without electricity.',
    steps: [
      'Fill the 7.5 cm cavity between double brick walls with clean river sand.',
      'Saturate sand with clean water twice daily.',
      'Cover top with thatch frame and wet gunny bags.'
    ],
    source: 'ICAR-IARI Horticulture Division'
  }
];

export default function TraditionalGuidancePage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <span className="badge badge-verified">
          <ShieldCheck size={14} /> Traditional Indigenous Agricultural Knowledge (ITK)
        </span>
        <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Traditional Storage Methods & Guidance</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem', maxWidth: '750px' }}>
          Source-backed traditional practices proven across generations in Indian farming communities, validated by ICAR, IARI, and CFTRI post-harvest research.
        </p>
      </div>

      {/* Practices Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {TRADITIONAL_PRACTICES.map((p, idx) => {
          const Icon = p.icon;
          return (
            <div key={idx} className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ background: `${p.color}22`, padding: '12px', borderRadius: '12px' }}>
                  <Icon size={24} color={p.color} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.2rem', color: '#f8fafc' }}>{p.title}</h3>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Applicable Crops: {p.crop}</span>
                </div>
              </div>

              <p style={{ color: '#cbd5e1', fontSize: '0.9rem', lineHeight: 1.6 }}>
                {p.description}
              </p>

              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '10px' }}>
                <strong style={{ fontSize: '0.82rem', color: '#f8fafc', display: 'block', marginBottom: '8px' }}>
                  Execution Guidelines:
                </strong>
                <ul style={{ paddingLeft: '18px', fontSize: '0.84rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {p.steps.map((st, sI) => (
                    <li key={sI}>{st}</li>
                  ))}
                </ul>
              </div>

              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: 'auto', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                Source: {p.source}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
