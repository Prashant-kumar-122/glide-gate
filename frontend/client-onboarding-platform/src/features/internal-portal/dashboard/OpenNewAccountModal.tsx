import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, TextInput, MultiSelect, Button, Divider } from '@mantine/core';
import { IconPlus, IconLoader2, IconX, IconUser } from '@tabler/icons-react';
import { casesService } from '../../../mocks/services/cases.service';
import { PRODUCT_LABELS } from '../../../types';
import type { ProductType } from '../../../types';

// ─── Product options ──────────────────────────────────────────────────────────

const PRODUCT_OPTIONS: { value: ProductType; label: string }[] = [
  { value: 'PB',         label: PRODUCT_LABELS['PB'] },
  { value: 'DvP',        label: PRODUCT_LABELS['DvP'] },
  { value: 'IB_CASH',    label: PRODUCT_LABELS['IB_CASH'] },
  { value: 'FCM',        label: PRODUCT_LABELS['FCM'] },
  { value: 'RETIREMENT', label: PRODUCT_LABELS['RETIREMENT'] },
  { value: 'RETAIL',     label: PRODUCT_LABELS['RETAIL'] },
];

// ─── Types ────────────────────────────────────────────────────────────────────

interface Contact {
  id:        string;
  firstName: string;
  lastName:  string;
  email:     string;
}

interface OpenNewAccountModalProps {
  opened: boolean;
  onClose: () => void;
}

const emptyContact = (): Contact => ({
  id:        `c-${Date.now()}-${Math.random()}`,
  firstName: '',
  lastName:  '',
  email:     '',
});

// ─── Component ────────────────────────────────────────────────────────────────

export function OpenNewAccountModal({ opened, onClose }: OpenNewAccountModalProps) {
  const navigate    = useNavigate();
  const queryClient = useQueryClient();

  const [clientName, setClientName] = useState('');
  const [products,   setProducts]   = useState<string[]>([]);
  const [contacts,   setContacts]   = useState<Contact[]>([]);

  const handleClose = () => {
    setClientName('');
    setProducts([]);
    setContacts([]);
    onClose();
  };

  // ── Contact helpers ───────────────────────────────────────────────────────

  const addContact = () => setContacts(prev => [...prev, emptyContact()]);

  const removeContact = (id: string) =>
    setContacts(prev => prev.filter(c => c.id !== id));

  const updateContact = (id: string, field: keyof Omit<Contact, 'id'>, value: string) =>
    setContacts(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c));

  // ── Mutation ──────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: () =>
      casesService.submitCase({
        clientId:   `client-${Date.now()}`,
        clientName: clientName.trim(),
        products:   products as ProductType[],
      }),
    onSuccess: created => {
      queryClient.invalidateQueries({ queryKey: ['cases', 'all'] });
      handleClose();
      navigate(`/internal/cases/${created.id}`);
    },
  });

  const canSubmit = clientName.trim() && products.length > 0 && !createMutation.isPending;

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Open New Account"
      centered
      size="lg"
    >
      <div className="space-y-4">

        {/* Client name */}
        <TextInput
          label="Client Name"
          placeholder="e.g. Acme Capital Ltd."
          value={clientName}
          onChange={e => setClientName(e.currentTarget.value)}
          required
        />

        {/* Products */}
        <MultiSelect
          label="Products"
          placeholder="Select one or more products"
          data={PRODUCT_OPTIONS}
          value={products}
          onChange={setProducts}
          required
        />

        {/* ── Contacts ─────────────────────────────────────────────────────── */}
        <Divider />

        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-text-primary">Contacts</p>
              <p className="text-xs text-text-muted mt-0.5">Add authorised users or key contacts for this account.</p>
            </div>
            {contacts.length === 0 && (
              <button
                type="button"
                onClick={addContact}
                className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-border-default text-xs font-medium text-text-secondary hover:text-primary hover:border-primary transition-colors"
              >
                <IconUser size={12} /> Add Contact
              </button>
            )}
          </div>

          {contacts.length > 0 && (
            <div className="space-y-2">
              {/* Column headers */}
              <div className="grid gap-2 px-0.5" style={{ gridTemplateColumns: '1fr 1fr 2fr 28px' }}>
                <span className="text-xs text-text-muted">First Name</span>
                <span className="text-xs text-text-muted">Last Name</span>
                <span className="text-xs text-text-muted">Email</span>
                <span />
              </div>

              {/* Contact rows */}
              {contacts.map(contact => (
                <div
                  key={contact.id}
                  className="grid gap-2 items-center"
                  style={{ gridTemplateColumns: '1fr 1fr 2fr 28px' }}
                >
                  <TextInput
                    size="xs"
                    placeholder="Jane"
                    value={contact.firstName}
                    onChange={e => updateContact(contact.id, 'firstName', e.currentTarget.value)}
                  />
                  <TextInput
                    size="xs"
                    placeholder="Smith"
                    value={contact.lastName}
                    onChange={e => updateContact(contact.id, 'lastName', e.currentTarget.value)}
                  />
                  <TextInput
                    size="xs"
                    type="email"
                    placeholder="jane@example.com"
                    value={contact.email}
                    onChange={e => updateContact(contact.id, 'email', e.currentTarget.value)}
                  />
                  <button
                    type="button"
                    onClick={() => removeContact(contact.id)}
                    className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                  >
                    <IconX size={13} />
                  </button>
                </div>
              ))}

              {/* Add another row */}
              <button
                type="button"
                onClick={addContact}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary-hover transition-colors pt-1"
              >
                <IconPlus size={12} /> Add another contact
              </button>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-1">
          <Button variant="default" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            leftSection={
              createMutation.isPending
                ? <IconLoader2 size={14} className="animate-spin" />
                : <IconPlus size={14} />
            }
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? 'Creating…' : 'Create Case'}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
