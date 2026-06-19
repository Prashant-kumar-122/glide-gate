#!/usr/bin/env python3
"""
Generate demo KYC documents for GlideGate demo scenarios.

No external dependencies  - uses a minimal PDF 1.4 writer in pure Python.

Usage (from project root):
    python scripts/generate_demo_docs.py

Output:
    docs/demo/documents/positive/   - Valid documents (Scenario A happy path)
    docs/demo/documents/negative/   - Invalid documents (Scenario B escalation)
"""
from __future__ import annotations
from pathlib import Path
from datetime import date, timedelta

TODAY = date.today()


def fmt(d: date) -> str:
    return d.strftime("%d %B %Y")


# ─── Minimal PDF 1.4 writer ───────────────────────────────────────────────────

def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class PDF:
    """
    Minimal PDF 1.4 writer.
    Supports: text (Helvetica regular/bold), horizontal rules, multi-page.
    Object layout: 1=Catalog, 2=Pages, 3=Font/Reg, 4=Font/Bold, 5+=content+pages.
    """

    def __init__(self) -> None:
        self._objs: dict[int, bytes] = {}
        self._next_id = 3
        self._page_ids: list[int] = []
        self._font_reg: int | None = None
        self._font_bold: int | None = None

    # ── object allocation ──────────────────────────────────────────────────

    def _alloc(self, body: str | bytes) -> int:
        oid = self._next_id
        self._next_id += 1
        self._objs[oid] = body if isinstance(body, bytes) else body.encode("latin-1")
        return oid

    def _ensure_fonts(self) -> tuple[int, int]:
        if self._font_reg is None:
            self._font_reg = self._alloc(
                "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
                " /Encoding /WinAnsiEncoding >>"
            )
            self._font_bold = self._alloc(
                "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold"
                " /Encoding /WinAnsiEncoding >>"
            )
        return self._font_reg, self._font_bold  # type: ignore[return-value]

    # ── text wrapping ──────────────────────────────────────────────────────

    @staticmethod
    def _wrap(text: str, cols: int = 88) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        cur: list[str] = []
        cur_len = 0
        for w in words:
            need = len(w) + (1 if cur else 0)
            if cur_len + need > cols:
                lines.append(" ".join(cur))
                cur, cur_len = [w], len(w)
            else:
                cur.append(w)
                cur_len += need
        if cur:
            lines.append(" ".join(cur))
        return lines

    # ── page rendering ────────────────────────────────────────────────────

    def add_page(self, elements: list[dict]) -> "PDF":
        """
        Element types:
          title    text                     - 18 pt bold, followed by rule
          subtitle text                     - 9 pt regular
          h2       text                     - 13 pt bold section header
          text     text                     - 11 pt regular, auto-wrapped
          bold     text                     - 11 pt bold, auto-wrapped
          small    text                     - 9 pt regular, auto-wrapped
          kv       key / value              - key (bold, x=50) : value (regular, x=220)
          ruler                             - horizontal line
          spacer   size=14 (optional)       - vertical gap
        """
        fr, fb = self._ensure_fonts()
        ops: list[str] = []
        y = 790.0

        def text_op(txt: str, x: float, size: int, bold: bool) -> None:
            nonlocal y
            f = "/F2" if bold else "/F1"
            ops.append(f"BT {f} {size} Tf {x:.1f} {y:.1f} Td ({_esc(txt)}) Tj ET")
            y -= size * 1.45

        def rule_op() -> None:
            nonlocal y
            ops.append(f"0.4 w 50 {y + 2:.1f} m 562 {y + 2:.1f} l S")
            y -= 10

        for el in elements:
            t = el.get("type", "text")

            if t == "title":
                text_op(el["text"], 50, 18, True)
                y -= 2
                rule_op()
                y -= 4

            elif t == "subtitle":
                text_op(el["text"], 50, 9, False)
                y -= 2

            elif t == "h2":
                y -= 5
                text_op(el["text"], 50, 13, True)
                y -= 3

            elif t == "text":
                for line in self._wrap(el["text"]):
                    text_op(line, 50, 11, False)

            elif t == "bold":
                for line in self._wrap(el["text"]):
                    text_op(line, 50, 11, True)

            elif t == "small":
                for line in self._wrap(el["text"], 100):
                    text_op(line, 50, 9, False)

            elif t == "kv":
                saved = y
                text_op(el["key"] + ":", 50, 11, True)
                y = saved
                text_op(el["value"], 220, 11, False)

            elif t == "ruler":
                rule_op()

            elif t == "spacer":
                y -= el.get("size", 14)

        stream = "\n".join(ops).encode("latin-1")
        cid = self._alloc(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )
        pid = self._alloc(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Contents {cid} 0 R "
            f"/Resources << /Font << /F1 {fr} 0 R /F2 {fb} 0 R >> >> >>"
        )
        self._page_ids.append(pid)
        return self

    # ── serialisation ──────────────────────────────────────────────────────

    def to_bytes(self) -> bytes:
        buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n\n")
        offsets: dict[int, int] = {}

        def write_obj(oid: int, body: bytes | str) -> None:
            offsets[oid] = len(buf)
            buf.extend(f"{oid} 0 obj\n".encode())
            buf.extend(body if isinstance(body, (bytes, bytearray)) else body.encode("latin-1"))
            buf.extend(b"\nendobj\n\n")

        kids = " ".join(f"{p} 0 R" for p in self._page_ids)
        write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        write_obj(
            2,
            f"<< /Type /Pages /Kids [{kids}] /Count {len(self._page_ids)} >>",
        )
        for oid in sorted(self._objs):
            write_obj(oid, self._objs[oid])

        total = 2 + len(self._objs)
        xref_pos = len(buf)
        buf.extend(f"xref\n0 {total + 1}\n".encode())
        buf.extend(b"0000000000 65535 f \n")
        for i in range(1, total + 1):
            buf.extend(f"{offsets.get(i, 0):010d} 00000 n \n".encode())
        buf.extend(
            f"trailer\n<< /Size {total + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode()
        )
        return bytes(buf)


# ─── Shared footer ────────────────────────────────────────────────────────────

_DEMO_NOTE = (
    "DEMO DOCUMENT  - Generated for GlideGate demonstration purposes only. "
    "Not a genuine legal, financial, or official document."
)


# ─── Positive documents ───────────────────────────────────────────────────────

