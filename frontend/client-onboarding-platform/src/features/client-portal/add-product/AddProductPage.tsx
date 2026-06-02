import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  IconCheck,
  IconLoader2,
  IconChevronDown,
  IconChevronUp,
  IconChevronRight,
  IconMenu2,
  IconBuildingBank,
  IconHeadset,
  IconFileText,
  IconClipboardText,
  IconUser,
  IconReceipt2,
  IconArrowsTransferDown,
  IconCreditCard,
  IconMapPin,
  IconUserCheck,
  IconX,
} from '@tabler/icons-react';
import { casesService, formsService, documentsService } from '../../../mocks/services/cases.service';
import { useAuth } from '../../../store/AuthContext';
import { PRODUCT_LABELS } from '../../../types';
import type { ProductType } from '../../../types';
import { formatDate } from '../../../utils/formatters';
import { StatusBadge } from '../../../components/common/StatusBadge';

// ─── Constants ────────────────────────────────────────────────────────────────

const ALL_PRODUCTS: ProductType[] = ['PB', 'DvP', 'IB_CASH', 'FCM', 'RETIREMENT', 'RETAIL'];

const PRODUCT_DESCRIPTIONS: Record<ProductType, string> = {
  PB:         'Prime brokerage services for equity, fixed income, and multi-asset strategies.',
  DvP:        'Settle transactions securely with simultaneous delivery and payment.',
  IB_CASH:    'Institutional-grade cash management and money market solutions.',
  FCM:        'Trade futures and derivatives with a leading futures commission merchant.',
  RETIREMENT: 'Tax-advantaged retirement account solutions.',
  RETAIL:     'Active retail trading with access to equities, ETFs, and options.',
};

interface ItemMeta { label: string; description: string; icon: React.ReactNode }

const FORM_META: Record<string, ItemMeta> = {
  ENROLLMENT:     { label: 'Enrollment Form',                  description: 'Entity profile, address, and primary contact',           icon: <IconFileText size={16} /> },
  CDD:            { label: 'Customer Due Diligence (CDD)',      description: 'Business activities, source of funds, and risk profile', icon: <IconClipboardText size={16} /> },
  CONTROL_PERSON: { label: 'Controller Person Form',           description: 'Individuals with 25%+ ownership or significant control', icon: <IconUser size={16} /> },
  TAX:            { label: 'Tax Form (W-9 / W-8BEN-E)',        description: 'Tax classification, FATCA status, and withholding rate', icon: <IconReceipt2 size={16} /> },
  SSI:            { label: 'Standard Settlement Instructions', description: 'Beneficiary bank account details for settlement',        icon: <IconArrowsTransferDown size={16} /> },
};

const DOC_META: Record<string, ItemMeta> = {
  PASSPORT:                  { label: 'Passport / Government-issued ID',   description: 'Valid passport or government-issued photo ID',       icon: <IconCreditCard size={16} /> },
  NATIONAL_ID:               { label: "National ID / Driver's License",    description: 'National identity card or driver\'s license',        icon: <IconCreditCard size={16} /> },
  ARTICLES_OF_INCORPORATION: { label: 'Articles of Incorporation',         description: 'Certificate of incorporation or formation documents', icon: <IconFileText size={16} /> },
  PROOF_OF_ADDRESS:          { label: 'Proof of Address',                  description: 'Utility bill or bank statement (last 3 months)',     icon: <IconMapPin size={16} /> },
  TAX_FORM:                  { label: 'Tax Form (W-9 / W-8BEN-E)',         description: 'Signed tax certification document',                  icon: <IconReceipt2 size={16} /> },
  ENROLLMENT_FORM:           { label: 'Signed Enrollment Form',            description: 'Completed and signed enrollment application',        icon: <IconFileText size={16} /> },
  CDD_FORM:                  { label: 'CDD Supporting Document',           description: 'Additional due diligence documentation',            icon: <IconClipboardText size={16} /> },
  CONTROL_PERSON_FORM:       { label: 'Control Person Identity Documents', description: 'Government-issued ID for all controlling persons',   icon: <IconUserCheck size={16} /> },
};

