import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  IconMenu2,
  IconHeadset,
  IconChevronRight,
  IconPlus,
  IconTrash,
} from '@tabler/icons-react';

const CURRENCIES = [
  { value: '', label: 'Select currency' },
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'JPY', label: 'JPY — Japanese Yen' },
  { value: 'CHF', label: 'CHF — Swiss Franc' },
  { value: 'CAD', label: 'CAD — Canadian Dollar' },
  { value: 'AUD', label: 'AUD — Australian Dollar' },
  { value: 'HKD', label: 'HKD — Hong Kong Dollar' },
  { value: 'SGD', label: 'SGD — Singapore Dollar' },
];

const ACCOUNT_TYPES = [
  { value: '', label: 'Select' },
  { value: 'checking', label: 'Checking' },
  { value: 'savings', label: 'Savings' },
  { value: 'custody', label: 'Custody / Brokerage' },
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

interface SSIEntry {
  currency: string;
  accountType: string;
  bankName: string;
  bankAddress: string;
  swiftBic: string;
  abaRoutingNumber: string;
  accountNumber: string;
  accountName: string;
  iban: string;
  hasCorrespondent: boolean | null;
  correspondentBankName: string;
  correspondentSwift: string;
  correspondentAccountNumber: string;
  furtherCreditAccountName: string;
  furtherCreditAccountNumber: string;
}

const EMPTY_SSI: SSIEntry = {
  currency: '', accountType: '',
  bankName: '', bankAddress: '', swiftBic: '', abaRoutingNumber: '',
  accountNumber: '', accountName: '', iban: '',
  hasCorrespondent: null,
  correspondentBankName: '', correspondentSwift: '', correspondentAccountNumber: '',
  furtherCreditAccountName: '', furtherCreditAccountNumber: '',
};

export default function SSIFormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(false);

  const [ssiEntries, setSsiEntries] = useState<SSIEntry[]>([{ ...EMPTY_SSI }]);
  const [certify, setCertify] = useState(false);

  const updateEntry = (i: number, field: keyof SSIEntry, val: string | boolean | null) =>
    setSsiEntries(prev => prev.map((e, idx) => idx === i ? { ...e, [field]: val } : e));

  const addEntry = () => setSsiEntries(prev => [...prev, { ...EMPTY_SSI }]);

  const removeEntry = (i: number) => setSsiEntries(prev => prev.filter((_, idx) => idx !== i));

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
          <span className="text-text-secondary">SSI Form</span>
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
            <h1 className="text-xl font-bold text-text-primary">Standard Settlement Instructions (SSI)</h1>
            <p className="text-sm text-text-secondary mt-1">
              Provide your settlement bank account details for each currency you trade. You can add multiple SSI entries.
            </p>
          </div>

          {/* SSI entries */}
          <div className="space-y-6">
            {ssiEntries.map((entry, i) => (
              <div key={i} className="bg-bg-surface border border-border-default rounded-xl p-6">
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-sm font-semibold text-text-primary">
                    SSI Entry {i + 1}
                  </h2>
                  {ssiEntries.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeEntry(i)}
                      className="flex items-center gap-1 text-xs text-text-muted hover:text-danger transition-colors"
                    >
                      <IconTrash size={13} /> Remove
                    </button>
                  )}
                </div>

                {/* Currency & Account Type */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <Label text="Currency" required />
                    <SelectInput value={entry.currency} onChange={v => updateEntry(i, 'currency', v)} options={CURRENCIES} />
                  </div>
                  <div>
                    <Label text="Account Type" required />
                    <SelectInput value={entry.accountType} onChange={v => updateEntry(i, 'accountType', v)} options={ACCOUNT_TYPES} />
                  </div>
                </div>

                {/* Beneficiary Bank */}
                <div className="border-t border-border-subtle pt-4 mb-4">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                    Beneficiary Bank
                  </p>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label text="Bank Name" required />
                        <input value={entry.bankName} onChange={e => updateEntry(i, 'bankName', e.target.value)}
                          placeholder="e.g. JPMorgan Chase Bank" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="SWIFT / BIC Code" required />
                        <input value={entry.swiftBic} onChange={e => updateEntry(i, 'swiftBic', e.target.value.toUpperCase())}
                          placeholder="e.g. CHASUS33" className={INPUT_CLS} />
                      </div>
                    </div>
                    <div>
                      <Label text="Bank Address" required />
                      <input value={entry.bankAddress} onChange={e => updateEntry(i, 'bankAddress', e.target.value)}
                        placeholder="Full bank address" className={INPUT_CLS} />
                    </div>
                    <div>
                      <Label text="ABA / Routing Number" optional />
                      <input value={entry.abaRoutingNumber} onChange={e => updateEntry(i, 'abaRoutingNumber', e.target.value)}
                        placeholder="For USD domestic transfers" className={INPUT_CLS} />
                    </div>
                  </div>
                </div>

                {/* Beneficiary Account */}
                <div className="border-t border-border-subtle pt-4 mb-4">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                    Beneficiary Account
                  </p>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label text="Account Name / Beneficiary Name" required />
                        <input value={entry.accountName} onChange={e => updateEntry(i, 'accountName', e.target.value)}
                          placeholder="Name on the account" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Account Number" required />
                        <input value={entry.accountNumber} onChange={e => updateEntry(i, 'accountNumber', e.target.value)}
                          placeholder="Bank account number" className={INPUT_CLS} />
                      </div>
                    </div>
                    <div>
                      <Label text="IBAN" optional />
                      <input value={entry.iban} onChange={e => updateEntry(i, 'iban', e.target.value.toUpperCase())}
                        placeholder="For European / international transfers" className={INPUT_CLS} />
                    </div>
                  </div>
                </div>

                {/* Correspondent Bank */}
                <div className="border-t border-border-subtle pt-4">
                  <p className="text-sm text-text-primary mb-2">
                    Is a correspondent / intermediary bank required?
                    <span className="text-danger ml-0.5">*</span>
                  </p>
                  <div className="flex gap-3">
                    {([true, false] as const).map(v => (
                      <button
                        key={String(v)}
                        type="button"
                        onClick={() => updateEntry(i, 'hasCorrespondent', v)}
                        className={`px-5 h-9 rounded-lg text-sm font-medium border transition-colors ${
                          entry.hasCorrespondent === v
                            ? 'bg-primary text-white border-primary'
                            : 'bg-bg-elevated text-text-secondary border-border-default hover:border-primary'
                        }`}
                      >
                        {v ? 'Yes' : 'No'}
                      </button>
                    ))}
                  </div>

                  {entry.hasCorrespondent === true && (
                    <div className="grid grid-cols-3 gap-4 mt-4">
                      <div>
                        <Label text="Correspondent Bank Name" required />
                        <input value={entry.correspondentBankName}
                          onChange={e => updateEntry(i, 'correspondentBankName', e.target.value)}
                          placeholder="Bank name" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Correspondent SWIFT" required />
                        <input value={entry.correspondentSwift}
                          onChange={e => updateEntry(i, 'correspondentSwift', e.target.value.toUpperCase())}
                          placeholder="SWIFT / BIC" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Correspondent Account #" required />
                        <input value={entry.correspondentAccountNumber}
                          onChange={e => updateEntry(i, 'correspondentAccountNumber', e.target.value)}
                          placeholder="Account number" className={INPUT_CLS} />
                      </div>
                    </div>
                  )}
                </div>

                {/* Further Credit */}
                <div className="border-t border-border-subtle pt-4 mt-4">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                    For Further Credit (FFC) <span className="normal-case text-text-muted font-normal">(Optional)</span>
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label text="FFC Account Name" />
                      <input value={entry.furtherCreditAccountName}
                        onChange={e => updateEntry(i, 'furtherCreditAccountName', e.target.value)}
                        placeholder="Account name" className={INPUT_CLS} />
                    </div>
                    <div>
                      <Label text="FFC Account Number" />
                      <input value={entry.furtherCreditAccountNumber}
                        onChange={e => updateEntry(i, 'furtherCreditAccountNumber', e.target.value)}
                        placeholder="Account number" className={INPUT_CLS} />
                    </div>
                  </div>
                </div>

              </div>
            ))}
          </div>

          {/* Add SSI button */}
          <button
            type="button"
            onClick={addEntry}
            className="mt-4 flex items-center gap-2 px-4 h-9 rounded-lg border border-dashed border-border-default text-sm text-text-secondary hover:text-primary hover:border-primary transition-colors w-full justify-center"
          >
            <IconPlus size={15} /> Add another SSI entry
          </button>

          {/* Certification */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-6 mt-5">
            <h2 className="text-sm font-semibold text-text-primary mb-3">Certification</h2>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={certify}
                onChange={e => setCertify(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded border-border-default accent-primary flex-shrink-0"
              />
              <span className="text-sm text-text-secondary leading-relaxed">
                I confirm that the settlement instructions provided above are accurate and authorized
                by the entity. I understand that ClearStreet will use these instructions for all
                applicable settlement transactions.
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
            disabled={!certify}
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
