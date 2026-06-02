import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TextInput, Select, Checkbox } from '@mantine/core';
import {
  IconCheck,
  IconLoader2,
  IconArrowLeft,
  IconArrowRight,
  IconX,
  IconPlus,
  IconSparkles,
} from '@tabler/icons-react';
import { casesService } from '../../../mocks/services/cases.service';
import { useAuth } from '../../../store/AuthContext';
import { StepIndicator } from '../../../components/common/StepIndicator';
import { FileUploadZone } from '../../../components/common/FileUploadZone';
import { PRODUCT_LABELS } from '../../../types';
import type {
  ProductType,
  EnrollmentFormData,
  CDDFormData,
  ControlPerson,
  Case,
} from '../../../types';
import { extractDataFromFile } from '../../../utils/mockExtractor';

// ── Constants ──────────────────────────────────────────────────────────────────

const WIZARD_STEPS = [
  'Select Products',
  'Upload Documents',
  'Review Extracted Data',
  'Complete Forms',
  'Submit',
];

const ALL_PRODUCTS: ProductType[] = ['PB', 'DvP', 'IB_CASH', 'FCM', 'RETIREMENT', 'RETAIL'];

const PRODUCT_DESCRIPTIONS: Record<ProductType, string> = {
  PB: 'Leverage our prime brokerage services for equity, fixed income, and multi-asset strategies.',
  DvP: 'Settle transactions securely with simultaneous delivery and payment.',
  IB_CASH: 'Access institutional-grade cash management and money market solutions.',
  FCM: 'Trade futures and derivatives with a leading futures commission merchant.',
  RETIREMENT: 'Tax-advantaged retirement account solutions for individuals and entities.',
  RETAIL: 'Active retail trading account with access to equities, ETFs, and options.',
};

// ── Step 0: Product Selection ──────────────────────────────────────────────────

