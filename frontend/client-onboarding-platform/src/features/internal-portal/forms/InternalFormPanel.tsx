import { useState } from 'react';
import { IconCheck, IconAlertCircle } from '@tabler/icons-react';
import { StatusBadge } from '../../../components/common/StatusBadge';
import type {
  FormSubmission,
  EnrollmentFormData,
  CDDFormData,
  ControlPersonFormData,
} from '../../../types';
import { formatDateTime } from '../../../utils/formatters';

// ─── Sidebar nav types ────────────────────────────────────────────────────────

interface NavItem    { id: string; label: string }
interface NavSection { id: string; number: number; label: string; items: NavItem[] }

// ─── Section definitions per form type ───────────────────────────────────────

const ENROLLMENT_SECTIONS: NavSection[] = [
  { id: 'your-details', number: 1, label: 'Your Details', items: [
    { id: 'general',              label: 'General' },
    { id: 'additional-details',   label: 'Additional Details' },
    { id: 'identity',             label: 'Identity' },
    { id: 'regulatory-control',   label: 'Regulatory and Control' },
    { id: 'tax',                  label: 'Tax' },
  ]},
  { id: 'key-personnel', number: 2, label: 'Key Personnel', items: [
    { id: 'traders', label: 'Traders (Employees)' },
  ]},
  { id: 'background', number: 3, label: 'Background', items: [
    { id: 'financials',         label: 'Financials' },
    { id: 'investment-profile', label: 'Investment Profile' },
    { id: 'employment',         label: 'Employment' },
  ]},
  { id: 'account-controller', number: 4, label: 'Account Controller', items: [
    { id: 'account-controller-general', label: 'General' },
  ]},
  { id: 'regulatory-questions', number: 5, label: 'Regulatory Questions', items: [] },
];

const CDD_SECTIONS: NavSection[] = [
  { id: 'business', number: 1, label: 'Business Information', items: [
    { id: 'business-profile',  label: 'Business Profile' },
    { id: 'source-of-funds',   label: 'Source of Funds' },
  ]},
  { id: 'beneficial-owners', number: 2, label: 'Beneficial Owners', items: [
    { id: 'owners-list', label: 'Owners' },
  ]},
  { id: 'compliance', number: 3, label: 'Compliance', items: [
    { id: 'pep-sanctions', label: 'PEP & Sanctions' },
  ]},
];

const CONTROL_PERSON_SECTIONS: NavSection[] = [
  { id: 'control-persons', number: 1, label: 'Control Persons', items: [
    { id: 'persons-list', label: 'Persons with Control' },
  ]},
];

const TAX_SECTIONS: NavSection[] = [
  { id: 'classification', number: 1, label: 'Tax Classification', items: [
    { id: 'entity-info', label: 'Entity Information' },
  ]},
  { id: 'identification', number: 2, label: 'Tax Identification', items: [
    { id: 'tin', label: 'TIN / EIN' },
  ]},
  { id: 'fatca', number: 3, label: 'FATCA & Withholding', items: [
    { id: 'fatca-status', label: 'Status & Rates' },
  ]},
];

const SSI_SECTIONS: NavSection[] = [
  { id: 'settlement', number: 1, label: 'Settlement Instructions', items: [
    { id: 'bank-details',  label: 'Bank Details' },
    { id: 'account-info',  label: 'Account Information' },
  ]},
];

const SECTIONS_BY_TYPE: Record<string, NavSection[]> = {
  ENROLLMENT:     ENROLLMENT_SECTIONS,
  CDD:            CDD_SECTIONS,
  CONTROL_PERSON: CONTROL_PERSON_SECTIONS,
  TAX:            TAX_SECTIONS,
  SSI:            SSI_SECTIONS,
};

// ─── Shared read-only display primitives ─────────────────────────────────────

function ReadField({ label, value }: { label: string; value?: string | number }) {
  return (
    <div>
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <div className="h-10 px-3 flex items-center rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary pointer-events-none select-none">
        {value ?? <span className="text-text-muted italic">Not provided</span>}
      </div>
    </div>
  );
}

