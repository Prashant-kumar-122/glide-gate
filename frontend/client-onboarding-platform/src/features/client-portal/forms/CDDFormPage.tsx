import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  IconMenu2,
  IconHeadset,
  IconChevronRight,
  IconPlus,
  IconTrash,
} from '@tabler/icons-react';

const JURISDICTIONS = [
  'United States', 'United Kingdom', 'European Union', 'Cayman Islands',
  'Singapore', 'Hong Kong', 'Japan', 'Canada', 'Australia', 'Switzerland',
];

const SOURCE_OPTIONS = [
  { value: '', label: 'Select' },
  { value: 'investment_returns', label: 'Investment Returns' },
  { value: 'capital_raise', label: 'Capital Raise' },
  { value: 'business_revenue', label: 'Business Revenue' },
  { value: 'asset_sale', label: 'Asset Sale' },
  { value: 'inheritance', label: 'Inheritance' },
  { value: 'other', label: 'Other' },
];

const VOLUME_OPTIONS = [
  { value: '', label: 'Select' },
  { value: 'under_1m', label: 'Under $1M annually' },
  { value: '1m_10m', label: '$1M – $10M annually' },
  { value: '10m_50m', label: '$10M – $50M annually' },
  { value: '50m_100m', label: '$50M – $100M annually' },
  { value: 'over_100m', label: 'Over $100M annually' },
];

interface BeneficialOwner { name: string; ownership: string; nationality: string }

const INPUT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-colors';

const SELECT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary appearance-none pr-8 transition-colors';

function Label({ text, required }: { text: string; required?: boolean }) {
  return (
    <label className="block text-xs text-text-secondary mb-1.5">
      {text}{required && <span className="text-danger ml-0.5">*</span>}
    </label>
  );
}

function YesNo({ value, onChange }: { value: boolean | null; onChange: (v: boolean) => void }) {
  return (
    <div className="flex gap-3 mt-2">
      {([true, false] as const).map(v => (
        <button
          key={String(v)}
          type="button"
          onClick={() => onChange(v)}
          className={`px-5 h-9 rounded-lg text-sm font-medium border transition-colors ${
            value === v
              ? 'bg-primary text-white border-primary'
              : 'bg-bg-elevated text-text-secondary border-border-default hover:border-primary'
          }`}
        >
          {v ? 'Yes' : 'No'}
        </button>
      ))}
    </div>
  );
}

