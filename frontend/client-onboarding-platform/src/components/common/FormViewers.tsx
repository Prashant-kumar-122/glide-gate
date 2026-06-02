import type { EnrollmentFormData, CDDFormData, ControlPersonFormData } from '../../types';

// ─── Read-only field ──────────────────────────────────────────────────────────

export function Field({
  label,
  value,
  span = 1,
}: {
  label: string;
  value: string | number | boolean | undefined;
  span?: number;
}) {
  const display =
    value === undefined || value === ''
      ? '—'
      : typeof value === 'boolean'
      ? value ? 'Yes' : 'No'
      : String(value);

  return (
    <div className={span === 2 ? 'col-span-2' : ''}>
      <p className="text-xs text-text-muted mb-0.5">{label}</p>
      <p className="text-sm text-text-primary font-medium">{display}</p>
    </div>
  );
}

// ─── Sub-section label ────────────────────────────────────────────────────────

function SubHeading({ label }: { label: string }) {
  return (
    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider pt-2 pb-1 border-t border-border-subtle col-span-2">
      {label}
    </p>
  );
}

// ─── Enrollment form ──────────────────────────────────────────────────────────

export function EnrollmentFormViewer({ data }: { data: EnrollmentFormData }) {
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-4">
      <SubHeading label="Entity Details" />
      <Field label="Legal Name"            value={data.legalName} />
      <Field label="Tax ID (EIN)"          value={data.taxId} />
      <Field label="Business Type"         value={data.businessType} />
      <Field label="Incorporation State"   value={data.incorporationState} />
      <Field label="Incorporation Date"    value={data.incorporationDate} />

      <SubHeading label="Registered Address" />
      <Field label="Street Line 1"  value={data.address.line1} />
      {data.address.line2 && <Field label="Suite / Unit" value={data.address.line2} />}
      <Field label="City"           value={data.address.city} />
      <Field label="State"          value={data.address.state} />
      <Field label="ZIP Code"       value={data.address.zip} />
      <Field label="Country"        value={data.address.country} />

      <SubHeading label="Primary Contact" />
      <Field label="Full Name"  value={data.primaryContact.fullName} />
      <Field label="Title"      value={data.primaryContact.title} />
      <Field label="Email"      value={data.primaryContact.email} />
      <Field label="Phone"      value={data.primaryContact.phone} />
    </div>
  );
}

// ─── CDD form ─────────────────────────────────────────────────────────────────

export function CDDFormViewer({ data }: { data: CDDFormData }) {
  return (
    <div className="grid grid-cols-2 gap-x-8 gap-y-4">
      <Field label="Nature of Business"       value={data.natureOfBusiness}    span={2} />
      <Field label="Source of Funds"          value={data.sourceOfFunds} />
      <Field label="Expected Trading Volume"  value={data.expectedTradingVolume} />
      <Field label="Operating Jurisdictions"  value={data.jurisdictions.join(', ')} span={2} />
      <Field label="PEP Status"               value={data.pepStatus} />
      <Field label="Sanctions Status"         value={data.sanctionsStatus} />
    </div>
  );
}

// ─── Control Person form ──────────────────────────────────────────────────────

export function ControlPersonFormViewer({ data }: { data: ControlPersonFormData }) {
  return (
    <div className="space-y-4">
      {data.controlPersons.map((p, i) => (
        <div key={i} className="rounded-lg border border-border-subtle bg-bg-base p-4">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Control Person {i + 1}
            <span className="ml-2 font-normal normal-case text-text-muted">
              — {p.ownershipPercentage}% ownership
            </span>
          </p>
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            <Field label="Full Name"   value={p.fullName} />
            <Field label="Title"       value={p.title} />
            <Field label="Date of Birth" value={p.dateOfBirth} />
            <Field label="Nationality" value={p.nationality} />
            <Field label="ID Type"     value={p.idDocumentType} />
            <Field label="ID Number"   value={p.idDocumentNumber} />
          </div>
        </div>
      ))}
    </div>
  );
}
