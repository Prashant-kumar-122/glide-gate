import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useForm, type UseFormRegister, type FieldValues } from 'react-hook-form';
import { useQuery } from '@tanstack/react-query';
import {
  IconMenu2,
  IconHeadset,
  IconChevronRight,
  IconCheck,
  IconAlertCircle,
} from '@tabler/icons-react';
import { formsService } from '../../../mocks/services/cases.service';
import type { EnrollmentFormData } from '../../../types';

// ─── Section / nav structure ──────────────────────────────────────────────────

interface NavItem {
  id: string;
  label: string;
}
interface NavSection {
  id: string;
  number: number;
  label: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    id: 'your-details', number: 1, label: 'Your Details',
    items: [
      { id: 'general',              label: 'General' },
      { id: 'additional-details',   label: 'Additional Details' },
      { id: 'identity',             label: 'Identity' },
      { id: 'regulatory-control',   label: 'Regulatory and Control' },
      { id: 'tax',                  label: 'Tax' },
    ],
  },
  {
    id: 'key-personnel', number: 2, label: 'Key Personnel',
    items: [
      { id: 'traders', label: 'Traders (Employees)' },
    ],
  },
  {
    id: 'background', number: 3, label: 'Background',
    items: [
      { id: 'financials',         label: 'Financials' },
      { id: 'investment-profile', label: 'Investment Profile' },
      { id: 'employment',         label: 'Employment' },
    ],
  },
  {
    id: 'account-controller', number: 4, label: 'Account Controller',
    items: [
      { id: 'account-controller-general', label: 'General' },
    ],
  },
  {
    id: 'regulatory-questions', number: 5, label: 'Regulatory Questions',
    items: [],
  },
];

const ALL_ITEMS = NAV_SECTIONS.flatMap(s =>
  s.items.length > 0 ? s.items : [{ id: s.id, label: s.label }]
);

// ─── Input / Select helpers ───────────────────────────────────────────────────