def doc_passport_valid() -> PDF:
    issue = TODAY - timedelta(days=365 * 2)
    expiry = issue + timedelta(days=365 * 10)
    mrz_exp = expiry.strftime("%y%m%d")
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "UNITED KINGDOM PASSPORT"},
            {"type": "subtitle", "text": "Her Majesty's Passport Office  - ICAO 9303 Travel Document"},
            {"type": "spacer"},
            {"type": "h2", "text": "Personal Information"},
            {"type": "kv", "key": "Surname", "value": "MEHTA"},
            {"type": "kv", "key": "Given Names", "value": "AARAV"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Place of Birth", "value": "Mumbai, India"},
            {"type": "kv", "key": "Nationality", "value": "British Citizen"},
            {"type": "kv", "key": "Sex", "value": "M"},
            {"type": "spacer"},
            {"type": "h2", "text": "Document Details"},
            {"type": "kv", "key": "Passport Number", "value": "P1234567"},
            {"type": "kv", "key": "Date of Issue", "value": fmt(issue)},
            {"type": "kv", "key": "Date of Expiry", "value": fmt(expiry)},
            {"type": "kv", "key": "Issuing Authority", "value": "HM Passport Office, United Kingdom"},
            {"type": "spacer"},
            {"type": "h2", "text": "Biometric and Photo Data"},
            {"type": "kv", "key": "Photograph", "value": "Colour photograph of holder present (page 2)"},
            {"type": "kv", "key": "Biometric Data", "value": "RFID chip present  - facial biometric data stored (ICAO 9303 Part 9)"},
            {"type": "kv", "key": "Chip Standard", "value": "ePassport  - LDS1 Application (ICAO 9303 compliant)"},
            {"type": "kv", "key": "Facial Recognition", "value": "Enrolled  - biometric template on chip verified at issuance"},
            {"type": "spacer"},
            {"type": "h2", "text": "Machine Readable Zone (MRZ)"},
            {"type": "small", "text": "P<GBRMEHTA<<AARAV<<<<<<<<<<<<<<<<<<<<<<<<<<<"},
            {"type": "small", "text": f"P1234567<GBR8503152M{mrz_exp}<<<<<<0"},
            {"type": "spacer", "size": 20},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Expires " + fmt(expiry)},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_driving_licence_valid() -> PDF:
    issue = TODAY - timedelta(days=365 * 3)
    expiry = TODAY + timedelta(days=365 * 7)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "DRIVER AND VEHICLE LICENSING AGENCY"},
            {"type": "subtitle", "text": "Great Britain Driving Licence  - Categories B, B1"},
            {"type": "spacer"},
            {"type": "h2", "text": "Holder Details"},
            {"type": "kv", "key": "Surname", "value": "MEHTA"},
            {"type": "kv", "key": "First Names", "value": "AARAV"},
            {"type": "kv", "key": "Date of Birth", "value": "15/03/1985"},
            {"type": "kv", "key": "Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "spacer"},
            {"type": "h2", "text": "Licence Details"},
            {"type": "kv", "key": "Licence Number", "value": "MEHTA850315AM9AB"},
            {"type": "kv", "key": "Date of Issue", "value": fmt(issue)},
            {"type": "kv", "key": "Valid Until", "value": fmt(expiry)},
            {"type": "kv", "key": "Issuing Authority", "value": "DVLA, Swansea, SA99 1AB"},
            {"type": "spacer"},
            {"type": "h2", "text": "Entitlements"},
            {"type": "kv", "key": "Category B", "value": "Motor vehicles  - Valid from 15/03/2003"},
            {"type": "kv", "key": "Category B1", "value": "Light quadricycles  - Valid from 15/03/2003"},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Full UK driving licence"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_bank_statement_valid() -> PDF:
    stmt_from = TODAY - timedelta(days=90)
    stmt_to = TODAY - timedelta(days=1)

    def d(offset_days: int) -> str:
        return (stmt_from + timedelta(days=offset_days)).strftime("%d %b %Y")

    return (
        PDF()
        .add_page([
            {"type": "title", "text": "Barclays Bank PLC  - Statement of Account"},
            {"type": "subtitle", "text": "Premier Banking  - Personal Current Account"},
            {"type": "spacer"},
            {"type": "h2", "text": "Account Holder Information"},
            {"type": "kv", "key": "Account Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Sort Code", "value": "20-00-00"},
            {"type": "kv", "key": "Account Number", "value": "12345678"},
            {"type": "kv", "key": "Account Type", "value": "Premier Current Account"},
            {"type": "kv", "key": "Statement Period", "value": f"{fmt(stmt_from)} to {fmt(stmt_to)}"},
            {"type": "spacer"},
            {"type": "kv", "key": "Opening Balance", "value": "GBP 24,350.00 CR"},
            {"type": "spacer"},
            {"type": "h2", "text": "Transactions"},
            {"type": "ruler"},
        ])
        .add_page([
            {"type": "kv", "key": "DATE", "value": "DESCRIPTION                          DEBIT       CREDIT      BALANCE"},
            {"type": "ruler"},
            {"type": "kv", "key": d(5),  "value": "SALARY TECHVISION LTD                            7,916.67    32,266.67"},
            {"type": "kv", "key": d(7),  "value": "MORTGAGE LLOYDS BANK           1,850.00                       30,416.67"},
            {"type": "kv", "key": d(8),  "value": "DIRECT DEBIT COUNCIL TAX          250.00                       30,166.67"},
            {"type": "kv", "key": d(10), "value": "TRANSFER SAVINGS ACCOUNT         2,000.00                      28,166.67"},
            {"type": "kv", "key": d(35), "value": "SALARY TECHVISION LTD                            7,916.67    36,083.34"},
            {"type": "kv", "key": d(37), "value": "MORTGAGE LLOYDS BANK           1,850.00                       34,233.34"},
            {"type": "kv", "key": d(40), "value": "DIRECT DEBIT COUNCIL TAX          250.00                       33,983.34"},
            {"type": "kv", "key": d(65), "value": "SALARY TECHVISION LTD                            7,916.67    41,900.01"},
            {"type": "kv", "key": d(67), "value": "MORTGAGE LLOYDS BANK           1,850.00                       40,050.01"},
            {"type": "kv", "key": d(70), "value": "DIRECT DEBIT COUNCIL TAX          250.00                       39,800.01"},
            {"type": "ruler"},
            {"type": "ruler"},
            {"type": "kv", "key": "Closing Balance", "value": "GBP 39,800.01 CR (as of " + fmt(stmt_to) + ")"},
            {"type": "spacer"},
            {"type": "h2", "text": "Income Analysis"},
            {"type": "kv", "key": "Account Holder", "value": "Aarav Mehta (matches client name)"},
            {"type": "kv", "key": "Total Credits (3 months)", "value": "GBP 23,750.01"},
            {"type": "kv", "key": "Average Monthly Credit", "value": "GBP 7,916.67"},
            {"type": "kv", "key": "Annualised Income (estimate)", "value": "GBP 95,000.04"},
            {"type": "spacer"},
            {"type": "h2", "text": "Document Integrity"},
            {"type": "kv", "key": "Document Origin", "value": "Original statement issued directly by Barclays Bank PLC"},
            {"type": "kv", "key": "Alteration / Tampering", "value": "No evidence of alteration or tampering detected"},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Income consistent with declared GBP 95,000 p.a."},
            {"type": "small", "text": "Barclays Bank PLC. Authorised by the PRA and regulated by the FCA and PRA. " + _DEMO_NOTE},
        ])
    )


def doc_payslip_valid() -> PDF:
    last_month = (TODAY.replace(day=1) - timedelta(days=1))
    period = last_month.strftime("%B %Y")
    gross = 7916.67
    tax = 2166.67
    ni = 516.67
    pension = 395.83
    net = gross - tax - ni - pension
    ytd_months = last_month.month
    return (
        PDF()
        .add_page([
            {"type": "title", "text": f"PAYSLIP  - {period}"},
            {"type": "subtitle", "text": "TechVision Ltd  - HR & Payroll Services"},
            {"type": "spacer"},
            {"type": "h2", "text": "Employee Details"},
            {"type": "kv", "key": "Account Holder / Employee Name", "value": "Aarav Mehta (matches client name)"},
            {"type": "kv", "key": "Employee ID", "value": "EMP-00823"},
            {"type": "kv", "key": "Department", "value": "Software Engineering"},
            {"type": "kv", "key": "Job Title", "value": "Senior Software Engineer"},
            {"type": "kv", "key": "Bank / Institution Name", "value": "TechVision Ltd (Issuing Employer)"},
            {"type": "kv", "key": "NI Number", "value": "AB 12 34 56 C"},
            {"type": "kv", "key": "Tax Code", "value": "1257L"},
            {"type": "kv", "key": "Statement Period", "value": period},
            {"type": "kv", "key": "Pay Date", "value": fmt(last_month)},
            {"type": "spacer"},
            {"type": "h2", "text": "Earnings"},
            {"type": "kv", "key": "Basic Salary", "value": f"GBP {gross:,.2f}  (Annual: GBP 95,000.00)"},
            {"type": "spacer"},
            {"type": "h2", "text": "Deductions"},
            {"type": "kv", "key": "Income Tax (PAYE)", "value": f"GBP {tax:,.2f}"},
            {"type": "kv", "key": "National Insurance", "value": f"GBP {ni:,.2f}"},
            {"type": "kv", "key": "Pension (5% employee)", "value": f"GBP {pension:,.2f}"},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "NET PAY", "value": f"GBP {net:,.2f}"},
            {"type": "kv", "key": "Closing Balance / Net Pay", "value": f"GBP {net:,.2f}"},
            {"type": "ruler"},
            {"type": "spacer"},
            {"type": "h2", "text": "Year to Date"},
            {"type": "kv", "key": "Gross YTD", "value": f"GBP {gross * ytd_months:,.2f}"},
            {"type": "kv", "key": "Tax YTD", "value": f"GBP {tax * ytd_months:,.2f}"},
            {"type": "spacer"},
            {"type": "h2", "text": "Document Integrity"},
            {"type": "kv", "key": "Alteration / Tampering", "value": "No evidence of alteration or tampering. Original payslip issued by TechVision Ltd."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": f"VALID  - Issued {fmt(last_month)} (within 30 days)"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_power_of_attorney_valid() -> PDF:
    signed = TODAY - timedelta(days=30)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "LASTING POWER OF ATTORNEY"},
            {"type": "subtitle", "text": "Property and Financial Affairs  - Office of the Public Guardian"},
            {"type": "spacer"},
            {"type": "h2", "text": "Parties"},
            {"type": "kv", "key": "Donor (Principal)", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Donor Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "kv", "key": "Attorney (Agent)", "value": "Priya Mehta"},
            {"type": "kv", "key": "Attorney Address", "value": "45 Regent Street, London, W1B 4HQ"},
            {"type": "spacer"},
            {"type": "h2", "text": "Grant of Authority"},
            {"type": "text", "text": "I, Aarav Mehta, hereby appoint Priya Mehta to act as my attorney in all "
                                      "matters relating to my property and financial affairs, including: managing "
                                      "and operating bank accounts and investments; buying, selling, and "
                                      "transferring financial instruments; entering into contracts and agreements; "
                                      "and acting in any financial matter as I would act personally."},
            {"type": "spacer"},
            {"type": "h2", "text": "Conditions and Restrictions"},
            {"type": "text", "text": "This LPA shall remain in force unless revoked in writing by the Donor, "
                                      "or upon the death of either party. The attorney must keep accounts and "
                                      "act in the donor's best interests at all times."},
            {"type": "spacer"},
            {"type": "h2", "text": "Execution"},
            {"type": "kv", "key": "Signed by Donor", "value": "Aarav Mehta (signed)"},
            {"type": "kv", "key": "Signed by Attorney", "value": "Priya Mehta (signed)"},
            {"type": "kv", "key": "Date of Execution", "value": fmt(signed)},
            {"type": "kv", "key": "Witness", "value": "James Crawford, Solicitor, Crawford & Partners LLP"},
            {"type": "kv", "key": "Witness Signature", "value": "J. Crawford (signed)"},
            {"type": "spacer"},
            {"type": "h2", "text": "Jurisdiction and Validity"},
            {"type": "kv", "key": "Governing Jurisdiction", "value": "England and Wales"},
            {"type": "kv", "key": "Applicable Law", "value": "Mental Capacity Act 2005 and Lasting Powers of Attorney Regulations 2007"},
            {"type": "kv", "key": "Document Expiry", "value": "No fixed expiry date  - document is not expired. Valid indefinitely unless revoked."},
            {"type": "spacer"},
            {"type": "h2", "text": "Registration"},
            {"type": "kv", "key": "OPG Reference", "value": f"LPA-{signed.year}-78923"},
            {"type": "kv", "key": "Registered", "value": fmt(signed + timedelta(days=7))},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Registered with the Office of the Public Guardian"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_insurance_policy_valid() -> PDF:
    start = TODAY - timedelta(days=200)
    end = start + timedelta(days=365)
    last_pmt = TODAY - timedelta(days=30)
    next_pmt = TODAY + timedelta(days=30)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "INSURANCE POLICY CERTIFICATE"},
            {"type": "subtitle", "text": "Aviva Insurance Ltd  - Income Protection Insurance"},
            {"type": "spacer"},
            {"type": "h2", "text": "Policy Details"},
            {"type": "kv", "key": "Policy Number", "value": "AVV-2024-INC-98765"},
            {"type": "kv", "key": "Policy Type", "value": "Income Protection Insurance  - Income Shield Plus"},
            {"type": "spacer"},
            {"type": "h2", "text": "Insured Person"},
            {"type": "kv", "key": "Policyholder Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "spacer"},
            {"type": "h2", "text": "Coverage Information"},
            {"type": "kv", "key": "Sum Assured / Cover Amount", "value": "GBP 47,500 per annum (50% of declared salary)"},
            {"type": "kv", "key": "Deferred Period", "value": "3 months"},
            {"type": "kv", "key": "Coverage Start Date", "value": fmt(start)},
            {"type": "kv", "key": "Coverage End Date", "value": fmt(end)},
            {"type": "kv", "key": "Annual Premium", "value": "GBP 1,140.00"},
            {"type": "spacer"},
            {"type": "h2", "text": "Insurer Details"},
            {"type": "kv", "key": "Insurer Name", "value": "Aviva Insurance Ltd"},
            {"type": "kv", "key": "FCA Registration", "value": "FRN 185836"},
            {"type": "spacer"},
            {"type": "h2", "text": "Premium Status"},
            {"type": "kv", "key": "Last Payment", "value": fmt(last_pmt) + "  - GBP 95.00 (monthly)"},
            {"type": "kv", "key": "Next Payment Due", "value": fmt(next_pmt)},
            {"type": "kv", "key": "Payment Status", "value": "UP TO DATE"},
            {"type": "kv", "key": "Policy Status", "value": "Active  - Policy is not expired. Coverage in force until " + fmt(end)},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Active coverage in force until " + fmt(end)},
            {"type": "small", "text": "Aviva Insurance Ltd. Authorised by the PRA and regulated by the FCA and PRA (FRN 185836). " + _DEMO_NOTE},
        ])
    )


