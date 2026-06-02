import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  IconMenu2,
  IconHeadset,
  IconChevronRight,
  IconInfoCircle,
} from '@tabler/icons-react';

const TAX_ID_TYPES = [
  { value: '', label: 'Select' },
  { value: 'EIN', label: 'EIN (Employer Identification Number)' },
  { value: 'SSN', label: 'SSN (Social Security Number)' },
  { value: 'ITIN', label: 'ITIN (Individual Taxpayer Identification Number)' },
  { value: 'FOREIGN', label: 'Foreign Tax ID' },
];

const TAX_CLASSIFICATIONS = [
  { value: '', label: 'Select' },
  { value: 'individual', label: 'Individual / Sole Proprietor' },
  { value: 'c_corp', label: 'C Corporation' },
  { value: 's_corp', label: 'S Corporation' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'trust', label: 'Trust / Estate' },
  { value: 'llc', label: 'Limited Liability Company (LLC)' },
  { value: 'other', label: 'Other' },
];

const FATCA_STATUSES = [
  { value: '', label: 'Select' },
  { value: 'us_person', label: 'U.S. Person' },
  { value: 'active_nffe', label: 'Active NFFE' },
  { value: 'passive_nffe', label: 'Passive NFFE' },
  { value: 'participating_ffi', label: 'Participating FFI' },
  { value: 'exempt_beneficial_owner', label: 'Exempt Beneficial Owner' },
  { value: 'other', label: 'Other' },
];

const WITHHOLDING_RATES = [
  { value: '0%', label: '0%' },
  { value: '10%', label: '10%' },
  { value: '15%', label: '15%' },
  { value: '20%', label: '20%' },
  { value: '25%', label: '25%' },
  { value: '30%', label: '30% (default)' },
];

const INPUT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-colors';

const SELECT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary appearance-none pr-8 transition-colors';

function Label({ text, required, optional }: { text: string; required?: boolean; optional?: boolean }) {
  return (
    <label className="block text-xs text-text-secondary mb-1.5">
      {text}
      {required && <span className="text-danger ml-0.5">*</span>}
      {optional && <span className="text-text-muted ml-1">(Optional)</span>}
    </label>
  );
}

function SelectInput({ value, onChange, options }: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="relative">
      <select value={value} onChange={e => onChange(e.target.value)} className={SELECT_CLS}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
    </div>
  );
}

export default function TaxFormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(false);

  const [entityName, setEntityName] = useState('');
  const [taxIdType, setTaxIdType] = useState('');
  const [taxIdNumber, setTaxIdNumber] = useState('');
  const [taxClassification, setTaxClassification] = useState('');
  const [countryOfTaxResidency, setCountryOfTaxResidency] = useState('');
  const [fatcaStatus, setFatcaStatus] = useState('');
  const [hasTreaty, setHasTreaty] = useState<boolean | null>(null);
  const [treatyCountry, setTreatyCountry] = useState('');
  const [treatyArticle, setTreatyArticle] = useState('');
  const [withholdingRate, setWithholdingRate] = useState('30%');
  const [certifyAccuracy, setCertifyAccuracy] = useState(false);

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
          <span className="text-text-secondary">Tax Form</span>
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
            <h1 className="text-xl font-bold text-text-primary">Tax Form</h1>
            <p className="text-sm text-text-secondary mt-1">
              Provide tax classification and withholding information for your entity (W-9 / W-8BEN-E).
            </p>
          </div>

          {/* Entity & Tax Identification */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4">Entity & Tax Identification</h2>
            <div className="space-y-4">
              <div>
                <Label text="Entity Legal Name" required />
                <input value={entityName} onChange={e => setEntityName(e.target.value)}
                  placeholder="Enter exact legal name as registered" className={INPUT_CLS} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label text="Tax ID Type" required />
                  <SelectInput value={taxIdType} onChange={setTaxIdType} options={TAX_ID_TYPES} />
                </div>
                <div>
                  <Label text="Tax ID Number" required />
                  <input value={taxIdNumber} onChange={e => setTaxIdNumber(e.target.value)}
                    placeholder={taxIdType === 'EIN' ? 'XX-XXXXXXX' : 'Enter tax ID'}
                    className={INPUT_CLS} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label text="Tax Classification" required />
                  <SelectInput value={taxClassification} onChange={setTaxClassification} options={TAX_CLASSIFICATIONS} />
                </div>
                <div>
                  <Label text="Country of Tax Residency" required />
                  <input value={countryOfTaxResidency} onChange={e => setCountryOfTaxResidency(e.target.value)}
                    placeholder="e.g. United States" className={INPUT_CLS} />
                </div>
              </div>
            </div>
          </div>

          {/* FATCA Status */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <div className="flex items-start gap-2 mb-4">
              <h2 className="text-sm font-semibold text-text-primary">FATCA Classification</h2>
              <IconInfoCircle size={14} className="text-text-muted mt-0.5 flex-shrink-0" />
            </div>
            <div>
              <Label text="FATCA Status" required />
              <SelectInput value={fatcaStatus} onChange={setFatcaStatus} options={FATCA_STATUSES} />
            </div>
          </div>

          {/* Tax Treaty */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4">Tax Treaty Benefits</h2>
            <div className="mb-4">
              <p className="text-sm text-text-primary mb-2">
                Is the entity claiming tax treaty benefits?
                <span className="text-danger ml-0.5">*</span>
              </p>
              <div className="flex gap-3">
                {([true, false] as const).map(v => (
                  <button
                    key={String(v)}
                    type="button"
                    onClick={() => setHasTreaty(v)}
                    className={`px-5 h-9 rounded-lg text-sm font-medium border transition-colors ${
                      hasTreaty === v
                        ? 'bg-primary text-white border-primary'
                        : 'bg-bg-elevated text-text-secondary border-border-default hover:border-primary'
                    }`}
                  >
                    {v ? 'Yes' : 'No'}
                  </button>
                ))}
              </div>
            </div>

            {hasTreaty === true && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <Label text="Treaty Country" required />
                  <input value={treatyCountry} onChange={e => setTreatyCountry(e.target.value)}
                    placeholder="e.g. United Kingdom" className={INPUT_CLS} />
                </div>
                <div>
                  <Label text="Treaty Article / Paragraph" required />
                  <input value={treatyArticle} onChange={e => setTreatyArticle(e.target.value)}
                    placeholder="e.g. Article 11, Para 2" className={INPUT_CLS} />
                </div>
              </div>
            )}
          </div>

          {/* Withholding Rate */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4">Withholding</h2>
            <div>
              <Label text="Applicable Withholding Rate" required />
              <SelectInput value={withholdingRate} onChange={setWithholdingRate} options={WITHHOLDING_RATES} />
              <p className="text-xs text-text-muted mt-1.5">
                Default rate is 30% for non-U.S. entities without a valid treaty exemption.
              </p>
            </div>
          </div>

          {/* Certification */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mb-5">
            <h2 className="text-sm font-semibold text-text-primary mb-3">Certification</h2>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={certifyAccuracy}
                onChange={e => setCertifyAccuracy(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-border-default accent-primary flex-shrink-0"
              />
              <span className="text-sm text-text-secondary leading-relaxed">
                I certify, under penalty of perjury, that the information provided on this form is true,
                correct, and complete, and that I am authorized to sign for the entity named above.
              </span>
            </label>
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
            disabled={!certifyAccuracy}
            onClick={() => navigate(`/client/applications/${caseId}`)}
            className="px-6 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Submit
          </button>
        </div>
      </footer>

    </div>
  );
}
