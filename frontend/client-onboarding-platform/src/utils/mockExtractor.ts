// Simulates intelligent document data extraction

const EXTRACTED_PAYLOADS: Record<string, Record<string, string>> = {
  articles: {
    legalName: 'Acme Capital LLC',
    taxId: '47-1234567',
    incorporationState: 'Delaware',
    incorporationDate: '2015-06-10',
    businessType: 'Limited Liability Company',
    'address.line1': '200 Park Avenue',
    'address.city': 'New York',
    'address.state': 'NY',
    'address.zip': '10166',
    'address.country': 'United States',
  },
  passport: {
    'primaryContact.fullName': 'Jordan Lee',
    'primaryContact.email': 'jordan.lee@acme.com',
    nationality: 'US',
    dateOfBirth: '1985-04-22',
    documentNumber: 'X12345678',
  },
};

export async function extractDataFromFile(file: File): Promise<Record<string, string>> {
  await new Promise(r => setTimeout(r, 1500));
  const name = file.name.toLowerCase();
  if (name.includes('article') || name.includes('incorporation') || name.includes('corp')) {
    return EXTRACTED_PAYLOADS.articles;
  }
  if (name.includes('passport') || name.includes('id')) {
    return EXTRACTED_PAYLOADS.passport;
  }
  return {};
}
