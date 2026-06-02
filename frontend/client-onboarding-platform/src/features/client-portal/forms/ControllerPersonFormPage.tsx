import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  IconMenu2,
  IconHeadset,
  IconChevronRight,
  IconPlus,
  IconTrash,
} from '@tabler/icons-react';

const ID_DOCUMENT_TYPES = [
  { value: '', label: 'Select' },
  { value: 'Passport', label: 'Passport' },
  { value: 'National ID', label: 'National ID / Driver\'s License' },
  { value: 'Residence Permit', label: 'Residence Permit' },
  { value: 'Other', label: 'Other Government-Issued ID' },
];

const INPUT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-colors';

const SELECT_CLS =
  'w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary appearance-none pr-8 transition-colors';

interface ControllerPerson {
  fullName: string;
  title: string;
  ownershipPercentage: string;
  dateOfBirth: string;
  nationality: string;
  idDocumentType: string;
  idDocumentNumber: string;
  idExpiryDate: string;
}

const EMPTY_PERSON: ControllerPerson = {
  fullName: '', title: '', ownershipPercentage: '',
  dateOfBirth: '', nationality: '',
  idDocumentType: '', idDocumentNumber: '', idExpiryDate: '',
};

function Label({ text, required, optional }: { text: string; required?: boolean; optional?: boolean }) {
  return (
    <label className="block text-xs text-text-secondary mb-1.5">
      {text}
      {required && <span className="text-danger ml-0.5">*</span>}
      {optional && <span className="text-text-muted ml-1">(Optional)</span>}
    </label>
  );
}

export default function ControllerPersonFormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(false);

  const [persons, setPersons] = useState<ControllerPerson[]>([{ ...EMPTY_PERSON }]);
  const [certify, setCertify] = useState(false);

  const updatePerson = (i: number, field: keyof ControllerPerson, val: string) =>
    setPersons(prev => prev.map((p, idx) => idx === i ? { ...p, [field]: val } : p));

  const addPerson = () => setPersons(prev => [...prev, { ...EMPTY_PERSON }]);

  const removePerson = (i: number) => setPersons(prev => prev.filter((_, idx) => idx !== i));

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
          <span className="text-text-secondary">Controller Person Form</span>
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
            <h1 className="text-xl font-bold text-text-primary">Controller Person Form</h1>
            <p className="text-sm text-text-secondary mt-1">
              List all individuals who have significant control over the entity — typically anyone
              with ownership of 25% or more, or who exercises significant influence or control.
            </p>
          </div>

          {/* Info banner */}
          <div className="mb-5 flex items-start gap-3 px-4 py-3 rounded-lg bg-primary-subtle border border-primary/20">
            <div className="flex-1 text-xs text-text-secondary leading-relaxed">
              <span className="font-semibold text-text-primary">Who should be listed? </span>
              Include any individual who owns ≥ 25% of the entity, is a senior managing official,
              or exercises control over the entity's operations regardless of ownership percentage.
            </div>
          </div>

          {/* Controller persons */}
          <div className="space-y-5">
            {persons.map((person, i) => (
              <div key={i} className="bg-bg-surface border border-border-default rounded-xl p-6">
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-sm font-semibold text-text-primary">
                    Controller Person {i + 1}
                  </h2>
                  {persons.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePerson(i)}
                      className="flex items-center gap-1 text-xs text-text-muted hover:text-danger transition-colors"
                    >
                      <IconTrash size={13} /> Remove
                    </button>
                  )}
                </div>

                {/* Personal info */}
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label text="Full Legal Name" required />
                      <input value={person.fullName} onChange={e => updatePerson(i, 'fullName', e.target.value)}
                        placeholder="As it appears on ID" className={INPUT_CLS} />
                    </div>
                    <div>
                      <Label text="Title / Role" required />
                      <input value={person.title} onChange={e => updatePerson(i, 'title', e.target.value)}
                        placeholder="e.g. Managing Director, General Partner" className={INPUT_CLS} />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label text="Ownership %" optional />
                      <input
                        type="number" min="0" max="100"
                        value={person.ownershipPercentage}
                        onChange={e => updatePerson(i, 'ownershipPercentage', e.target.value)}
                        placeholder="e.g. 25" className={INPUT_CLS}
                      />
                    </div>
                    <div>
                      <Label text="Date of Birth" required />
                      <input type="date" value={person.dateOfBirth}
                        onChange={e => updatePerson(i, 'dateOfBirth', e.target.value)}
                        className={INPUT_CLS} />
                    </div>
                    <div>
                      <Label text="Nationality" required />
                      <input value={person.nationality} onChange={e => updatePerson(i, 'nationality', e.target.value)}
                        placeholder="e.g. US, UK" className={INPUT_CLS} />
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-border-subtle pt-4">
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">
                      Identity Document
                    </p>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <Label text="Document Type" required />
                        <div className="relative">
                          <select
                            value={person.idDocumentType}
                            onChange={e => updatePerson(i, 'idDocumentType', e.target.value)}
                            className={SELECT_CLS}
                          >
                            {ID_DOCUMENT_TYPES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
                        </div>
                      </div>
                      <div>
                        <Label text="Document Number" required />
                        <input value={person.idDocumentNumber}
                          onChange={e => updatePerson(i, 'idDocumentNumber', e.target.value)}
                          placeholder="Enter document number" className={INPUT_CLS} />
                      </div>
                      <div>
                        <Label text="Expiry Date" optional />
                        <input type="date" value={person.idExpiryDate}
                          onChange={e => updatePerson(i, 'idExpiryDate', e.target.value)}
                          className={INPUT_CLS} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Add person button */}
          <button
            type="button"
            onClick={addPerson}
            className="mt-4 flex items-center gap-2 px-4 h-9 rounded-lg border border-dashed border-border-default text-sm text-text-secondary hover:text-primary hover:border-primary transition-colors w-full justify-center"
          >
            <IconPlus size={15} /> Add another controller person
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
                I certify that the information provided above is accurate and complete to the best of
                my knowledge, and that I am authorized to submit this form on behalf of the entity.
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