// Full set of forms/docs required for every product — used to derive what still needs action
const REQUIRED_FORM_TYPES = ['ENROLLMENT', 'CDD', 'CONTROL_PERSON', 'TAX', 'SSI'];
const REQUIRED_DOC_TYPES  = ['PASSPORT', 'ARTICLES_OF_INCORPORATION', 'PROOF_OF_ADDRESS', 'TAX_FORM', 'NATIONAL_ID'];

type Step = 'select' | 'review';

// ─── Review item type ─────────────────────────────────────────────────────────

interface ReviewItem {
  id:          string;
  kind:        'form' | 'doc' | 'required-form' | 'required-doc';
  rawType:     string;
  label:       string;
  description: string;
  icon:        React.ReactNode;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload:     Record<string, any>;
}

// ─── Field row helper ─────────────────────────────────────────────────────────

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex flex-col gap-0.5 py-2.5 border-b border-border-subtle">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-sm text-text-primary leading-snug">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1 px-5">{title}</p>
      <div className="px-5 grid grid-cols-2 gap-x-4">{children}</div>
    </div>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function DetailPanel({ item, onClose }: { item: ReviewItem; onClose: () => void }) {
  const d = item.payload;

  const renderBody = () => {
    if (item.kind === 'required-form' || item.kind === 'required-doc') {
      return (
        <div className="px-5 py-6 space-y-4">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-warning/10 border border-warning/20">
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-warning/15 flex items-center justify-center text-warning mt-0.5">
              {item.icon}
            </div>
            <div>
              <p className="text-sm font-semibold text-warning mb-1">
                {item.kind === 'required-form' ? 'Form to be completed' : 'Document to be uploaded'}
              </p>
              <p className="text-xs text-text-secondary leading-relaxed">
                {item.description}
              </p>
            </div>
          </div>
          <div className="border border-border-default rounded-xl p-4">
            <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">What you'll need to do</p>
            <p className="text-sm text-text-secondary leading-relaxed">
              {item.kind === 'required-form'
                ? 'This form is required for the new product. You will be able to fill it out directly from the application tracking page after the account is opened.'
                : 'This document is required for the new product. You will be able to upload it from the application tracking page after the account is opened.'}
            </p>
          </div>
        </div>
      );
    }

    if (item.kind === 'doc') {
      return (
        <>
          <Section title="File Info">
            <FieldRow label="File Name" value={d.fileName} />
            <FieldRow label="File Size" value={d.fileSize} />
            <FieldRow label="Uploaded" value={d.uploadedAt ? formatDate(d.uploadedAt) : undefined} />
            <FieldRow label="Status" value={d.status ? <StatusBadge status={d.status} /> : undefined} />
          </Section>
          {d.extractedData && Object.keys(d.extractedData).length > 0 && (
            <Section title="Extracted Data">
              {Object.entries(d.extractedData as Record<string, string>).map(([k, v]) => (
                <FieldRow
                  key={k}
                  label={k.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}
                  value={v}
                />
              ))}
            </Section>
          )}
        </>
      );
    }

    switch (item.rawType) {
      case 'ENROLLMENT':
        return (
          <>
            <Section title="Entity Profile">
              <FieldRow label="Legal Name"          value={d.legalName} />
              <FieldRow label="Tax ID / EIN"        value={d.taxId} />
              <FieldRow label="Business Type"       value={d.businessType} />
              <FieldRow label="Incorporation Date"  value={d.incorporationDate} />
              <FieldRow label="Incorporation State" value={d.incorporationState} />
            </Section>
            {d.address && (
              <Section title="Address">
                <FieldRow label="Line 1"  value={d.address.line1} />
                <FieldRow label="Line 2"  value={d.address.line2} />
                <FieldRow label="City"    value={d.address.city} />
                <FieldRow label="State"   value={d.address.state} />
                <FieldRow label="ZIP"     value={d.address.zip} />
                <FieldRow label="Country" value={d.address.country} />
              </Section>
            )}
            {d.primaryContact && (
              <Section title="Primary Contact">
                <FieldRow label="Full Name" value={d.primaryContact.fullName} />
                <FieldRow label="Title"     value={d.primaryContact.title} />
                <FieldRow label="Email"     value={d.primaryContact.email} />
                <FieldRow label="Phone"     value={d.primaryContact.phone} />
              </Section>
            )}
          </>
        );

      case 'CDD':
        return (
          <Section title="Due Diligence Details">
            <FieldRow label="Nature of Business"        value={d.natureOfBusiness} />
            <FieldRow label="Source of Funds"           value={d.sourceOfFunds} />
            <FieldRow label="Expected Trading Volume"   value={d.expectedTradingVolume} />
            <FieldRow label="Operating Jurisdictions"   value={Array.isArray(d.jurisdictions) ? d.jurisdictions.join(', ') : d.jurisdictions} />
            <FieldRow label="PEP Status"                value={d.pepStatus === true ? 'Yes' : d.pepStatus === false ? 'No' : undefined} />
            <FieldRow label="Sanctions Status"          value={d.sanctionsStatus === true ? 'Yes' : d.sanctionsStatus === false ? 'No' : undefined} />
          </Section>
        );

      case 'CONTROL_PERSON':
        return (
          <>
            {Array.isArray(d.controlPersons) && d.controlPersons.map((p: Record<string, unknown>, i: number) => (
              <Section key={i} title={`Controller Person ${i + 1}`}>
                <FieldRow label="Full Name"        value={p.fullName as string} />
                <FieldRow label="Title"            value={p.title as string} />
                <FieldRow label="Ownership"        value={p.ownershipPercentage !== undefined ? `${p.ownershipPercentage}%` : undefined} />
                <FieldRow label="Date of Birth"    value={p.dateOfBirth as string} />
                <FieldRow label="Nationality"      value={p.nationality as string} />
                <FieldRow label="ID Document Type" value={p.idDocumentType as string} />
                <FieldRow label="ID Number"        value={p.idDocumentNumber as string} />
              </Section>
            ))}
          </>
        );

      case 'TAX':
        return (
          <Section title="Tax Details">
            <FieldRow label="Entity Name"              value={d.entityName} />
            <FieldRow label="Tax ID Type"              value={d.taxIdType} />
            <FieldRow label="Tax ID Number"            value={d.taxIdNumber} />
            <FieldRow label="Tax Classification"       value={d.taxClassification} />
            <FieldRow label="Country of Tax Residency" value={d.countryOfTaxResidency} />
            <FieldRow label="FATCA Status"             value={d.fatcaStatus} />
            <FieldRow label="Treaty Country"           value={d.treatyCountry} />
            <FieldRow label="Withholding Rate"         value={d.withholdingRate} />
          </Section>
        );

      case 'SSI':
        return (
          <>
            <Section title="Beneficiary Account">
              <FieldRow label="Currency"       value={d.currency} />
              <FieldRow label="Account Name"   value={d.accountName} />
              <FieldRow label="Account Number" value={d.accountNumber} />
            </Section>
            <Section title="Beneficiary Bank">
              <FieldRow label="Bank Name"    value={d.bankName} />
              <FieldRow label="Bank Address" value={d.bankAddress} />
              <FieldRow label="SWIFT / BIC"  value={d.swiftBic} />
            </Section>
            {d.correspondentBankName && (
              <Section title="Correspondent Bank">
                <FieldRow label="Bank Name"       value={d.correspondentBankName} />
                <FieldRow label="SWIFT / BIC"     value={d.correspondentSwift} />
                <FieldRow label="Account Number"  value={d.correspondentAccountNumber} />
              </Section>
            )}
          </>
        );

      default:
        return (
          <div className="px-5 py-8 text-center text-sm text-text-muted">
            No preview available for this item.
          </div>
        );
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex-shrink-0 flex items-center justify-between gap-3 px-5 py-4 border-b border-border-default bg-bg-elevated">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary-subtle flex items-center justify-center text-primary">
            {item.icon}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text-primary truncate">{item.label}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              {item.kind === 'form' || item.kind === 'doc' ? (
                <span className="inline-flex items-center gap-1 text-xs text-success font-medium">
                  <IconCheck size={10} strokeWidth={3} /> Copied from existing account
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">
                  Action required
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          <IconX size={15} />
        </button>
      </div>

      {/* Panel body */}
      <div className="flex-1 overflow-y-auto py-4">
        {renderBody()}
      </div>
    </div>
  );
}

// ─── Collapsible copied-items group ──────────────────────────────────────────

function CopiedGroup({
  title,
  items,
  selectedId,
  onSelect,
  variant = 'copied',
}: {
  title:      string;
  items:      ReviewItem[];
  selectedId: string | null;
  onSelect:   (item: ReviewItem) => void;
  variant?:   'copied' | 'required';
}) {
  const [open, setOpen] = useState(true);
  const isCopied = variant === 'copied';

  return (
    <div className={`rounded-xl border overflow-hidden ${isCopied ? 'border-border-default' : 'border-warning/30'}`}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className={`w-full flex items-center justify-between px-5 py-3.5 hover:bg-bg-hover transition-colors text-left ${
          isCopied ? 'bg-bg-elevated' : 'bg-warning/5'
        }`}
      >
        <span className="text-sm font-semibold text-text-primary">
          {title}{' '}
          <span className={`font-semibold ${isCopied ? 'text-success' : 'text-warning'}`}>
            ({items.length})
          </span>
        </span>
        {open
          ? <IconChevronUp size={15} className="text-text-muted" />
          : <IconChevronDown size={15} className="text-text-muted" />
        }
      </button>

      {/* Item rows */}
      {open && items.map(item => {
        const isSelected = selectedId === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item)}
            className={`w-full flex items-center gap-4 px-5 py-4 border-t border-border-subtle text-left transition-colors ${
              isSelected
                ? isCopied
                  ? 'bg-primary-subtle border-l-2 border-l-primary'
                  : 'bg-warning/10 border-l-2 border-l-warning'
                : 'hover:bg-bg-hover'
            }`}
          >
            {/* Icon */}
            <div className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${
              isSelected
                ? isCopied ? 'bg-primary text-white' : 'bg-warning text-white'
                : isCopied ? 'bg-primary-subtle text-primary' : 'bg-warning/15 text-warning'
            }`}>
              {item.icon}
            </div>

            {/* Label + description */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${
                isSelected
                  ? isCopied ? 'text-primary' : 'text-warning'
                  : 'text-text-primary'
              }`}>
                {item.label}
              </p>
              <p className="text-xs text-text-muted mt-0.5">{item.description}</p>
            </div>

            {/* Status badge + chevron */}
            <div className="flex-shrink-0 flex items-center gap-2">
              {isCopied ? (
                <IconCheck size={15} className="text-success" strokeWidth={2.5} />
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">
                  Required
                </span>
              )}
              <IconChevronRight size={13} className={`transition-colors ${
                isSelected
                  ? isCopied ? 'text-primary' : 'text-warning'
                  : 'text-text-muted'
              }`} />
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AddProductPage() {
  const { user }    = useAuth();
  const navigate    = useNavigate();
  const queryClient = useQueryClient();

  const [step, setStep]                   = useState<Step>('select');
  const [selected, setSelected]           = useState<ProductType[]>([]);
  const [confirmed, setConfirmed]         = useState(false);
  const [selectedItem, setSelectedItem]   = useState<ReviewItem | null>(null);

  // ── Queries ────────────────────────────────────────────────────────────────

  const { data: existingCases = [] } = useQuery({
    queryKey: ['cases', 'client', user?.id],
    queryFn:  () => casesService.getCasesByClientId(user!.id),
    enabled:  !!user,
  });

  const firstCaseId = existingCases[0]?.id;

  const { data: reusedForms = [] } = useQuery({
    queryKey: ['forms', 'case', firstCaseId],
    queryFn:  () => formsService.getFormsByCase(firstCaseId!),
    enabled:  !!firstCaseId && step === 'review',
  });

  const { data: reusedDocs = [] } = useQuery({
    queryKey: ['documents', firstCaseId],
    queryFn:  () => documentsService.getDocumentsByCase(firstCaseId!),
    enabled:  !!firstCaseId && step === 'review',
  });

  // ── Derived ────────────────────────────────────────────────────────────────

  const existingProducts  = new Set(existingCases.flatMap(c => c.products));
  const availableProducts = ALL_PRODUCTS.filter(p => !existingProducts.has(p));

  // Source account name (where reused data comes from)
  const sourceCase = existingCases.find(c => c.status === 'completed') ?? existingCases[0];
  const sourceAccountName = sourceCase
    ? `${PRODUCT_LABELS[sourceCase.products[0]]} Account`
    : 'Existing Account';

  // Target product name(s) being added
  const targetProductName = selected.length === 1
    ? PRODUCT_LABELS[selected[0]]
    : `${selected.map(p => PRODUCT_LABELS[p]).join(' & ')}`;

  // ── Copied items (already exist in source case) ──────────────────────────

  const copiedFormItems: ReviewItem[] = reusedForms.map(f => {
    const meta = FORM_META[f.type];
    return {
      id:          f.id,
      kind:        'form',
      rawType:     f.type,
      label:       meta?.label       ?? f.type,
      description: meta?.description ?? '',
      icon:        meta?.icon        ?? <IconFileText size={16} />,
      payload:     f.data as unknown as Record<string, unknown>,
    };
  });

  const copiedDocItems: ReviewItem[] = reusedDocs.map(d => {
    const meta = DOC_META[d.type];
    return {
      id:          d.id,
      kind:        'doc',
      rawType:     d.type,
      label:       meta?.label       ?? (d.type as string).replace(/_/g, ' '),
      description: meta?.description ?? '',
      icon:        meta?.icon        ?? <IconFileText size={16} />,
      payload:     { fileName: d.fileName, fileSize: d.fileSize, uploadedAt: d.uploadedAt, status: d.status, extractedData: d.extractedData },
    };
  });

  // ── Required items (not covered by reused data — need action) ─────────────

  const reusedFormTypes = new Set(reusedForms.map(f => f.type as string));
  const requiredFormItems: ReviewItem[] = REQUIRED_FORM_TYPES
    .filter(type => !reusedFormTypes.has(type))
    .map(type => {
      const meta = FORM_META[type];
      return {
        id:          `required-form-${type}`,
        kind:        'required-form' as const,
        rawType:     type,
        label:       meta?.label       ?? type,
        description: meta?.description ?? '',
        icon:        meta?.icon        ?? <IconFileText size={16} />,
        payload:     {},
      };
    });

  const reusedDocTypes = new Set(reusedDocs.map(d => d.type as string));
  const requiredDocItems: ReviewItem[] = REQUIRED_DOC_TYPES
    .filter(type => !reusedDocTypes.has(type))
    .map(type => {
      const meta = DOC_META[type];
      return {
        id:          `required-doc-${type}`,
        kind:        'required-doc' as const,
        rawType:     type,
        label:       meta?.label       ?? type.replace(/_/g, ' '),
        description: meta?.description ?? '',
        icon:        meta?.icon        ?? <IconFileText size={16} />,
        payload:     {},
      };
    });

  // ── Mutation ───────────────────────────────────────────────────────────────

  const submitMutation = useMutation({
    mutationFn: () =>
      casesService.submitMultipleCases({
        clientId:   user!.id,
        clientName: user!.fullName,
        products:   selected,
        entityId:   existingCases[0]?.entityId,
      }),
    onSuccess: created => {
      queryClient.invalidateQueries({ queryKey: ['cases', 'client', user?.id] });
      if (created.length === 1) {
        navigate(`/client/applications/${created[0].id}?onboarding=1`);
      } else {
        navigate('/client/dashboard');
      }
    },
  });

  const toggle = (p: ProductType) =>
    setSelected(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);

  // ── Review step — full-screen "Getting Started" ────────────────────────────

  if (step === 'review') {
    return (
      <div className="fixed inset-0 z-50 bg-bg-base flex flex-col overflow-hidden">

        {/* Header */}
        <header className="flex-shrink-0 h-14 bg-bg-surface border-b border-border-default flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-3">
            <button className="text-text-muted hover:text-text-primary transition-colors">
              <IconMenu2 size={20} />
            </button>
            <div className="flex items-center gap-2">
              <IconBuildingBank size={20} className="text-primary flex-shrink-0" />
              <span className="text-sm font-bold text-text-primary whitespace-nowrap">ClearPath Client Portal</span>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 h-8 rounded-lg border border-primary text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">
            <IconHeadset size={14} /> Contact us
          </button>
        </header>

        {/* Sub-header breadcrumb */}
        <div className="h-11 bg-bg-surface border-b border-border-default flex items-center gap-4 px-6 flex-shrink-0">
          <span className="text-sm font-bold text-text-primary whitespace-nowrap">AIB Investments Pvt. Ltd.</span>
          <nav className="flex items-center gap-1.5 text-xs">
            <Link to="/client/dashboard" className="text-primary hover:underline">Home</Link>
            <IconChevronRight size={11} className="text-text-muted" />
            <button type="button" onClick={() => setStep('select')} className="text-primary hover:underline">
              Add New Product
            </button>
            <IconChevronRight size={11} className="text-text-muted" />
            <span className="text-text-secondary">Getting Started</span>
          </nav>
        </div>

        {/* Body — flex row: left content + right detail panel */}
        <div className="flex-1 flex overflow-hidden">

          {/* Left: scrollable content */}
          <main className={`${selectedItem ? 'w-1/2' : 'flex-1'} overflow-y-auto`}>
            <div className="py-10 px-8 pb-32 max-w-2xl">

              {/* Page heading */}
              <div className="mb-8">
                <h1 className="text-2xl font-bold text-text-primary mb-2">Getting Started</h1>
                <p className="text-sm text-text-secondary leading-relaxed">
                  We found forms and documents from your existing accounts that can be used for{' '}
                  <span className="text-text-primary font-medium">
                    {selected.map(p => PRODUCT_LABELS[p]).join(', ')}
                  </span>.
                  These items have been automatically copied — you won't need to fill them out or upload them again.
                </p>
                <p className="text-sm text-text-secondary mt-2">
                  Click any item to preview its contents, then confirm to proceed.
                </p>
              </div>

              {/* Forms section */}
              {(copiedFormItems.length > 0 || requiredFormItems.length > 0) && (
                <div className="mb-6 space-y-3">
                  <h2 className="text-base font-semibold text-text-primary">Forms</h2>
                  {copiedFormItems.length > 0 && (
                    <CopiedGroup
                      variant="copied"
                      title={`Copied over from ${sourceAccountName}`}
                      items={copiedFormItems}
                      selectedId={selectedItem?.id ?? null}
                      onSelect={item => setSelectedItem(prev => prev?.id === item.id ? null : item)}
                    />
                  )}
                  {requiredFormItems.length > 0 && (
                    <CopiedGroup
                      variant="required"
                      title={`Required only for ${targetProductName}`}
                      items={requiredFormItems}
                      selectedId={selectedItem?.id ?? null}
                      onSelect={item => setSelectedItem(prev => prev?.id === item.id ? null : item)}
                    />
                  )}
                </div>
              )}

              {/* Documents section */}
              {(copiedDocItems.length > 0 || requiredDocItems.length > 0) && (
                <div className="mb-8 space-y-3">
                  <h2 className="text-base font-semibold text-text-primary">Documents</h2>
                  {copiedDocItems.length > 0 && (
                    <CopiedGroup
                      variant="copied"
                      title={`Copied over from ${sourceAccountName}`}
                      items={copiedDocItems}
                      selectedId={selectedItem?.id ?? null}
                      onSelect={item => setSelectedItem(prev => prev?.id === item.id ? null : item)}
                    />
                  )}
                  {requiredDocItems.length > 0 && (
                    <CopiedGroup
                      variant="required"
                      title={`Required only for ${targetProductName}`}
                      items={requiredDocItems}
                      selectedId={selectedItem?.id ?? null}
                      onSelect={item => setSelectedItem(prev => prev?.id === item.id ? null : item)}
                    />
                  )}
                </div>
              )}

              {copiedFormItems.length === 0 && requiredFormItems.length === 0 &&
               copiedDocItems.length === 0 && requiredDocItems.length === 0 && (
                <div className="py-10 text-center bg-bg-surface border border-border-default rounded-xl mb-8">
                  <p className="text-sm text-text-muted">No existing forms or documents found.</p>
                  <p className="text-xs text-text-muted mt-1">You'll complete these after the account is opened.</p>
                </div>
              )}

              {/* Confirmation */}
              <div className="bg-bg-surface border border-border-default rounded-xl p-5">
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">Confirmation</p>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={e => setConfirmed(e.target.checked)}
                    className="mt-0.5 w-4 h-4 rounded border-border-default accent-primary flex-shrink-0"
                  />
                  <span className="text-sm text-text-secondary leading-relaxed">
                    I confirm that I have reviewed the forms and documents listed above and agree to
                    proceed with adding{' '}
                    <span className="text-text-primary font-medium">
                      {selected.map(p => PRODUCT_LABELS[p]).join(', ')}
                    </span>{' '}
                    to my account. I understand that the reused items will be automatically applied
                    to the new application.
                  </span>
                </label>
              </div>

              {submitMutation.isError && (
                <p className="mt-4 text-sm text-danger">Failed to submit. Please try again.</p>
              )}

            </div>
          </main>

          {/* Right: detail panel (slides in) */}
          {selectedItem && (
            <aside className="w-1/2 flex-shrink-0 border-l border-border-default bg-bg-surface flex flex-col overflow-hidden">
              <DetailPanel item={selectedItem} onClose={() => setSelectedItem(null)} />
            </aside>
          )}
        </div>

        {/* Fixed footer */}
        <footer className="fixed bottom-0 left-0 right-0 h-16 bg-bg-surface border-t border-border-default flex items-center justify-end gap-3 px-10 z-20">
          <button
            type="button"
            onClick={() => { setStep('select'); setConfirmed(false); setSelectedItem(null); }}
            className="px-5 h-9 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-primary transition-colors"
          >
            Back
          </button>
          <button
            type="button"
            onClick={() => submitMutation.mutate()}
            disabled={!confirmed || submitMutation.isPending}
            className="flex items-center gap-2 px-6 h-9 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
          >
            {submitMutation.isPending && <IconLoader2 size={15} className="animate-spin" />}
            {submitMutation.isPending ? 'Submitting…' : 'Confirm & Continue'}
          </button>
        </footer>

      </div>
    );
  }

  // ── Select step — product selection grid ──────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Add New Product</h1>
      <p className="text-sm text-text-secondary mb-6">
        Select a product to add to your existing account. Your entity information and documents
        on file will be reused — no need to re-submit them.
      </p>

      {existingProducts.size > 0 && (
        <div className="mb-5 px-3 py-2 rounded-lg bg-bg-elevated border border-border-default text-xs text-text-muted">
          Already active:{' '}
          {[...existingProducts].map(p => PRODUCT_LABELS[p]).join(', ')}
        </div>
      )}

      {availableProducts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 bg-bg-surface border border-border-default rounded-xl text-center gap-3">
          <p className="text-text-secondary text-sm">You already have all available products.</p>
          <button type="button" onClick={() => navigate('/client/dashboard')} className="text-sm text-primary hover:underline">
            Back to dashboard →
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
            {availableProducts.map(p => {
              const isSelected = selected.includes(p);
              return (
                <button
                  key={p}
                  type="button"
                  onClick={() => toggle(p)}
                  className={[
                    'text-left p-4 rounded-lg border-2 transition-all duration-150',
                    isSelected
                      ? 'border-primary bg-primary-subtle ring-2 ring-primary/20'
                      : 'border-border-default bg-bg-surface hover:border-primary/50 hover:bg-bg-elevated',
                  ].join(' ')}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <span className="text-sm font-semibold text-text-primary">{PRODUCT_LABELS[p]}</span>
                    <div className={[
                      'w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors',
                      isSelected ? 'border-primary bg-primary' : 'border-border-default bg-bg-elevated',
                    ].join(' ')}>
                      {isSelected && <IconCheck size={10} className="text-white" strokeWidth={3} />}
                    </div>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed">{PRODUCT_DESCRIPTIONS[p]}</p>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => setStep('review')}
            disabled={selected.length === 0}
            className="flex items-center justify-center gap-2 w-full h-10 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
          >
            {selected.length === 0
              ? 'Select a product to continue'
              : `Continue with ${selected.length === 1 ? PRODUCT_LABELS[selected[0]] : `${selected.length} products`}`
            }
          </button>
        </>
      )}
    </div>
  );
}