function ReadSelect({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <div className="h-10 px-3 flex items-center justify-between rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary pointer-events-none select-none">
        <span>{value ?? <span className="text-text-muted italic">Not selected</span>}</span>
        <span className="text-text-muted text-xs">▾</span>
      </div>
    </div>
  );
}

function ReadRadio({ label, value, options }: { label: string; value?: string; options: string[] }) {
  return (
    <div>
      <p className="text-sm text-text-secondary mb-2">{label}</p>
      <div className="flex gap-4">
        {options.map(opt => (
          <label key={opt} className="flex items-center gap-2 pointer-events-none select-none">
            <input
              type="radio"
              readOnly
              checked={value === opt}
              className="accent-primary"
            />
            <span className="text-sm text-text-primary capitalize">{opt}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="pb-4 mb-6 border-b border-border-default">
      <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
      {subtitle && <p className="text-sm text-text-secondary mt-1">{subtitle}</p>}
    </div>
  );
}

// ─── Not-submitted overlay banner ─────────────────────────────────────────────

function NotSubmittedBanner() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 mb-6 rounded-lg bg-warning-subtle border border-warning/25">
      <IconAlertCircle size={16} className="text-warning flex-shrink-0" />
      <p className="text-sm text-warning font-medium">
        Client has not submitted this form yet. Field values are empty.
      </p>
    </div>
  );
}

// ─── Per-section content renderers ───────────────────────────────────────────

function EnrollmentSectionContent({
  sectionId,
  data,
}: {
  sectionId: string;
  data?: EnrollmentFormData;
}) {
  switch (sectionId) {
    case 'general':
      return (
        <div className="space-y-6">
          <SectionHeading title="General" subtitle="Carefully go through the application and fill out the required information." />
          <div className="grid grid-cols-3 gap-4">
            <ReadField label="First Name"  value={data?.primaryContact?.fullName?.split(' ')[0]} />
            <ReadField label="Middle Name" value={undefined} />
            <ReadField label="Last Name"   value={data?.primaryContact?.fullName?.split(' ').slice(1).join(' ')} />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary mb-3">Legal Address</p>
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-4">
                <ReadSelect label="Country" value={data?.address?.country} />
              </div>
              <ReadField label="Address Line 1" value={data?.address?.line1} />
              <ReadField label="Address Line 2" value={data?.address?.line2} />
              <div className="grid grid-cols-2 gap-4">
                <ReadField label="City"           value={data?.address?.city} />
                <ReadSelect label="State/Province" value={data?.address?.state} />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <ReadField label="Postal Code" value={data?.address?.zip} />
              </div>
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary mb-3">Mailing Address</p>
            <div className="flex items-center gap-2.5 mb-3 pointer-events-none select-none">
              <input type="checkbox" readOnly className="w-4 h-4 rounded border-border-default bg-bg-elevated accent-primary" />
              <span className="text-sm text-text-secondary">Check if the Mailing Address is same as the Legal Address.</span>
            </div>
          </div>
        </div>
      );

    case 'additional-details':
      return (
        <div className="space-y-6">
          <SectionHeading title="Additional Details" subtitle="Provide personal background information." />
          <div className="grid grid-cols-2 gap-4">
            <ReadField label="Date of Birth"  />
            <ReadField label="Place of Birth" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <ReadSelect label="Citizenship / Nationality" value={undefined} />
          </div>
        </div>
      );

    case 'identity':
      return (
        <div className="space-y-6">
          <SectionHeading title="Identity" subtitle="Provide government-issued identification details." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="ID Type"   value={undefined} />
            <ReadField  label="ID Number" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadField label="Issue Date"  />
            <ReadField label="Expiry Date" />
          </div>
        </div>
      );

    case 'regulatory-control':
      return (
        <div className="space-y-6">
          <SectionHeading title="Regulatory and Control" subtitle="Answer the following regulatory questions." />
          <ReadRadio
            label="Are you a Control Person of a publicly traded company (10%+ ownership or director/officer)?"
            value={undefined}
            options={['yes', 'no']}
          />
          <ReadRadio
            label="Are you, or an immediate family member, a Politically Exposed Person (PEP)?"
            value={undefined}
            options={['yes', 'no']}
          />
        </div>
      );

    case 'tax':
      return (
        <div className="space-y-6">
          <SectionHeading title="Tax" subtitle="Provide your tax identification details." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="Tax Country" value={undefined} />
            <ReadField  label="Tax Identification Number (TIN / SSN)" value={data?.taxId} />
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
        <div className="space-y-6">
          <SectionHeading title="Traders (Employees)" subtitle="Add authorized traders or employees for this account." />
          <div className="p-6 rounded-lg bg-bg-elevated border border-border-default text-center">
            <p className="text-sm text-text-muted">No traders added yet.</p>
          </div>
        </div>
      );

    case 'financials':
      return (
        <div className="space-y-6">
          <SectionHeading title="Financials" subtitle="Provide your financial background for account suitability." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="Estimated Net Worth" value={undefined} />
            <ReadSelect label="Annual Income"       value={undefined} />
          </div>
        </div>
      );

    case 'investment-profile':
      return (
        <div className="space-y-6">
          <SectionHeading title="Investment Profile" subtitle="Tell us about your investment goals and risk appetite." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="Risk Tolerance"       value={undefined} />
            <ReadSelect label="Investment Objective" value={undefined} />
          </div>
        </div>
      );

    case 'employment':
      return (
        <div className="space-y-6">
          <SectionHeading title="Employment" subtitle="Provide your current employment information." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="Employment Status"     value={undefined} />
            <ReadField  label="Employer Name"         />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadField label="Occupation / Job Title" />
          </div>
        </div>
      );

    case 'account-controller-general':
      return (
        <div className="space-y-6">
          <SectionHeading title="Account Controller" subtitle="Designate who controls this account." />
          <div className="p-4 rounded-lg bg-bg-elevated border border-border-default">
            <p className="text-sm text-text-secondary">
              The account controller has authority to make trading decisions.
              This is typically the primary account holder or an appointed representative.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadField label="Controller Full Name" value={data?.primaryContact?.fullName} />
            <ReadField label="Controller Email"     value={data?.primaryContact?.email} />
          </div>
        </div>
      );

    case 'regulatory-questions':
      return (
        <div className="space-y-6">
          <SectionHeading title="Regulatory Questions" subtitle="Answer all applicable regulatory disclosures." />
          {[
            'Are you affiliated with or employed by a FINRA member broker-dealer?',
            'Are you a director, 10% shareholder, or policy-making officer of a publicly traded company?',
            'Have you been subject to any FINRA disciplinary actions in the past 10 years?',
            'Are you subject to any legal proceedings related to financial activities?',
          ].map((q, i) => (
            <div key={i} className="pb-4 border-b border-border-subtle last:border-0">
              <ReadRadio label={q} value={undefined} options={['yes', 'no']} />
            </div>
          ))}
        </div>
      );

    default:
      return null;
  }
}

function CDDSectionContent({ sectionId, data }: { sectionId: string; data?: CDDFormData }) {
  switch (sectionId) {
    case 'business-profile':
      return (
        <div className="space-y-6">
          <SectionHeading title="Business Profile" subtitle="Describe the nature of your business activities." />
          <div>
            <p className="text-xs text-text-muted mb-1">Nature of Business</p>
            <div className="min-h-[80px] px-3 py-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary pointer-events-none select-none">
              {data?.natureOfBusiness ?? <span className="text-text-muted italic">Not provided</span>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="Expected Trading Volume" value={data?.expectedTradingVolume} />
            <ReadField  label="Operating Jurisdictions" value={data?.jurisdictions?.join(', ')} />
          </div>
        </div>
      );

    case 'source-of-funds':
      return (
        <div className="space-y-6">
          <SectionHeading title="Source of Funds" subtitle="Describe where the funds for this account originate." />
          <ReadSelect label="Primary Source of Funds" value={data?.sourceOfFunds} />
        </div>
      );

    case 'owners-list':
      return (
        <div className="space-y-6">
          <SectionHeading title="Beneficial Owners" subtitle="List all individuals with 25% or more ownership interest." />
          <div className="p-6 rounded-lg bg-bg-elevated border border-border-default text-center">
            <p className="text-sm text-text-muted">No beneficial owners added yet.</p>
          </div>
        </div>
      );

    case 'pep-sanctions':
      return (
        <div className="space-y-6">
          <SectionHeading title="PEP & Sanctions" subtitle="Provide compliance declarations." />
          <ReadField label="PEP Status"       value={data?.pepStatus} />
          <ReadField label="Sanctions Status" value={data?.sanctionsStatus} />
        </div>
      );

    default:
      return null;
  }
}

function ControlPersonSectionContent({
  sectionId,
  data,
}: {
  sectionId: string;
  data?: ControlPersonFormData;
}) {
  if (sectionId !== 'persons-list') return null;
  return (
    <div className="space-y-6">
      <SectionHeading title="Persons with Control" subtitle="List all individuals with significant control or ownership." />
      {data?.controlPersons && data.controlPersons.length > 0 ? (
        data.controlPersons.map((p, i) => (
          <div key={i} className="rounded-lg border border-border-default bg-bg-elevated p-4 space-y-3">
            <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Control Person {i + 1}
              <span className="ml-2 font-normal normal-case text-text-muted">— {p.ownershipPercentage}% ownership</span>
            </p>
            <div className="grid grid-cols-2 gap-4">
              <ReadField label="Full Name"     value={p.fullName} />
              <ReadField label="Title"         value={p.title} />
              <ReadField label="Date of Birth" value={p.dateOfBirth} />
              <ReadField label="Nationality"   value={p.nationality} />
              <ReadField label="ID Type"       value={p.idDocumentType} />
              <ReadField label="ID Number"     value={p.idDocumentNumber} />
            </div>
          </div>
        ))
      ) : (
        <div className="p-6 rounded-lg bg-bg-elevated border border-border-default text-center">
          <p className="text-sm text-text-muted">No control persons added yet.</p>
        </div>
      )}
    </div>
  );
}

function TaxSectionContent({ sectionId }: { sectionId: string }) {
  switch (sectionId) {
    case 'entity-info':
      return (
        <div className="space-y-6">
          <SectionHeading title="Entity Information" subtitle="Provide the legal entity details for tax purposes." />
          <div className="grid grid-cols-2 gap-4">
            <ReadField  label="Legal Name of Entity" />
            <ReadField  label="Business Address"     />
          </div>
          <ReadSelect label="Tax Classification" value={undefined} />
        </div>
      );

    case 'tin':
      return (
        <div className="space-y-6">
          <SectionHeading title="TIN / EIN" subtitle="Provide your tax identification number." />
          <div className="grid grid-cols-2 gap-4">
            <ReadSelect label="TIN Type"                        value={undefined} />
            <ReadField  label="Taxpayer Identification Number"  />
          </div>
          <div className="p-4 rounded-lg bg-info-subtle border border-info/20">
            <p className="text-xs text-info leading-relaxed">
              If you are exempt from backup withholding, enter your exemption code.
            </p>
          </div>
          <ReadField label="Exemption Code" />
        </div>
      );

    case 'fatca-status':
      return (
        <div className="space-y-6">
          <SectionHeading title="FATCA & Withholding" subtitle="Provide your FATCA classification and withholding rate." />
          <ReadSelect label="FATCA Status"     value={undefined} />
          <ReadSelect label="Withholding Rate" value={undefined} />
          <ReadRadio
            label="Are you subject to backup withholding?"
            value={undefined}
            options={['yes', 'no']}
          />
        </div>
      );

    default:
      return null;
  }
}

function SSISectionContent({ sectionId }: { sectionId: string }) {
  switch (sectionId) {
    case 'bank-details':
      return (
        <div className="space-y-6">
          <SectionHeading title="Bank Details" subtitle="Provide the bank information for settlement." />
          <div className="grid grid-cols-2 gap-4">
            <ReadField  label="Bank Name"   />
            <ReadField  label="Bank ABA / Routing Number" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadField  label="Bank Address"  />
            <ReadSelect label="Currency"      value={undefined} />
          </div>
        </div>
      );

    case 'account-info':
      return (
        <div className="space-y-6">
          <SectionHeading title="Account Information" subtitle="Provide the account details for settlement." />
          <div className="grid grid-cols-2 gap-4">
            <ReadField  label="Account Name"   />
            <ReadField  label="Account Number" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ReadField  label="SWIFT / BIC Code" />
            <ReadSelect label="Account Type"     value={undefined} />
          </div>
          <ReadField label="For Further Credit (FFC)" />
          <div className="p-4 rounded-lg bg-bg-elevated border border-border-default">
            <p className="text-xs text-text-muted italic leading-relaxed">
              All settlement instructions are verified by the operations team before activation.
            </p>
          </div>
        </div>
      );

    default:
      return null;
  }
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export default function InternalFormPanel({
  formType,
  submission,
}: {
  formType: string;
  submission: FormSubmission | null;
}) {
  const sections   = SECTIONS_BY_TYPE[formType] ?? [];
  const allItems   = sections.flatMap(s =>
    s.items.length > 0 ? s.items : [{ id: s.id, label: s.label }]
  );
  const firstItem  = allItems[0]?.id ?? '';
  const [activeId, setActiveId] = useState(firstItem);

  const isSubmitted = submission !== null;

  // Extract typed data from the submission
  const enrollmentData    = formType === 'ENROLLMENT'     ? (submission?.data as EnrollmentFormData    | undefined) : undefined;
  const cddData           = formType === 'CDD'            ? (submission?.data as CDDFormData            | undefined) : undefined;
  const controlPersonData = formType === 'CONTROL_PERSON' ? (submission?.data as ControlPersonFormData  | undefined) : undefined;

  function renderContent() {
    switch (formType) {
      case 'ENROLLMENT':
        return <EnrollmentSectionContent    sectionId={activeId} data={enrollmentData} />;
      case 'CDD':
        return <CDDSectionContent           sectionId={activeId} data={cddData} />;
      case 'CONTROL_PERSON':
        return <ControlPersonSectionContent sectionId={activeId} data={controlPersonData} />;
      case 'TAX':
        return <TaxSectionContent           sectionId={activeId} />;
      case 'SSI':
        return <SSISectionContent           sectionId={activeId} />;
      default:
        return null;
    }
  }

  return (
    <div className="flex min-h-full">

      {/* ── Left sidebar ── */}
      <aside className="w-52 flex-shrink-0 border-r border-border-default bg-bg-elevated">
        {/* Submission status pill */}
        <div className="px-5 py-4 border-b border-border-subtle">
          {isSubmitted ? (
            <div className="space-y-1.5">
              <StatusBadge status={submission.status} />
              <p className="text-xs text-text-muted">
                {formatDateTime(submission.submittedAt)}
              </p>
            </div>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">
              <IconAlertCircle size={11} />
              Not submitted
            </span>
          )}
        </div>

        {/* Section nav */}
        <nav className="py-6 px-5">
          {sections.map(section => {
            const sectionActive =
              section.items.some(i => i.id === activeId) ||
              (section.items.length === 0 && section.id === activeId);

            return (
              <div key={section.id} className="relative">
                <button
                  onClick={() => {
                    if (section.items.length === 0) setActiveId(section.id);
                    else setActiveId(section.items[0].id);
                  }}
                  className="flex items-center gap-3 w-full text-left py-0.5 mb-1"
                >
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

                {section.items.length > 0 && (
                  <div
                    className="mb-3"
                    style={{ marginLeft: '10px', paddingLeft: '25px', borderLeft: '1.5px solid #2A3140' }}
                  >
                    {section.items.map(item => {
                      const isActive = item.id === activeId;
                      return (
                        <button
                          key={item.id}
                          onClick={() => setActiveId(item.id)}
                          className={`flex items-center justify-between w-full text-left py-[5px] text-xs transition-colors ${
                            isActive
                              ? 'text-text-primary font-medium'
                              : 'text-text-muted hover:text-text-secondary'
                          }`}
                        >
                          <span>{item.label}</span>
                          {isSubmitted && !isActive && (
                            <IconCheck size={10} className="text-success flex-shrink-0 ml-1" strokeWidth={2.5} />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}

                {section.items.length === 0 && <div className="mb-3" />}
              </div>
            );
          })}
        </nav>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1">
        <div className="py-8 px-7">
          {!isSubmitted && <NotSubmittedBanner />}
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