export default function CDDFormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(false);

  const [natureOfBusiness, setNatureOfBusiness] = useState('');
  const [sourceOfFunds, setSourceOfFunds] = useState('');
  const [otherSource, setOtherSource] = useState('');
  const [tradingVolume, setTradingVolume] = useState('');
  const [jurisdictions, setJurisdictions] = useState<string[]>([]);
  const [pepStatus, setPepStatus] = useState<boolean | null>(null);
  const [sanctionsStatus, setSanctionsStatus] = useState<boolean | null>(null);
  const [hasBeneficialOwners, setHasBeneficialOwners] = useState<boolean | null>(null);
  const [owners, setOwners] = useState<BeneficialOwner[]>([{ name: '', ownership: '', nationality: '' }]);

  const toggleJurisdiction = (j: string) =>
    setJurisdictions(prev => prev.includes(j) ? prev.filter(x => x !== j) : [...prev, j]);

  const updateOwner = (i: number, field: keyof BeneficialOwner, val: string) =>
    setOwners(prev => prev.map((o, idx) => idx === i ? { ...o, [field]: val } : o));

  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">

      {/* Header */}
      <header className="flex-shrink-0 h-14 bg-bg-surface border-b border-border-default flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-3">
          <button className="text-text-muted hover:text-text-primary transition-colors">
            <IconMenu2 size={20} />
          </button>
          <span className="text-sm font-semibold text-text-primary">Client Enrollment Portal</span>
        </div>
        <button className="flex items-center gap-2 px-4 h-8 rounded-lg border border-primary text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">
          <IconHeadset size={14} /> Contact us
        </button>
      </header>

      {/* Sub-header */}
      <div className="h-11 bg-bg-surface border-b border-border-default flex items-center gap-4 px-6 flex-shrink-0">
        <span className="text-sm font-bold text-text-primary whitespace-nowrap">AIB Investments Pvt. Ltd.</span>
        <nav className="flex items-center gap-1.5 text-xs">
          <Link to="/client/dashboard" className="text-primary hover:underline">Home</Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <Link to={`/client/applications/${caseId}`} className="text-primary hover:underline">IB Application</Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <Link to={`/client/applications/${caseId}`} className="text-primary hover:underline">{caseId}</Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <span className="text-text-secondary">Customer Due Diligence (CDD)</span>
        </nav>
      </div>

      {/* Body */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto py-10 px-8 pb-28">

          {saved && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-success/10 border border-success/20 text-sm text-success font-medium">
              Changes saved successfully.
            </div>
          )}

          <div className="mb-7">
            <h1 className="text-xl font-bold text-text-primary">Customer Due Diligence (CDD)</h1>
            <p className="text-sm text-text-secondary mt-1">
              Provide information about your business activities and risk profile.
            </p>
          </div>

          {/* Business Information */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4">Business Information</h2>
            <div className="space-y-4">
              <div>
                <Label text="Nature of Business" required />
                <textarea
                  rows={3}
                  value={natureOfBusiness}
                  onChange={e => setNatureOfBusiness(e.target.value)}
                  placeholder="Describe the primary business activities of the entity…"
                  className="w-full px-3 py-2.5 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 resize-none transition-colors"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label text="Source of Funds" required />
                  <div className="relative">
                    <select value={sourceOfFunds} onChange={e => setSourceOfFunds(e.target.value)} className={SELECT_CLS}>
                      {SOURCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
                  </div>
                </div>
                {sourceOfFunds === 'other' ? (
                  <div>
                    <Label text="Please specify" />
                    <input value={otherSource} onChange={e => setOtherSource(e.target.value)}
                      placeholder="Describe source of funds" className={INPUT_CLS} />
                  </div>
                ) : (
                  <div>
                    <Label text="Expected Annual Trading Volume" required />
                    <div className="relative">
                      <select value={tradingVolume} onChange={e => setTradingVolume(e.target.value)} className={SELECT_CLS}>
                        {VOLUME_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
                    </div>
                  </div>
                )}
              </div>
              {sourceOfFunds === 'other' && (
                <div>
                  <Label text="Expected Annual Trading Volume" required />
                  <div className="relative">
                    <select value={tradingVolume} onChange={e => setTradingVolume(e.target.value)} className={SELECT_CLS}>
                      {VOLUME_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Operating Jurisdictions */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-1">
              Operating Jurisdictions <span className="text-danger">*</span>
            </h2>
            <p className="text-xs text-text-muted mb-4">
              Select all jurisdictions where the entity operates or has customers.
            </p>
            <div className="flex flex-wrap gap-2">
              {JURISDICTIONS.map(j => (
                <button
                  key={j}
                  type="button"
                  onClick={() => toggleJurisdiction(j)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    jurisdictions.includes(j)
                      ? 'bg-primary text-white border-primary'
                      : 'bg-bg-elevated text-text-secondary border-border-default hover:border-primary hover:text-primary'
                  }`}
                >
                  {j}
                </button>
              ))}
            </div>
          </div>

          {/* Risk & Compliance */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-5">Risk & Compliance</h2>
            <div className="space-y-6">
              <div>
                <p className="text-sm text-text-primary">
                  Is any director, officer, or beneficial owner a Politically Exposed Person (PEP)?
                  <span className="text-danger ml-0.5">*</span>
                </p>
                <YesNo value={pepStatus} onChange={setPepStatus} />
              </div>
              <div>
                <p className="text-sm text-text-primary">
                  Is the entity subject to any sanctions or embargo restrictions?
                  <span className="text-danger ml-0.5">*</span>
                </p>
                <YesNo value={sanctionsStatus} onChange={setSanctionsStatus} />
              </div>
            </div>
          </div>

          {/* Beneficial Ownership */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-1">Beneficial Ownership</h2>
            <p className="text-xs text-text-muted mb-4">
              Identify all individuals who directly or indirectly own 25% or more of the entity.
            </p>
            <div>
              <p className="text-sm text-text-primary">
                Does the entity have any beneficial owners with ≥ 25% ownership?
                <span className="text-danger ml-0.5">*</span>
              </p>
              <YesNo value={hasBeneficialOwners} onChange={setHasBeneficialOwners} />
            </div>

            {hasBeneficialOwners === true && (
              <div className="space-y-4 mt-5">
                {owners.map((owner, i) => (
                  <div key={i} className="border border-border-subtle rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                        Beneficial Owner {i + 1}
                      </span>
                      {owners.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setOwners(prev => prev.filter((_, idx) => idx !== i))}
                          className="text-text-muted hover:text-danger transition-colors"
                        >
                          <IconTrash size={14} />
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label text="Full Name" />
                        <input value={owner.name} onChange={e => updateOwner(i, 'name', e.target.value)}
                          placeholder="Enter full name" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Ownership %" />
                        <input type="number" min="25" max="100" value={owner.ownership}
                          onChange={e => updateOwner(i, 'ownership', e.target.value)}
                          placeholder="e.g. 25" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Nationality" />
                        <input value={owner.nationality} onChange={e => updateOwner(i, 'nationality', e.target.value)}
                          placeholder="e.g. US" className={INPUT_CLS} />
                      </div>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setOwners(prev => [...prev, { name: '', ownership: '', nationality: '' }])}
                  className="flex items-center gap-1.5 text-xs text-primary hover:text-primary-hover font-medium transition-colors"
                >
                  <IconPlus size={13} /> Add another beneficial owner
                </button>
              </div>
            )}
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 h-16 bg-bg-surface border-t border-border-default flex items-center justify-end px-10 z-20">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => { setSaved(true); setTimeout(() => setSaved(false), 3000); }}
            className="px-5 h-9 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-primary transition-colors"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => navigate(`/client/applications/${caseId}`)}
            className="px-6 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold transition-colors"
          >
            Submit
          </button>
        </div>
      </footer>

    </div>
  );
}