def doc_kyc_form_complete() -> PDF:
    signed = TODAY - timedelta(days=7)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "KNOW YOUR CUSTOMER (KYC) FORM"},
            {"type": "subtitle", "text": "GlideGate Wealth Management Ltd  - Client Identification Form (CIF)"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section A  - Personal Information"},
            {"type": "kv", "key": "Client Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Full Legal Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Place of Birth", "value": "Mumbai, India"},
            {"type": "kv", "key": "Nationality", "value": "British"},
            {"type": "kv", "key": "Passport Number", "value": "P1234567"},
            {"type": "kv", "key": "Residential Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "kv", "key": "Email", "value": "aarav.mehta@example.com"},
            {"type": "kv", "key": "Phone", "value": "+44 7700 900123"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section B  - Employment & Financial Information"},
            {"type": "kv", "key": "Occupation", "value": "Software Engineer"},
            {"type": "kv", "key": "Employer", "value": "TechVision Ltd"},
            {"type": "kv", "key": "Annual Income", "value": "GBP 95,000"},
            {"type": "kv", "key": "Source of Funds", "value": "Employment income and accumulated savings"},
            {"type": "kv", "key": "Source of Wealth", "value": "Earnings from employment over 10+ years with TechVision Ltd"},
        ])
        .add_page([
            {"type": "h2", "text": "Section C  - Tax Information"},
            {"type": "kv", "key": "Tax Residency", "value": "United Kingdom"},
            {"type": "kv", "key": "TIN / Tax Identification Number (NI)", "value": "AB 12 34 56 C"},
            {"type": "kv", "key": "US Person (FATCA)", "value": "No"},
            {"type": "kv", "key": "Reportable Jurisdictions (CRS)", "value": "None"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section D  - PEP / AML Screening"},
            {"type": "kv", "key": "PEP Declaration", "value": "Not a Politically Exposed Person  - confirmed"},
            {"type": "kv", "key": "Politically Exposed Person", "value": "No"},
            {"type": "kv", "key": "Close Associate of PEP", "value": "No"},
            {"type": "kv", "key": "Subject to Sanctions", "value": "No"},
            {"type": "kv", "key": "Criminal Convictions", "value": "None declared"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section E  - Investment Profile"},
            {"type": "kv", "key": "Investment Experience", "value": "Moderate (5-10 years)"},
            {"type": "kv", "key": "Risk Tolerance", "value": "Moderate"},
            {"type": "kv", "key": "Investment Horizon", "value": "Long-term (10+ years)"},
            {"type": "kv", "key": "Products Requested", "value": "Cash Account, Retirement Account"},
            {"type": "spacer"},
            {"type": "h2", "text": "Declaration & Signature"},
            {"type": "text", "text": "I confirm that the information provided is true, accurate, and complete "
                                      "to the best of my knowledge. I understand that providing false information "
                                      "may result in account termination and may constitute a criminal offence."},
            {"type": "spacer"},
            {"type": "kv", "key": "Signature / Confirmation", "value": "Aarav Mehta (signed)"},
            {"type": "kv", "key": "Client Signature", "value": "Aarav Mehta (signed)"},
            {"type": "kv", "key": "Date Completed", "value": fmt(signed)},
            {"type": "kv", "key": "Advisor Signature", "value": "J. Collins, GlideGate Wealth Management"},
            {"type": "kv", "key": "Advisor Date", "value": fmt(signed)},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "COMPLETE  - All sections completed and signed"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_aml_declaration_signed() -> PDF:
    signed = TODAY - timedelta(days=5)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "ANTI-MONEY LAUNDERING DECLARATION"},
            {"type": "subtitle", "text": "GlideGate Wealth Management Ltd  - AML/CTF Compliance"},
            {"type": "spacer"},
            {"type": "h2", "text": "Declarant Information"},
            {"type": "kv", "key": "Client Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Full Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Tax Residency", "value": "United Kingdom"},
            {"type": "kv", "key": "TIN / Tax Identification Number (NI)", "value": "AB 12 34 56 C"},
            {"type": "kv", "key": "PEP Declaration", "value": "Not a Politically Exposed Person  - confirmed"},
            {"type": "kv", "key": "Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "kv", "key": "Passport Number", "value": "P1234567"},
            {"type": "spacer"},
            {"type": "h2", "text": "Source of Funds Declaration"},
            {"type": "text", "text": "I, Aarav Mehta, hereby declare that the funds and assets I intend to "
                                      "invest with GlideGate Wealth Management Ltd originate exclusively from "
                                      "the following legitimate sources:"},
            {"type": "spacer"},
            {"type": "bold", "text": "PRIMARY SOURCE: Employment income"},
            {"type": "text", "text": "Annual salary of GBP 95,000 from TechVision Ltd "
                                      "(Senior Software Engineer, employed since April 2014)."},
            {"type": "spacer"},
            {"type": "bold", "text": "SECONDARY SOURCE: Accumulated savings"},
            {"type": "text", "text": "Savings accumulated from employment income over 10+ years, "
                                      "held at Barclays Bank PLC (Account No: 12345678, Sort: 20-00-00)."},
            {"type": "spacer"},
            {"type": "h2", "text": "Representations and Warranties"},
            {"type": "text", "text": "I confirm that: (1) None of my funds derive from criminal activity, "
                                      "drug trafficking, terrorism financing, bribery, or corruption; "
                                      "(2) I am not a Politically Exposed Person nor an associate of any PEP; "
                                      "(3) I am not subject to any international sanctions; "
                                      "(4) All information is true and accurate to the best of my knowledge."},
            {"type": "spacer"},
            {"type": "h2", "text": "Undertaking"},
            {"type": "text", "text": "I undertake to immediately notify GlideGate Wealth Management Ltd of "
                                      "any material changes to my circumstances that may affect this declaration."},
            {"type": "spacer"},
            {"type": "h2", "text": "Signature"},
            {"type": "kv", "key": "Signature / Confirmation", "value": "Aarav Mehta (signed)"},
            {"type": "kv", "key": "Declarant Signature", "value": "Aarav Mehta (signed)"},
            {"type": "kv", "key": "Date Completed", "value": fmt(signed)},
            {"type": "kv", "key": "Date of Declaration", "value": fmt(signed)},
            {"type": "kv", "key": "Witnessed By", "value": "J. Collins, GlideGate Compliance Officer"},
            {"type": "kv", "key": "Witness Date", "value": fmt(signed)},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "COMPLETE  - Signed and witnessed"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_company_registration_valid() -> PDF:
    reg_date = TODAY - timedelta(days=365 * 3)
    last_stmt = TODAY - timedelta(days=45)
    last_accts = TODAY - timedelta(days=120)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "CERTIFICATE OF INCORPORATION"},
            {"type": "subtitle", "text": "Companies House  - England & Wales"},
            {"type": "spacer"},
            {"type": "h2", "text": "Company Details"},
            {"type": "kv", "key": "Company Name", "value": "TechVision Ltd"},
            {"type": "kv", "key": "Registration Number", "value": "12345678"},
            {"type": "kv", "key": "Company Number", "value": "12345678"},
            {"type": "kv", "key": "Company Type", "value": "Private Company Limited by Shares"},
            {"type": "kv", "key": "Registered in", "value": "England & Wales"},
            {"type": "kv", "key": "Registration Date", "value": fmt(reg_date)},
            {"type": "kv", "key": "Date of Incorporation", "value": fmt(reg_date)},
            {"type": "kv", "key": "Registered Office", "value": "100 Liverpool Street, London, EC2M 2AT"},
            {"type": "spacer"},
            {"type": "h2", "text": "Directors and Beneficial Owners"},
            {"type": "kv", "key": "Director 1", "value": f"Aarav Mehta  - Appointed {fmt(reg_date)}"},
            {"type": "kv", "key": "Director 2", "value": f"Sarah Collins  - Appointed {fmt(reg_date)}"},
            {"type": "kv", "key": "Beneficial Owner 1", "value": "Aarav Mehta  - 50% shareholding"},
            {"type": "kv", "key": "Beneficial Owner 2", "value": "Sarah Collins  - 50% shareholding"},
            {"type": "spacer"},
            {"type": "h2", "text": "Share Capital"},
            {"type": "kv", "key": "Authorised Capital", "value": "GBP 100,000 (100,000 ordinary shares at GBP 1.00)"},
            {"type": "kv", "key": "Issued Capital", "value": "GBP 10,000 (10,000 shares issued and fully paid)"},
            {"type": "spacer"},
            {"type": "h2", "text": "Official Certification"},
            {"type": "text", "text": "I hereby certify that TechVision Ltd was incorporated under the "
                                      "Companies Act 2006 as a private company limited by shares."},
            {"type": "spacer"},
            {"type": "kv", "key": "Signed", "value": "Registrar of Companies for England and Wales"},
            {"type": "kv", "key": "Date", "value": fmt(reg_date)},
            {"type": "kv", "key": "Authentication Code", "value": f"CH-REG-{reg_date.year}-0087234"},
            {"type": "spacer"},
            {"type": "h2", "text": "Current Filings Status"},
            {"type": "kv", "key": "Company Status", "value": "Active  - Live and in good standing"},
            {"type": "kv", "key": "Current Status", "value": "Active"},
            {"type": "kv", "key": "Last Confirmation Statement", "value": fmt(last_stmt)},
            {"type": "kv", "key": "Last Annual Accounts Filed", "value": fmt(last_accts)},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "VALID  - Active registered company, filings up to date"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


# ─── Negative documents ───────────────────────────────────────────────────────

def doc_passport_expired() -> PDF:
    issue = TODAY - timedelta(days=365 * 12)
    expiry = issue + timedelta(days=365 * 10)
    mrz_exp = expiry.strftime("%y%m%d")
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "UNITED KINGDOM PASSPORT"},
            {"type": "subtitle", "text": "Her Majesty's Passport Office  - ICAO 9303 Travel Document"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** DOCUMENT EXPIRED  - DO NOT ACCEPT FOR KYC ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Personal Information"},
            {"type": "kv", "key": "Surname", "value": "MEHTA"},
            {"type": "kv", "key": "Given Names", "value": "AARAV"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Nationality", "value": "British Citizen"},
            {"type": "spacer"},
            {"type": "h2", "text": "Document Details"},
            {"type": "kv", "key": "Passport Number", "value": "P9876543"},
            {"type": "kv", "key": "Date of Issue", "value": fmt(issue)},
            {"type": "kv", "key": "Date of Expiry", "value": fmt(expiry)},
            {"type": "kv", "key": "Issuing Authority", "value": "HM Passport Office, United Kingdom"},
            {"type": "spacer"},
            {"type": "h2", "text": "Machine Readable Zone (MRZ)"},
            {"type": "small", "text": "P<GBRMEHTA<<AARAV<<<<<<<<<<<<<<<<<<<<<<<<<<<"},
            {"type": "small", "text": f"P9876543<GBR8503152M{mrz_exp}<<<<<<9"},
            {"type": "spacer", "size": 20},
            {"type": "h2", "text": "Validation Failure Reason"},
            {"type": "bold", "text": "REJECTION: Passport expired on " + fmt(expiry)},
            {"type": "text", "text": f"This passport expired on {fmt(expiry)}  - over 2 years ago. "
                                      "UK KYC regulations require identity documents to be valid (not expired) "
                                      "at the time of the onboarding application. This document cannot be "
                                      "accepted. Client must present a current, valid passport."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Expired identity document"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_national_id_incomplete() -> PDF:
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "NATIONAL IDENTITY CARD"},
            {"type": "subtitle", "text": "UK National ID  - Home Office / UKVI"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** DOCUMENT INVALID  - CRITICAL FIELDS MISSING ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Personal Information"},
            {"type": "kv", "key": "Surname", "value": "MEHTA"},
            {"type": "kv", "key": "Given Names", "value": "AARAV"},
            {"type": "kv", "key": "Date of Birth", "value": "[FIELD MISSING  - NOT PROVIDED]"},
            {"type": "kv", "key": "Place of Birth", "value": "[REDACTED / ILLEGIBLE]"},
            {"type": "kv", "key": "Nationality", "value": "British"},
            {"type": "kv", "key": "Sex", "value": "[NOT STATED]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Document Details"},
            {"type": "kv", "key": "ID Card Number", "value": "[PARTIALLY OBSCURED: NID-????-5678]"},
            {"type": "kv", "key": "Date of Issue", "value": "[ILLEGIBLE  - DOCUMENT DAMAGED]"},
            {"type": "kv", "key": "Date of Expiry", "value": "[FIELD MISSING]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Holder Signature"},
            {"type": "text", "text": "[SIGNATURE FIELD BLANK  - Document holder has not signed]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Summary"},
            {"type": "bold", "text": "REJECTION: Multiple mandatory fields missing or illegible"},
            {"type": "text", "text": "1. Date of birth: missing  - cannot verify age/identity"},
            {"type": "text", "text": "2. Document number: partially obscured  - cannot uniquely identify document"},
            {"type": "text", "text": "3. Date of expiry: missing  - cannot confirm document is valid"},
            {"type": "text", "text": "4. Date of issue: illegible  - provenance cannot be established"},
            {"type": "text", "text": "5. Holder signature: absent  - document not authenticated by holder"},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - 5 mandatory fields missing or illegible"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_bank_statement_low_income() -> PDF:
    stmt_from = TODAY - timedelta(days=90)
    stmt_to = TODAY - timedelta(days=1)

    def d(offset_days: int) -> str:
        return (stmt_from + timedelta(days=offset_days)).strftime("%d %b %Y")

    return (
        PDF()
        .add_page([
            {"type": "title", "text": "HSBC UK  - Statement of Account"},
            {"type": "subtitle", "text": "Personal Current Account  - Advance Banking"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** INCOME INCONSISTENCY  - Declared vs. actual income mismatch ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Account Holder Information"},
            {"type": "kv", "key": "Account Name", "value": "A. Mehta"},
            {"type": "kv", "key": "Sort Code", "value": "40-02-50"},
            {"type": "kv", "key": "Account Number", "value": "87654321"},
            {"type": "kv", "key": "Statement Period", "value": f"{fmt(stmt_from)} to {fmt(stmt_to)}"},
            {"type": "spacer"},
            {"type": "h2", "text": "Transactions"},
            {"type": "ruler"},
            {"type": "kv", "key": "DATE", "value": "DESCRIPTION                               CREDIT      BALANCE"},
            {"type": "ruler"},
            {"type": "kv", "key": d(5),  "value": "SALARY - EMPLOYER                         1,250.00     1,250.00"},
            {"type": "kv", "key": d(35), "value": "SALARY - EMPLOYER                         1,250.00     2,500.00"},
            {"type": "kv", "key": d(65), "value": "SALARY - EMPLOYER                         1,250.00     3,750.00"},
            {"type": "ruler"},
            {"type": "kv", "key": "Total Monthly Credits", "value": "GBP 1,250.00"},
            {"type": "kv", "key": "Annualised Income (estimate)", "value": "GBP 15,000.00"},
            {"type": "spacer"},
            {"type": "h2", "text": "Compliance Alert  - Income Discrepancy"},
            {"type": "bold", "text": "REJECTION: Income does not match declared amount"},
            {"type": "text", "text": "Client declared annual income of GBP 95,000 during onboarding. "
                                      "This bank statement shows total monthly credits of GBP 1,250, "
                                      "equivalent to an estimated annual income of GBP 15,000  - "
                                      "a discrepancy of GBP 80,000 (84% below declared amount)."},
            {"type": "spacer"},
            {"type": "text", "text": "This document does not support the declared source of funds. "
                                      "Escalation to compliance review team is required. "
                                      "Additional documentation (e.g., payslips, tax returns, "
                                      "employer letter) must be obtained before onboarding can proceed."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Income GBP 15,000 vs. declared GBP 95,000 (84% discrepancy)"},
            {"type": "small", "text": "HSBC UK Limited. Authorised by the PRA and regulated by the FCA and PRA. " + _DEMO_NOTE},
        ])
    )


def doc_payslip_outdated() -> PDF:
    old_date = TODAY - timedelta(days=180)
    period = old_date.strftime("%B %Y")
    return (
        PDF()
        .add_page([
            {"type": "title", "text": f"PAYSLIP  - {period}"},
            {"type": "subtitle", "text": "TechVision Ltd  - HR & Payroll Services"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** OUT OF DATE  - Document issued more than 90 days ago ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Employee Details"},
            {"type": "kv", "key": "Employee Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Employee ID", "value": "EMP-00823"},
            {"type": "kv", "key": "Department", "value": "Software Engineering"},
            {"type": "kv", "key": "Pay Period", "value": period},
            {"type": "kv", "key": "Pay Date", "value": fmt(old_date)},
            {"type": "spacer"},
            {"type": "h2", "text": "Earnings"},
            {"type": "kv", "key": "Basic Salary", "value": "GBP 7,916.67 (Annual: GBP 95,000.00)"},
            {"type": "spacer"},
            {"type": "h2", "text": "Deductions"},
            {"type": "kv", "key": "Income Tax (PAYE)", "value": "GBP 2,166.67"},
            {"type": "kv", "key": "National Insurance", "value": "GBP 516.67"},
            {"type": "kv", "key": "Pension (5%)", "value": "GBP 395.83"},
            {"type": "ruler"},
            {"type": "kv", "key": "NET PAY", "value": "GBP 4,837.50"},
            {"type": "ruler"},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Reason"},
            {"type": "bold", "text": "REJECTION: Payslip is 180 days old (limit: 90 days)"},
            {"type": "text", "text": f"This payslip was issued on {fmt(old_date)}. KYC requirements for "
                                      "income verification mandate that payslips must be dated within 90 days "
                                      "of the onboarding application date. This document is 180 days old "
                                      "and falls outside the acceptable recency window. "
                                      "A payslip from the last 3 months must be provided."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Issued 180 days ago (maximum: 90 days)"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_contract_unsigned() -> PDF:
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "INVESTMENT MANAGEMENT AGREEMENT"},
            {"type": "subtitle", "text": "GlideGate Wealth Management Ltd  - DRAFT"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** DOCUMENT INCOMPLETE  - MISSING ALL REQUIRED SIGNATURES ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Parties"},
            {"type": "kv", "key": "Client", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Client Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "kv", "key": "Investment Manager", "value": "GlideGate Wealth Management Ltd"},
            {"type": "spacer"},
            {"type": "h2", "text": "Agreement Terms"},
            {"type": "text", "text": "1. MANDATE: The Manager shall manage the Client's portfolio in accordance "
                                      "with the agreed Investment Policy Statement (IPS)."},
            {"type": "spacer"},
            {"type": "text", "text": "2. FEES: Annual management fee of 0.75% of assets under management, "
                                      "charged quarterly in arrears."},
            {"type": "spacer"},
            {"type": "text", "text": "3. RISK: The Client acknowledges investment risk and confirms a moderate "
                                      "risk tolerance as disclosed in the KYC questionnaire."},
            {"type": "spacer"},
            {"type": "text", "text": "4. REPORTING: The Manager shall provide quarterly portfolio reports "
                                      "and an annual performance review."},
            {"type": "spacer"},
            {"type": "h2", "text": "Signatures"},
            {"type": "kv", "key": "Client Signature", "value": "[SIGNATURE MISSING  - NOT SIGNED]"},
            {"type": "kv", "key": "Client Date", "value": "[DATE MISSING]"},
            {"type": "kv", "key": "Manager Signature", "value": "[SIGNATURE MISSING  - NOT SIGNED]"},
            {"type": "kv", "key": "Manager Date", "value": "[DATE MISSING]"},
            {"type": "kv", "key": "Witness Signature", "value": "[WITNESS SIGNATURE MISSING]"},
            {"type": "kv", "key": "Witness Date", "value": "[DATE MISSING]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Reason"},
            {"type": "bold", "text": "REJECTION: Unsigned contract  - no executing party has signed"},
            {"type": "text", "text": "This agreement has not been executed by any party. All three "
                                      "signature fields (client, manager, witness) are blank and undated. "
                                      "A contract without signatures has no legal force and cannot be "
                                      "accepted as a valid legal document for KYC purposes."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Unsigned, undated draft document"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_insurance_policy_lapsed() -> PDF:
    start = TODAY - timedelta(days=400)
    end = start + timedelta(days=365)
    lapse_notice = end + timedelta(days=14)
    terminated = end + timedelta(days=30)
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "INSURANCE POLICY CERTIFICATE"},
            {"type": "subtitle", "text": "Aviva Insurance Ltd  - Income Protection Insurance"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** POLICY LAPSED  - COVERAGE TERMINATED ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Policy Details"},
            {"type": "kv", "key": "Policy Number", "value": "AVV-2023-INC-54321"},
            {"type": "kv", "key": "Policy Type", "value": "Income Protection Insurance  - Income Shield Plus"},
            {"type": "spacer"},
            {"type": "h2", "text": "Insured Person"},
            {"type": "kv", "key": "Policyholder Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "spacer"},
            {"type": "h2", "text": "Coverage Information"},
            {"type": "kv", "key": "Cover Amount", "value": "GBP 47,500 per annum"},
            {"type": "kv", "key": "Coverage Start Date", "value": fmt(start)},
            {"type": "kv", "key": "Coverage End Date", "value": fmt(end)},
            {"type": "kv", "key": "Annual Premium", "value": "GBP 1,140.00"},
            {"type": "spacer"},
            {"type": "h2", "text": "Lapse Timeline"},
            {"type": "kv", "key": "Renewal Premium Due", "value": fmt(end) + "  - GBP 1,140.00"},
            {"type": "kv", "key": "Payment Received", "value": "NONE"},
            {"type": "kv", "key": "Lapse Notice Issued", "value": fmt(lapse_notice)},
            {"type": "kv", "key": "Grace Period Expired", "value": fmt(terminated)},
            {"type": "kv", "key": "Coverage Terminated", "value": fmt(terminated)},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Reason"},
            {"type": "bold", "text": "REJECTION: Policy lapsed  - no active coverage"},
            {"type": "text", "text": f"This policy lapsed on {fmt(end)} due to non-payment of the "
                                      f"annual renewal premium of GBP 1,140.00. Despite a 30-day grace "
                                      f"period and formal lapse notice on {fmt(lapse_notice)}, no payment "
                                      f"was received. Coverage was formally terminated on {fmt(terminated)}. "
                                      f"There is no active insurance cover under this policy."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Policy lapsed, no active coverage"},
            {"type": "small", "text": "Aviva Insurance Ltd. Authorised by the PRA and regulated by the FCA and PRA. " + _DEMO_NOTE},
        ])
    )


def doc_kyc_form_incomplete() -> PDF:
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "KNOW YOUR CUSTOMER (KYC) FORM"},
            {"type": "subtitle", "text": "GlideGate Wealth Management Ltd  - Client Identification Form (CIF)"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** FORM INCOMPLETE  - 5 MANDATORY FIELDS MISSING, UNSIGNED ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section A  - Personal Information"},
            {"type": "kv", "key": "Full Legal Name", "value": "Aarav Mehta"},
            {"type": "kv", "key": "Date of Birth", "value": "15 March 1985"},
            {"type": "kv", "key": "Nationality", "value": "British"},
            {"type": "kv", "key": "Passport Number", "value": "P1234567"},
            {"type": "kv", "key": "Residential Address", "value": "12 Baker Street, London, W1U 6TN"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section B  - Employment & Financial Information"},
            {"type": "kv", "key": "Occupation", "value": "Software Engineer"},
            {"type": "kv", "key": "Employer", "value": "TechVision Ltd"},
            {"type": "kv", "key": "Annual Income", "value": "GBP 95,000"},
            {"type": "kv", "key": "Source of Funds", "value": "[FIELD LEFT BLANK  - MANDATORY]"},
            {"type": "kv", "key": "Source of Wealth", "value": "[FIELD LEFT BLANK  - MANDATORY]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section C  - Tax Information"},
            {"type": "kv", "key": "Tax Residency", "value": "[NOT PROVIDED  - MANDATORY]"},
            {"type": "kv", "key": "NI Number", "value": "AB 12 34 56 C"},
            {"type": "kv", "key": "US Person (FATCA)", "value": "[UNANSWERED  - MANDATORY]"},
            {"type": "kv", "key": "CRS Reportable Jurisdictions", "value": "[NOT PROVIDED  - MANDATORY]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Section D  - PEP / AML Screening"},
            {"type": "kv", "key": "Politically Exposed Person", "value": "[UNANSWERED  - MANDATORY]"},
            {"type": "kv", "key": "Associate of PEP", "value": "[UNANSWERED  - MANDATORY]"},
            {"type": "kv", "key": "Subject to Sanctions", "value": "[UNANSWERED  - MANDATORY]"},
            {"type": "kv", "key": "Criminal Convictions", "value": "[UNANSWERED  - MANDATORY]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Signature Block"},
            {"type": "kv", "key": "Client Signature", "value": "[UNSIGNED]"},
            {"type": "kv", "key": "Date", "value": "[NOT DATED]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Summary"},
            {"type": "bold", "text": "REJECTION: Incomplete KYC form  - mandatory fields missing"},
            {"type": "text", "text": "Mandatory fields not completed: (1) Source of Funds  - required for AML; "
                                      "(2) Source of Wealth  - required for AML; "
                                      "(3) Tax Residency  - required for CRS/FATCA; "
                                      "(4) US Person status  - required for FATCA reporting; "
                                      "(5) PEP and sanctions screening questions  - required by MLRO. "
                                      "Additionally, the form is unsigned and undated. "
                                      "This form cannot be accepted until all mandatory sections are completed."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - 5 mandatory fields missing, unsigned"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


def doc_articles_missing_signatures() -> PDF:
    return (
        PDF()
        .add_page([
            {"type": "title", "text": "ARTICLES OF ASSOCIATION"},
            {"type": "subtitle", "text": "TechVision Ltd  - Company Constitution (Companies Act 2006, s.18)"},
            {"type": "spacer"},
            {"type": "bold", "text": "*** DOCUMENT INVALID  - ALL SUBSCRIBER SIGNATURES MISSING ***"},
            {"type": "spacer"},
            {"type": "h2", "text": "Company Details"},
            {"type": "kv", "key": "Company Name", "value": "TechVision Ltd"},
            {"type": "kv", "key": "Company Number", "value": "12345678"},
            {"type": "kv", "key": "Registered Office", "value": "100 Liverpool Street, London, EC2M 2AT"},
            {"type": "spacer"},
            {"type": "h2", "text": "Memorandum of Association"},
            {"type": "text", "text": "We, the subscribers to this memorandum of association, wish to form a "
                                      "company under the Companies Act 2006. We agree to become members of "
                                      "the company and to take at least one share each."},
            {"type": "spacer"},
            {"type": "h2", "text": "Articles of Association  - Key Provisions"},
            {"type": "text", "text": "1. LIABILITY: The liability of each member is limited to the amount, "
                                      "if any, unpaid on the shares held by that member."},
            {"type": "spacer"},
            {"type": "text", "text": "2. DIRECTORS: The directors may exercise all the powers of the company "
                                      "except any that are required to be exercised in a general meeting."},
            {"type": "spacer"},
            {"type": "text", "text": "3. SHARES: The company may issue shares of such nominal value and such "
                                      "rights and restrictions as the directors determine."},
            {"type": "spacer"},
            {"type": "h2", "text": "Subscriber Authentication"},
            {"type": "kv", "key": "Subscriber 1 (Aarav Mehta)", "value": "[SIGNATURE MISSING  - MANDATORY]"},
            {"type": "kv", "key": "Date signed", "value": "[NOT DATED]"},
            {"type": "kv", "key": "Subscriber 2 (Sarah Collins)", "value": "[SIGNATURE MISSING  - MANDATORY]"},
            {"type": "kv", "key": "Date signed", "value": "[NOT DATED]"},
            {"type": "kv", "key": "Independent Witness", "value": "[WITNESS SIGNATURE MISSING  - MANDATORY]"},
            {"type": "kv", "key": "Witness date", "value": "[NOT DATED]"},
            {"type": "spacer"},
            {"type": "h2", "text": "Validation Failure Reason"},
            {"type": "bold", "text": "REJECTION: Unsigned articles  - no legal standing"},
            {"type": "text", "text": "All subscriber signatures are missing and the document is undated. "
                                      "Articles of Association require signatures from all subscribers "
                                      "and an independent witness to have legal effect under the Companies "
                                      "Act 2006. This document cannot be accepted for entity KYC purposes. "
                                      "Additionally, the articles may not reflect the current company "
                                      "constitution if any amendments were adopted post-incorporation."},
            {"type": "spacer"},
            {"type": "ruler"},
            {"type": "kv", "key": "Validation Status", "value": "REJECTED  - Unsigned, undated, missing witness"},
            {"type": "small", "text": _DEMO_NOTE},
        ])
    )


# ─── Runner ───────────────────────────────────────────────────────────────────

DOCS_ROOT = Path(__file__).parent.parent / "docs" / "demo" / "documents"


def save(path: Path, pdf: PDF) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf.to_bytes())
    size_kb = path.stat().st_size / 1024
    rel = path.relative_to(DOCS_ROOT)
    print(f"  {rel}  ({size_kb:.1f} KB)")


def main() -> None:
    print("Generating GlideGate KYC demo documents...\n")

    pos = DOCS_ROOT / "positive"
    neg = DOCS_ROOT / "negative"

    print("POSITIVE  - valid documents (Scenario A  - happy path):")
    save(pos / "identity"   / "GG_DEMO_PASSPORT_VALID.pdf",            doc_passport_valid())
    save(pos / "identity"   / "GG_DEMO_DRIVING_LICENCE_VALID.pdf",     doc_driving_licence_valid())
    save(pos / "financial"  / "GG_DEMO_BANK_STATEMENT_VALID.pdf",      doc_bank_statement_valid())
    save(pos / "financial"  / "GG_DEMO_PAYSLIP_VALID.pdf",             doc_payslip_valid())
    save(pos / "legal"      / "GG_DEMO_POWER_OF_ATTORNEY_VALID.pdf",   doc_power_of_attorney_valid())
    save(pos / "insurance"  / "GG_DEMO_INSURANCE_POLICY_VALID.pdf",    doc_insurance_policy_valid())
    save(pos / "compliance" / "GG_DEMO_KYC_FORM_COMPLETE.pdf",         doc_kyc_form_complete())
    save(pos / "compliance" / "GG_DEMO_AML_DECLARATION_SIGNED.pdf",    doc_aml_declaration_signed())
    save(pos / "entity"     / "GG_DEMO_COMPANY_REGISTRATION_VALID.pdf",doc_company_registration_valid())

    print()
    print("NEGATIVE  - invalid documents (Scenario B  - escalation/rejection):")
    save(neg / "identity"   / "GG_DEMO_PASSPORT_EXPIRED.pdf",           doc_passport_expired())
    save(neg / "identity"   / "GG_DEMO_NATIONAL_ID_INCOMPLETE.pdf",     doc_national_id_incomplete())
    save(neg / "financial"  / "GG_DEMO_BANK_STATEMENT_LOW_INCOME.pdf",  doc_bank_statement_low_income())
    save(neg / "financial"  / "GG_DEMO_PAYSLIP_OUTDATED.pdf",           doc_payslip_outdated())
    save(neg / "legal"      / "GG_DEMO_CONTRACT_UNSIGNED.pdf",          doc_contract_unsigned())
    save(neg / "insurance"  / "GG_DEMO_INSURANCE_POLICY_LAPSED.pdf",    doc_insurance_policy_lapsed())
    save(neg / "compliance" / "GG_DEMO_KYC_FORM_INCOMPLETE.pdf",        doc_kyc_form_incomplete())
    save(neg / "entity"     / "GG_DEMO_ARTICLES_MISSING_SIGNATURES.pdf",doc_articles_missing_signatures())

    total = sum(1 for _ in DOCS_ROOT.rglob("*.pdf"))
    print(f"\nDone. {total} documents generated in {DOCS_ROOT}")


if __name__ == "__main__":
    main()