function ProductCard({
  product,
  selected,
  onToggle,
}: {
  product: ProductType;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={[
        'text-left p-4 rounded-lg border-2 transition-all duration-150',
        selected
          ? 'border-primary bg-primary-subtle ring-2 ring-primary/20'
          : 'border-border-default bg-bg-surface hover:border-primary/50 hover:bg-bg-elevated',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-sm font-semibold text-text-primary">
          {PRODUCT_LABELS[product]}
        </span>
        <div
          className={[
            'w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors',
            selected ? 'border-primary bg-primary' : 'border-border-default bg-bg-elevated',
          ].join(' ')}
        >
          {selected && <IconCheck size={10} className="text-white" strokeWidth={3} />}
        </div>
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">
        {PRODUCT_DESCRIPTIONS[product]}
      </p>
      <div className="mt-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono text-text-muted bg-bg-elevated">
          {product}
        </span>
      </div>
    </button>
  );
}

// ── Step 2: Extracted data preview ────────────────────────────────────────────

function ExtractedDataPreview({ data }: { data: Record<string, string> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted text-sm">
        No data extracted. You can fill in the forms manually in the next step.
      </div>
    );
  }
  return (
    <div className="bg-bg-elevated rounded-lg p-4 space-y-2">
      <p className="text-xs text-text-muted mb-3">
        This data will be used to pre-fill your forms.
      </p>
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-start gap-3">
          <span className="text-xs text-text-muted w-44 flex-shrink-0 font-mono pt-0.5">
            {key.replace(/\./g, ' › ').replace(/([A-Z])/g, ' $1').trim()}
          </span>
          <span className="text-sm text-text-primary flex-1">{value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Step 3: Forms ─────────────────────────────────────────────────────────────

function EnrollmentTab({
  data,
  onChange,
}: {
  data: Partial<EnrollmentFormData>;
  onChange: (d: Partial<EnrollmentFormData>) => void;
}) {
  const set = (key: string, value: string) => {
    if (key.startsWith('address.')) {
      const field = key.split('.')[1];
      onChange({ ...data, address: { ...data.address, [field]: value } as EnrollmentFormData['address'] });
    } else if (key.startsWith('primaryContact.')) {
      const field = key.split('.')[1];
      onChange({ ...data, primaryContact: { ...data.primaryContact, [field]: value } as EnrollmentFormData['primaryContact'] });
    } else {
      onChange({ ...data, [key]: value });
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <TextInput
          label="Legal Name"
          placeholder="Acme Capital LLC"
          value={data.legalName ?? ''}
          onChange={e => set('legalName', e.target.value)}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
        <TextInput
          label="Tax ID / EIN"
          placeholder="00-0000000"
          value={data.taxId ?? ''}
          onChange={e => set('taxId', e.target.value)}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
        <TextInput
          label="Incorporation Date"
          placeholder="YYYY-MM-DD"
          value={data.incorporationDate ?? ''}
          onChange={e => set('incorporationDate', e.target.value)}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
        <TextInput
          label="Incorporation State"
          placeholder="Delaware"
          value={data.incorporationState ?? ''}
          onChange={e => set('incorporationState', e.target.value)}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
        <TextInput
          label="Business Type"
          placeholder="Limited Liability Company"
          value={data.businessType ?? ''}
          onChange={e => set('businessType', e.target.value)}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
      </div>

      <div className="border-t border-border-default pt-4">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Address</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <TextInput
              label="Address Line 1"
              placeholder="200 Park Avenue"
              value={data.address?.line1 ?? ''}
              onChange={e => set('address.line1', e.target.value)}
              classNames={{ label: 'text-text-secondary text-sm' }}
            />
          </div>
          <TextInput
            label="City"
            placeholder="New York"
            value={data.address?.city ?? ''}
            onChange={e => set('address.city', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="State"
            placeholder="NY"
            value={data.address?.state ?? ''}
            onChange={e => set('address.state', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="ZIP Code"
            placeholder="10166"
            value={data.address?.zip ?? ''}
            onChange={e => set('address.zip', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="Country"
            placeholder="United States"
            value={data.address?.country ?? ''}
            onChange={e => set('address.country', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
        </div>
      </div>

      <div className="border-t border-border-default pt-4">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Primary Contact</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TextInput
            label="Full Name"
            placeholder="Jordan Lee"
            value={data.primaryContact?.fullName ?? ''}
            onChange={e => set('primaryContact.fullName', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="Title"
            placeholder="Chief Financial Officer"
            value={data.primaryContact?.title ?? ''}
            onChange={e => set('primaryContact.title', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="Email"
            placeholder="jordan@acme.com"
            value={data.primaryContact?.email ?? ''}
            onChange={e => set('primaryContact.email', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
          <TextInput
            label="Phone"
            placeholder="+1 212 555 0100"
            value={data.primaryContact?.phone ?? ''}
            onChange={e => set('primaryContact.phone', e.target.value)}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
        </div>
      </div>
    </div>
  );
}

function CDDTab({
  data,
  onChange,
}: {
  data: Partial<CDDFormData>;
  onChange: (d: Partial<CDDFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <TextInput
            label="Nature of Business"
            placeholder="Describe your primary business activities"
            value={data.natureOfBusiness ?? ''}
            onChange={e => onChange({ ...data, natureOfBusiness: e.target.value })}
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
        </div>

        <Select
          label="Source of Funds"
          placeholder="Select source"
          data={[
            { value: 'Revenue', label: 'Business Revenue' },
            { value: 'Investment', label: 'Investment Returns' },
            { value: 'Capital Raise', label: 'Capital Raise' },
          ]}
          value={data.sourceOfFunds ?? null}
          onChange={v => onChange({ ...data, sourceOfFunds: v ?? '' })}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />

        <Select
          label="Expected Trading Volume"
          placeholder="Select range"
          data={[
            { value: 'Under $1M', label: 'Under $1M/month' },
            { value: '$1M–$10M', label: '$1M – $10M/month' },
            { value: '$10M–$100M', label: '$10M – $100M/month' },
            { value: 'Over $100M', label: 'Over $100M/month' },
          ]}
          value={data.expectedTradingVolume ?? null}
          onChange={v => onChange({ ...data, expectedTradingVolume: v ?? '' })}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />

        <div className="sm:col-span-2">
          <TextInput
            label="Operating Jurisdictions (comma-separated)"
            placeholder="United States, United Kingdom, Singapore"
            value={data.jurisdictions?.join(', ') ?? ''}
            onChange={e =>
              onChange({
                ...data,
                jurisdictions: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
              })
            }
            classNames={{ label: 'text-text-secondary text-sm' }}
          />
        </div>
      </div>

      <div className="border-t border-border-default pt-4 space-y-3">
        <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
          Compliance Declarations
        </p>
        <Checkbox
          label="Entity or its principals are or have been a Politically Exposed Person (PEP)"
          checked={data.pepStatus ?? false}
          onChange={e => onChange({ ...data, pepStatus: e.target.checked })}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
        <Checkbox
          label="Entity or its principals appear on a sanctions screening list"
          checked={data.sanctionsStatus ?? false}
          onChange={e => onChange({ ...data, sanctionsStatus: e.target.checked })}
          classNames={{ label: 'text-text-secondary text-sm' }}
        />
      </div>
    </div>
  );
}

function ControlPersonsTab({
  persons,
  onChange,
}: {
  persons: ControlPerson[];
  onChange: (p: ControlPerson[]) => void;
}) {
  const blank = (): ControlPerson => ({
    fullName: '',
    title: '',
    ownershipPercentage: 0,
    dateOfBirth: '',
    nationality: '',
    idDocumentType: 'Passport',
    idDocumentNumber: '',
  });

  const update = (i: number, field: keyof ControlPerson, value: string | number) => {
    const updated = persons.map((p, idx) => (idx === i ? { ...p, [field]: value } : p));
    onChange(updated);
  };

  return (
    <div className="space-y-4">
      {persons.map((person, i) => (
        <div key={i} className="bg-bg-elevated rounded-lg p-4 border border-border-default">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-text-primary">Control Person {i + 1}</p>
            <button
              type="button"
              onClick={() => onChange(persons.filter((_, idx) => idx !== i))}
              className="flex items-center justify-center w-7 h-7 rounded text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
            >
              <IconX size={14} />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <TextInput
              label="Full Name"
              value={person.fullName}
              onChange={e => update(i, 'fullName', e.target.value)}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <TextInput
              label="Title"
              value={person.title}
              onChange={e => update(i, 'title', e.target.value)}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <TextInput
              label="Ownership %"
              type="number"
              value={String(person.ownershipPercentage)}
              onChange={e => update(i, 'ownershipPercentage', parseFloat(e.target.value) || 0)}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <TextInput
              label="Date of Birth"
              placeholder="YYYY-MM-DD"
              value={person.dateOfBirth}
              onChange={e => update(i, 'dateOfBirth', e.target.value)}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <TextInput
              label="Nationality"
              value={person.nationality}
              onChange={e => update(i, 'nationality', e.target.value)}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <Select
              label="ID Document Type"
              data={['Passport', 'National ID', 'Driver License']}
              value={person.idDocumentType}
              onChange={v => update(i, 'idDocumentType', v ?? 'Passport')}
              classNames={{ label: 'text-text-secondary text-xs' }}
            />
            <div className="sm:col-span-2">
              <TextInput
                label="ID Document Number"
                value={person.idDocumentNumber}
                onChange={e => update(i, 'idDocumentNumber', e.target.value)}
                classNames={{ label: 'text-text-secondary text-xs' }}
              />
            </div>
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={() => onChange([...persons, blank()])}
        className="flex items-center gap-2 px-4 h-9 rounded-lg border border-dashed border-border-default text-text-secondary hover:text-text-primary hover:border-primary hover:bg-primary-subtle text-sm transition-colors"
      >
        <IconPlus size={14} />
        Add Control Person
      </button>
    </div>
  );
}

// ── Step 4: Submit summary ─────────────────────────────────────────────────────

function SubmitStep({
  selectedProducts,
  enrollmentData,
  cddData,
  controlPersons,
  onSubmit,
  isSubmitting,
  submittedCases,
}: {
  selectedProducts: ProductType[];
  enrollmentData: Partial<EnrollmentFormData>;
  cddData: Partial<CDDFormData>;
  controlPersons: ControlPerson[];
  onSubmit: () => void;
  isSubmitting: boolean;
  submittedCases: Case[];
}) {
  const navigate = useNavigate();

  const hasEnrollment     = !!enrollmentData.legalName;
  const hasCDD            = !!cddData.natureOfBusiness;
  const hasControlPersons = controlPersons.length > 0;
  const count             = selectedProducts.length;

  // ── Success ──────────────────────────────────────────────────────────────────
  if (submittedCases.length > 0) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center flex-shrink-0">
            <IconCheck size={26} className="text-success" strokeWidth={2} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text-primary">
              {submittedCases.length === 1
                ? 'Application Submitted!'
                : `${submittedCases.length} Applications Submitted!`}
            </h3>
            <p className="text-sm text-text-secondary mt-0.5">
              {submittedCases.length === 1
                ? 'Your application has been submitted for review.'
                : 'Each account has its own case and can be tracked and completed independently.'}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {submittedCases.map(c => (
            <div
              key={c.id}
              className="flex items-center justify-between gap-3 px-4 py-3.5 rounded-lg bg-bg-elevated border border-border-default"
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-text-primary">
                  {c.products.map(p => PRODUCT_LABELS[p]).join(', ')}
                </p>
                <p className="text-xs font-mono text-text-muted mt-0.5">{c.id}</p>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/client/applications/${c.id}`)}
                className="flex items-center gap-1.5 px-3 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors flex-shrink-0"
              >
                View <IconArrowRight size={12} />
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate('/client/dashboard')}
          className="w-full h-9 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-primary transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  // ── Review before submit ──────────────────────────────────────────────────────
  return (
    <div className="space-y-5">
      {/* Info banner */}
      <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-primary-subtle border border-primary/20">
        <IconSparkles size={15} className="text-primary flex-shrink-0 mt-0.5" />
        <p className="text-sm text-text-secondary leading-relaxed">
          {count === 1
            ? 'Your entity information will be attached to the new account.'
            : <>
                <span className="text-primary font-semibold">{count} separate cases</span> will be
                created — one per product. Your entity information, forms, and documents are
                shared across all of them so you won't need to re-enter anything.
              </>
          }
        </p>
      </div>

      {/* Per-product cards */}
      <div className="space-y-2">
        {selectedProducts.map((p, i) => (
          <div key={p} className="rounded-lg border border-border-default overflow-hidden">
            {/* Card header */}
            <div className="flex items-center justify-between px-4 py-3 bg-bg-elevated">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-text-primary">{PRODUCT_LABELS[p]}</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-medium">
                  <IconPlus size={9} /> New Case
                </span>
              </div>
              {i > 0 && (
                <span className="text-xs text-success font-medium flex items-center gap-1">
                  <IconCheck size={11} strokeWidth={2.5} /> Reusing shared data
                </span>
              )}
            </div>

            {/* Shared items */}
            <div className="px-4 py-3 space-y-1.5">
              {hasEnrollment ? (
                <SharedRow label="Enrollment Form" note={i === 0 ? 'from this application' : 'reused'} />
              ) : (
                <PendingRow label="Enrollment Form" />
              )}
              {hasCDD ? (
                <SharedRow label="CDD Form" note={i === 0 ? 'from this application' : 'reused'} />
              ) : (
                <PendingRow label="CDD Form" />
              )}
              {hasControlPersons ? (
                <SharedRow label={`Control Persons (${controlPersons.length})`} note={i === 0 ? 'from this application' : 'reused'} />
              ) : (
                <PendingRow label="Control Persons" />
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-text-muted">
        By submitting, you confirm that all information provided is accurate to the best of your knowledge.
      </p>

      <button
        type="button"
        onClick={onSubmit}
        disabled={isSubmitting}
        className="flex items-center justify-center gap-2 w-full h-10 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
      >
        {isSubmitting && <IconLoader2 size={16} className="animate-spin" />}
        {isSubmitting
          ? 'Submitting…'
          : count === 1
            ? 'Submit Application'
            : `Submit ${count} Applications`}
      </button>
    </div>
  );
}

function SharedRow({ label, note }: { label: string; note: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-text-secondary">
      <IconCheck size={11} className="text-success flex-shrink-0" strokeWidth={2.5} />
      <span>{label}</span>
      <span className="text-text-muted">— {note}</span>
    </div>
  );
}

function PendingRow({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-text-muted">
      <span className="w-[11px] h-[11px] rounded-full border border-border-default flex-shrink-0" />
      <span>{label}</span>
      <span className="text-warning/80">— to be completed</span>
    </div>
  );
}

// ── Main wizard ────────────────────────────────────────────────────────────────

export default function OpenNewAccountPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedProducts, setSelectedProducts] = useState<ProductType[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [extractedData, setExtractedData] = useState<Record<string, string>>({});
  const [isExtracting, setIsExtracting] = useState(false);
  const [activeFormTab, setActiveFormTab] = useState<'enrollment' | 'cdd' | 'control'>('enrollment');
  const [submittedCases, setSubmittedCases] = useState<Case[]>([]);

  const [enrollmentForm, setEnrollmentForm] = useState<Partial<EnrollmentFormData>>({});
  const [cddForm, setCddForm] = useState<Partial<CDDFormData>>({});
  const [controlPersons, setControlPersons] = useState<ControlPerson[]>([]);

  const [stepError, setStepError] = useState('');

  const submitMutation = useMutation({
    mutationFn: () =>
      casesService.submitMultipleCases({
        clientId:       user!.id,
        clientName:     user!.fullName,
        products:       selectedProducts,
        enrollmentData: enrollmentForm,
        cddData:        cddForm,
        controlPersons,
      }),
    onSuccess: created => {
      queryClient.invalidateQueries({ queryKey: ['cases', 'client', user?.id] });
      setSubmittedCases(created);
    },
  });

  const applyExtractedData = (data: Record<string, string>) => {
    const enrollment: Partial<EnrollmentFormData> = { ...enrollmentForm };
    const address: Record<string, string> = {};
    const contact: Record<string, string> = {};

    for (const [key, value] of Object.entries(data)) {
      if (key.startsWith('address.')) {
        address[key.split('.')[1]] = value;
      } else if (key.startsWith('primaryContact.')) {
        contact[key.split('.')[1]] = value;
      } else if (['legalName', 'taxId', 'incorporationDate', 'incorporationState', 'businessType'].includes(key)) {
        (enrollment as Record<string, string>)[key] = value;
      }
    }
    if (Object.keys(address).length > 0) {
      enrollment.address = { ...enrollment.address, ...address } as EnrollmentFormData['address'];
    }
    if (Object.keys(contact).length > 0) {
      enrollment.primaryContact = { ...enrollment.primaryContact, ...contact } as EnrollmentFormData['primaryContact'];
    }
    setEnrollmentForm(enrollment);
  };

  const handleExtract = async () => {
    if (uploadedFiles.length === 0) return;
    setIsExtracting(true);
    try {
      const results = await Promise.all(uploadedFiles.map(f => extractDataFromFile(f)));
      const merged = results.reduce((acc, r) => ({ ...acc, ...r }), {} as Record<string, string>);
      setExtractedData(merged);
      applyExtractedData(merged);
    } finally {
      setIsExtracting(false);
    }
  };

  const validateStep = (): boolean => {
    setStepError('');
    if (currentStep === 0 && selectedProducts.length === 0) {
      setStepError('Please select at least one product.');
      return false;
    }
    if (currentStep === 1 && uploadedFiles.length === 0) {
      setStepError('Please upload at least one document.');
      return false;
    }
    return true;
  };

  const goNext = () => {
    if (!validateStep()) return;
    setCurrentStep(s => Math.min(s + 1, WIZARD_STEPS.length - 1));
  };

  const goBack = () => {
    setStepError('');
    setCurrentStep(s => Math.max(s - 1, 0));
  };

  const completedSteps = Array.from({ length: currentStep }, (_, i) => i);

  const requiredDocs = [
    'Articles of Incorporation',
    'Passport / Government-issued ID',
    ...(selectedProducts.includes('PB') ? ['Proof of Address'] : []),
  ];

  return (
    <div className="max-w-3xl mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary mb-1">Open New Account</h1>
        <p className="text-sm text-text-secondary">
          Complete the steps below to submit your onboarding application.
        </p>
      </div>

      {/* Step indicator */}
      <div className="mb-8">
        <StepIndicator
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          completedSteps={completedSteps}
        />
      </div>

      {/* Step content */}
      <div className="bg-bg-surface border border-border-default rounded-xl p-6">
        <h2 className="text-base font-semibold text-text-primary mb-4">
          {WIZARD_STEPS[currentStep]}
        </h2>

        {/* Step 0: Product selection */}
        {currentStep === 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {ALL_PRODUCTS.map(p => (
              <ProductCard
                key={p}
                product={p}
                selected={selectedProducts.includes(p)}
                onToggle={() =>
                  setSelectedProducts(prev =>
                    prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
                  )
                }
              />
            ))}
          </div>
        )}

        {/* Step 1: Document upload */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-1.5 mb-2">
              {requiredDocs.map(d => (
                <span
                  key={d}
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs bg-bg-elevated border border-border-default text-text-secondary"
                >
                  {d}
                </span>
              ))}
            </div>

            <FileUploadZone
              onFilesAccepted={setUploadedFiles}
              multiple
              label="Drop documents here or click to upload"
              description="PDF, JPEG, PNG accepted"
              accept=".pdf,.jpg,.jpeg,.png"
            />

            {uploadedFiles.length > 0 && (
              <button
                type="button"
                onClick={handleExtract}
                disabled={isExtracting}
                className="flex items-center gap-2 px-4 h-9 rounded-lg bg-bg-elevated border border-border-default hover:border-primary hover:bg-primary-subtle text-text-secondary hover:text-text-primary text-sm font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isExtracting ? (
                  <IconLoader2 size={15} className="animate-spin" />
                ) : (
                  <IconSparkles size={15} className="text-primary" />
                )}
                {isExtracting ? 'Extracting data…' : 'Extract Data from Documents'}
              </button>
            )}
          </div>
        )}

        {/* Step 2: Extracted data */}
        {currentStep === 2 && (
          <div>
            {isExtracting ? (
              <div className="flex flex-col items-center gap-3 py-10">
                <IconLoader2 size={32} className="animate-spin text-primary" />
                <p className="text-text-secondary text-sm">Extracting data from your documents…</p>
              </div>
            ) : (
              <ExtractedDataPreview data={extractedData} />
            )}
          </div>
        )}

        {/* Step 3: Forms */}
        {currentStep === 3 && (
          <div>
            {/* Tabs */}
            <div className="flex gap-1 p-1 rounded-lg bg-bg-elevated mb-5 w-fit">
              {(['enrollment', 'cdd', 'control'] as const).map(tab => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveFormTab(tab)}
                  className={[
                    'px-3 py-1.5 rounded text-sm font-medium transition-colors',
                    activeFormTab === tab
                      ? 'bg-primary text-white'
                      : 'text-text-secondary hover:text-text-primary',
                  ].join(' ')}
                >
                  {tab === 'enrollment' ? 'Enrollment' : tab === 'cdd' ? 'CDD' : 'Control Persons'}
                </button>
              ))}
            </div>

            {activeFormTab === 'enrollment' && (
              <EnrollmentTab data={enrollmentForm} onChange={setEnrollmentForm} />
            )}
            {activeFormTab === 'cdd' && (
              <CDDTab data={cddForm} onChange={setCddForm} />
            )}
            {activeFormTab === 'control' && (
              <ControlPersonsTab persons={controlPersons} onChange={setControlPersons} />
            )}
          </div>
        )}

        {/* Step 4: Submit */}
        {currentStep === 4 && (
          <SubmitStep
            selectedProducts={selectedProducts}
            enrollmentData={enrollmentForm}
            cddData={cddForm}
            controlPersons={controlPersons}
            onSubmit={() => submitMutation.mutate()}
            isSubmitting={submitMutation.isPending}
            submittedCases={submittedCases}
          />
        )}

        {/* Step error */}
        {stepError && (
          <div className="mt-4 px-3 py-2 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm">
            {stepError}
          </div>
        )}
      </div>

      {/* Navigation buttons */}
      {submittedCases.length === 0 && (
        <div className="flex items-center justify-between mt-5">
          <button
            type="button"
            onClick={goBack}
            disabled={currentStep === 0}
            className="flex items-center gap-2 px-4 h-9 rounded-lg border border-border-default text-text-secondary hover:text-text-primary hover:border-primary disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            <IconArrowLeft size={15} />
            Back
          </button>

          {currentStep < WIZARD_STEPS.length - 1 && (
            <button
              type="button"
              onClick={goNext}
              className="flex items-center gap-2 px-4 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold transition-colors"
            >
              Next
              <IconArrowRight size={15} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