function Field({
  label, placeholder, optional = false,
  register, name, error,
}: {
  label: string; placeholder?: string; optional?: boolean;
  register?: UseFormRegister<FieldValues>;
  name?: string; error?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-text-secondary mb-1.5">
        {label}{optional && <span className="text-text-muted ml-1">(Optional)</span>}
      </label>
      <input
        {...(register && name ? register(name) : {})}
        placeholder={placeholder ?? 'Enter'}
        className="w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-colors"
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}

function SelectField({
  label, options, register, name,
}: {
  label: string; options: { value: string; label: string }[];
  register?: UseFormRegister<FieldValues>; name?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-text-secondary mb-1.5">{label}</label>
      <div className="relative">
        <select
          {...(register && name ? register(name) : {})}
          className="w-full h-10 px-3 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary appearance-none pr-8 transition-colors"
        >
          {options.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">▾</span>
      </div>
    </div>
  );
}

const US_STATES = [
  { value: '', label: 'Select' },
  { value: 'AL', label: 'Alabama' }, { value: 'AK', label: 'Alaska' },
  { value: 'AZ', label: 'Arizona' }, { value: 'CA', label: 'California' },
  { value: 'CO', label: 'Colorado' }, { value: 'CT', label: 'Connecticut' },
  { value: 'DE', label: 'Delaware' }, { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' }, { value: 'IL', label: 'Illinois' },
  { value: 'MA', label: 'Massachusetts' }, { value: 'MD', label: 'Maryland' },
  { value: 'MI', label: 'Michigan' }, { value: 'MN', label: 'Minnesota' },
  { value: 'NJ', label: 'New Jersey' }, { value: 'NY', label: 'New York' },
  { value: 'NC', label: 'North Carolina' }, { value: 'OH', label: 'Ohio' },
  { value: 'PA', label: 'Pennsylvania' }, { value: 'TX', label: 'Texas' },
  { value: 'VA', label: 'Virginia' }, { value: 'WA', label: 'Washington' },
];

const COUNTRIES = [
  { value: 'US', label: 'USA' },
  { value: 'GB', label: 'United Kingdom' },
  { value: 'CA', label: 'Canada' },
  { value: 'AU', label: 'Australia' },
  { value: 'KY', label: 'Cayman Islands' },
];

const RISK_LEVELS = [
  { value: '', label: 'Select' },
  { value: 'conservative', label: 'Conservative' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'aggressive', label: 'Aggressive' },
];

const EMPLOYMENT_STATUSES = [
  { value: '', label: 'Select' },
  { value: 'employed', label: 'Employed' },
  { value: 'self_employed', label: 'Self-Employed' },
  { value: 'unemployed', label: 'Unemployed' },
  { value: 'retired', label: 'Retired' },
];

const INCOME_RANGES = [
  { value: '', label: 'Select' },
  { value: 'under_50k', label: 'Under $50,000' },
  { value: '50k_100k', label: '$50,000 – $100,000' },
  { value: '100k_250k', label: '$100,000 – $250,000' },
  { value: '250k_1m', label: '$250,000 – $1,000,000' },
  { value: 'over_1m', label: 'Over $1,000,000' },
];

// ─── Section content ──────────────────────────────────────────────────────────

function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="pb-4 mb-6 border-b border-border-default">
      <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
      {subtitle && <p className="text-sm text-text-secondary mt-1">{subtitle}</p>}
    </div>
  );
}

function AddressBlock({
  prefix, title, register,
}: {
  prefix: string; title: string; register: UseFormRegister<FieldValues>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold text-text-primary">
        {title}{' '}
        <span className="text-warning font-normal text-xs">(PO Box's are not accepted)</span>
      </p>
      <div className="grid grid-cols-3 gap-4">
        <SelectField label="Country" options={COUNTRIES} register={register} name={`${prefix}.country`} />
      </div>
      <Field label="Address Line 1" register={register} name={`${prefix}.line1`} />
      <Field label="Address Line 2" optional register={register} name={`${prefix}.line2`} />
      <div className="grid grid-cols-2 gap-4">
        <Field label="City" register={register} name={`${prefix}.city`} />
        <SelectField label="State/Province" options={US_STATES} register={register} name={`${prefix}.state`} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Field label="Postal Code" register={register} name={`${prefix}.zip`} />
      </div>
    </div>
  );
}

// ─── Completed saved banner ───────────────────────────────────────────────────

function SavedBanner() {
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-success-subtle border border-success/20 text-success text-sm font-medium">
      <IconCheck size={15} />
      Changes saved successfully.
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

const SECTION_BREADCRUMB: Record<string, string> = {
  'general':                  'Enrollment Form',
  'additional-details':       'Enrollment Form',
  'identity':                 'Enrollment Form',
  'regulatory-control':       'Due Diligence',
  'tax':                      'Enrollment Form',
  'traders':                  'Key Personnel',
  'financials':               'Background',
  'investment-profile':       'Background',
  'employment':               'Background',
  'account-controller-general': 'Account Controller',
  'regulatory-questions':     'Regulatory Questions',
};

export default function EnrollmentFormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const initialSection = searchParams.get('section') ?? 'general';
  const [activeItemId, setActiveItemId] = useState(initialSection);
  const [mailingSameAsLegal, setMailingSameAsLegal] = useState(false);
  const [saved, setSaved] = useState(false);
  const [completedItems, setCompletedItems] = useState<Set<string>>(new Set(['additional-details', 'identity']));

  // Load existing enrollment form data
  const { data: forms = [] } = useQuery({
    queryKey: ['forms', 'case', caseId],
    queryFn: () => formsService.getFormsByCase(caseId!),
    enabled: !!caseId,
  });

  const existingEnrollment = forms.find(f => f.type === 'ENROLLMENT');
  const enrollmentData = existingEnrollment?.data as Partial<EnrollmentFormData> | undefined;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { register: _register, handleSubmit, watch, setValue } = useForm({
    defaultValues: {
      firstName:  enrollmentData?.primaryContact?.fullName?.split(' ')[0] ?? '',
      middleName: '',
      lastName:   enrollmentData?.primaryContact?.fullName?.split(' ').slice(1).join(' ') ?? '',
      legalAddress: {
        country: 'US',
        line1:   enrollmentData?.address?.line1 ?? '',
        line2:   enrollmentData?.address?.line2 ?? '',
        city:    enrollmentData?.address?.city  ?? '',
        state:   enrollmentData?.address?.state ?? '',
        zip:     enrollmentData?.address?.zip   ?? '',
      },
      mailingAddress: {
        country: 'US', line1: '', line2: '', city: '', state: '', zip: '',
      },
      // Additional Details
      dateOfBirth:  '',
      placeOfBirth: '',
      citizenship:  'US',
      // Identity
      idType:       'passport',
      idNumber:     enrollmentData ? 'X12345678' : '',
      idIssueDate:  '',
      idExpiry:     '',
      // Regulatory
      isControlPerson: 'no',
      isPEP:           'no',
      // Tax
      taxCountry:  'US',
      tin:         enrollmentData?.taxId ?? '',
      // Financials
      netWorth:    '',
      annualIncome: '',
      // Employment
      employmentStatus: '',
      employerName:     '',
      occupation:       '',
      // Investment
      riskTolerance:         '',
      investmentObjective:   '',
    },
  });

  const register = _register as UseFormRegister<FieldValues>;
  const legalAddress = watch('legalAddress');

  useEffect(() => {
    if (mailingSameAsLegal) {
      setValue('mailingAddress', { ...legalAddress });
    }
  }, [mailingSameAsLegal, legalAddress, setValue]);

  const onSave = handleSubmit(() => {
    setCompletedItems(prev => new Set([...prev, activeItemId]));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  });

  const goToNext = () => {
    const currentIdx = ALL_ITEMS.findIndex(i => i.id === activeItemId);
    if (currentIdx < ALL_ITEMS.length - 1) {
      setCompletedItems(prev => new Set([...prev, activeItemId]));
      setActiveItemId(ALL_ITEMS[currentIdx + 1].id);
    } else {
      navigate(`/client/applications/${caseId}`);
    }
  };

  const activeSection = NAV_SECTIONS.find(s =>
    s.items.some(i => i.id === activeItemId) || (s.items.length === 0 && s.id === activeItemId)
  );

  // ── Render section content ──────────────────────────────────────────────────

  function renderContent() {
    switch (activeItemId) {

      case 'general':
        return (
          <div className="space-y-8">
            <SectionHeading
              title="General"
              subtitle="Carefully go through the application and fill out the required information."
            />

            {/* Name */}
            <div className="grid grid-cols-3 gap-4">
              <Field label="First Name"              register={register} name="firstName" />
              <Field label="Middle Name" optional     register={register} name="middleName" />
              <Field label="Last Name"               register={register} name="lastName" />
            </div>

            {/* Legal Address */}
            <div className="pt-2">
              <AddressBlock prefix="legalAddress" title="Legal Address" register={register} />
            </div>

            {/* Mailing Address */}
            <div className="pt-2 space-y-4">
              <p className="text-sm font-semibold text-text-primary">
                Mailing Address{' '}
                <span className="text-warning font-normal text-xs">(PO Box's are not accepted)</span>
              </p>
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={mailingSameAsLegal}
                  onChange={e => setMailingSameAsLegal(e.target.checked)}
                  className="w-4 h-4 rounded border-border-default bg-bg-elevated accent-primary"
                />
                <span className="text-sm text-text-secondary">
                  Check if the Mailing Address is same as the Legal Address.
                </span>
              </label>
              {!mailingSameAsLegal && (
                <AddressBlock prefix="mailingAddress" title="" register={register} />
              )}
            </div>
          </div>
        );

      case 'additional-details':
        return (
          <div className="space-y-8">
            <SectionHeading title="Additional Details" subtitle="Provide personal background information." />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Date of Birth"   placeholder="YYYY-MM-DD" register={register} name="dateOfBirth" />
              <Field label="Place of Birth"  register={register} name="placeOfBirth" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <SelectField label="Citizenship / Nationality" options={COUNTRIES} register={register} name="citizenship" />
            </div>
          </div>
        );

      case 'identity':
        return (
          <div className="space-y-8">
            <SectionHeading title="Identity" subtitle="Provide your government-issued identification details." />
            <div className="grid grid-cols-2 gap-4">
              <SelectField
                label="ID Type"
                options={[
                  { value: 'passport',         label: 'Passport' },
                  { value: 'drivers_license',   label: "Driver's License" },
                  { value: 'national_id',       label: 'National ID Card' },
                ]}
                register={register} name="idType"
              />
              <Field label="ID Number" register={register} name="idNumber" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Issue Date"  placeholder="YYYY-MM-DD" register={register} name="idIssueDate" />
              <Field label="Expiry Date" placeholder="YYYY-MM-DD" register={register} name="idExpiry" />
            </div>
          </div>
        );

      case 'regulatory-control':
        return (
          <div className="space-y-8">
            <SectionHeading title="Regulatory and Control" subtitle="Answer the following regulatory questions." />
            <div className="space-y-5">
              <div>
                <p className="text-sm text-text-secondary mb-2">
                  Are you a Control Person of a publicly traded company (10%+ ownership or director/officer)?
                </p>
                <div className="flex gap-4">
                  {['yes', 'no'].map(v => (
                    <label key={v} className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" value={v} {...register('isControlPerson')}
                        className="accent-primary" />
                      <span className="text-sm text-text-primary capitalize">{v}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-text-secondary mb-2">
                  Are you, or an immediate family member, a Politically Exposed Person (PEP)?
                </p>
                <div className="flex gap-4">
                  {['yes', 'no'].map(v => (
                    <label key={v} className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" value={v} {...register('isPEP')}
                        className="accent-primary" />
                      <span className="text-sm text-text-primary capitalize">{v}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      case 'tax':
        return (
          <div className="space-y-8">
            <SectionHeading title="Tax" subtitle="Provide your tax identification details." />
            <div className="grid grid-cols-2 gap-4">
              <SelectField label="Tax Country" options={COUNTRIES} register={register} name="taxCountry" />
              <Field label="Tax Identification Number (TIN / SSN)" register={register} name="tin" />
            </div>
            <div className="p-4 rounded-lg bg-info-subtle border border-info/20">
              <p className="text-xs text-info leading-relaxed">
                Your TIN/SSN is required for regulatory reporting purposes and is encrypted at rest.
                We comply with IRS W-9 and FATCA requirements.
              </p>
            </div>
          </div>
        );

      case 'traders':
        return (
          <div className="space-y-8">
            <SectionHeading title="Traders (Employees)" subtitle="Add authorized traders or employees for this account." />
            <div className="p-6 rounded-lg bg-bg-elevated border border-border-default text-center">
              <p className="text-sm text-text-muted">No traders added yet.</p>
              <button className="mt-3 px-4 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-medium transition-colors">
                + Add Trader
              </button>
            </div>
          </div>
        );

      case 'financials':
        return (
          <div className="space-y-8">
            <SectionHeading title="Financials" subtitle="Provide your financial background for account suitability." />
            <div className="grid grid-cols-2 gap-4">
              <SelectField label="Estimated Net Worth"  options={INCOME_RANGES} register={register} name="netWorth" />
              <SelectField label="Annual Income"        options={INCOME_RANGES} register={register} name="annualIncome" />
            </div>
          </div>
        );

      case 'investment-profile':
        return (
          <div className="space-y-8">
            <SectionHeading title="Investment Profile" subtitle="Tell us about your investment goals and risk appetite." />
            <div className="grid grid-cols-2 gap-4">
              <SelectField label="Risk Tolerance" options={RISK_LEVELS} register={register} name="riskTolerance" />
              <SelectField
                label="Investment Objective"
                options={[
                  { value: '', label: 'Select' },
                  { value: 'growth', label: 'Capital Growth' },
                  { value: 'income', label: 'Income' },
                  { value: 'preservation', label: 'Capital Preservation' },
                  { value: 'speculation', label: 'Speculation' },
                ]}
                register={register} name="investmentObjective"
              />
            </div>
          </div>
        );

      case 'employment':
        return (
          <div className="space-y-8">
            <SectionHeading title="Employment" subtitle="Provide your current employment information." />
            <div className="grid grid-cols-2 gap-4">
              <SelectField label="Employment Status" options={EMPLOYMENT_STATUSES} register={register} name="employmentStatus" />
              <Field label="Employer Name" optional register={register} name="employerName" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Occupation / Job Title" optional register={register} name="occupation" />
            </div>
          </div>
        );

      case 'account-controller-general':
        return (
          <div className="space-y-8">
            <SectionHeading title="Account Controller" subtitle="Designate who controls this account." />
            <div className="p-4 rounded-lg bg-bg-elevated border border-border-default">
              <p className="text-sm text-text-secondary">
                The account controller has authority to make trading decisions.
                This is typically the primary account holder or an appointed representative.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Controller Full Name"  register={register} name="firstName" />
              <Field label="Controller Email"       placeholder="email@example.com" />
            </div>
          </div>
        );

      case 'regulatory-questions':
        return (
          <div className="space-y-8">
            <SectionHeading title="Regulatory Questions" subtitle="Answer all applicable regulatory disclosures." />
            {[
              'Are you affiliated with or employed by a FINRA member broker-dealer?',
              'Are you a director, 10% shareholder, or policy-making officer of a publicly traded company?',
              'Have you been subject to any FINRA disciplinary actions in the past 10 years?',
              'Are you subject to any legal proceedings related to financial activities?',
            ].map((q, i) => (
              <div key={i} className="pb-4 border-b border-border-subtle last:border-0">
                <p className="text-sm text-text-secondary mb-2">{q}</p>
                <div className="flex gap-4">
                  {['yes', 'no'].map(v => (
                    <label key={v} className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name={`reg-q-${i}`} value={v} className="accent-primary" />
                      <span className="text-sm text-text-primary capitalize">{v}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        );

      default:
        return (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <IconAlertCircle size={32} className="text-text-muted" />
            <p className="text-text-muted text-sm">Section coming soon.</p>
          </div>
        );
    }
  }

  const isLastItem = ALL_ITEMS[ALL_ITEMS.length - 1].id === activeItemId;

  return (
    <div className="min-h-screen bg-bg-base flex flex-col">

      {/* ── Top navigation bar ──────────────────────────────────────────────── */}
      <header className="h-14 bg-bg-surface border-b border-border-default flex items-center justify-between px-6 flex-shrink-0 z-10">
        <div className="flex items-center gap-4">
          <button className="text-text-muted hover:text-text-primary transition-colors">
            <IconMenu2 size={20} />
          </button>
          <span className="text-sm font-semibold text-text-primary">Client Enrollment Portal</span>
        </div>
        <button className="flex items-center gap-2 px-4 h-8 rounded-lg border border-primary text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">
          <IconHeadset size={14} />
          Contact us
        </button>
      </header>

      {/* ── Sub-header: company + breadcrumb ──────────────────────────────── */}
      <div className="h-11 bg-bg-surface border-b border-border-default flex items-center gap-4 px-6 flex-shrink-0">
        <span className="text-sm font-bold text-text-primary whitespace-nowrap">
          AIB Investments Pvt. Ltd.
        </span>
        <nav className="flex items-center gap-1.5 text-xs">
          <Link to="/client/dashboard" className="text-primary hover:underline">Home</Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <Link to={`/client/applications/${caseId}`} className="text-primary hover:underline">
            IB Application
          </Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <Link to={`/client/applications/${caseId}`} className="text-primary hover:underline">
            {caseId}
          </Link>
          <IconChevronRight size={11} className="text-text-muted" />
          <span className="text-text-secondary">
            {SECTION_BREADCRUMB[activeItemId] ?? 'Enrollment Form'}
          </span>
        </nav>
      </div>

      {/* ── Body ──────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left sidebar */}
        <aside className="w-56 flex-shrink-0 overflow-y-auto">
          <nav className="py-8 px-5">
            {NAV_SECTIONS.map(section => {
              const sectionActive =
                section.items.some(i => i.id === activeItemId) ||
                (section.items.length === 0 && section.id === activeItemId);

              return (
                <div key={section.id} className="relative">

                  {/* Section header row */}
                  <button
                    onClick={() => {
                      if (section.items.length === 0) setActiveItemId(section.id);
                      else setActiveItemId(section.items[0].id);
                    }}
                    className="flex items-center gap-3 w-full text-left py-0.5 mb-1"
                  >
                    {/* Numbered circle — outlined only; filled only when active */}
                    <span className={[
                      'flex-shrink-0 w-[22px] h-[22px] rounded-full flex items-center justify-center text-[11px] font-bold border-2 transition-colors',
                      sectionActive
                        ? 'border-primary text-primary bg-primary/10'
                        : 'border-text-muted/40 text-text-muted',
                    ].join(' ')}>
                      {section.number}
                    </span>
                    <span className={`text-sm font-semibold leading-tight transition-colors ${
                      sectionActive ? 'text-text-primary' : 'text-text-muted'
                    }`}>
                      {section.label}
                    </span>
                  </button>

                  {/* Sub-items — indented with a vertical line aligned to circle center */}
                  {section.items.length > 0 && (
                    <div
                      className="mb-3"
                      style={{ marginLeft: '10px', paddingLeft: '25px', borderLeft: '1.5px solid #2A3140' }}
                    >
                      {section.items.map(item => {
                        const isActive = item.id === activeItemId;
                        const isDone   = completedItems.has(item.id);
                        return (
                          <button
                            key={item.id}
                            onClick={() => setActiveItemId(item.id)}
                            className={`flex items-center justify-between w-full text-left py-[5px] text-xs transition-colors ${
                              isActive
                                ? 'text-text-primary font-medium'
                                : 'text-text-muted hover:text-text-secondary'
                            }`}
                          >
                            <span>{item.label}</span>
                            {isDone && !isActive && (
                              <IconCheck size={10} className="text-success flex-shrink-0 ml-1" strokeWidth={2.5} />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Bottom gap for sections without sub-items */}
                  {section.items.length === 0 && <div className="mb-3" />}
                </div>
              );
            })}
          </nav>
        </aside>

        {/* Main form content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto py-10 px-8 pb-28">

            {/* Saved banner */}
            {saved && (
              <div className="mb-6">
                <SavedBanner />
              </div>
            )}

            {/* Form content */}
            <form onSubmit={e => e.preventDefault()}>
              {renderContent()}
            </form>
          </div>
        </main>
      </div>

      {/* ── Fixed bottom bar ──────────────────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 right-0 h-16 bg-bg-surface border-t border-border-default flex items-center justify-end px-10 z-20">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onSave}
            className="px-5 h-9 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-primary transition-colors"
          >
            Save
          </button>
          <button
            type="button"
            onClick={goToNext}
            className="px-6 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold transition-colors"
          >
            {isLastItem ? 'Finish' : 'Continue'}
          </button>
        </div>
      </footer>
    </div>
  );
}
