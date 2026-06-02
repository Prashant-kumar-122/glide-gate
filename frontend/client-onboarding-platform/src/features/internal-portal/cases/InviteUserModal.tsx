import { useState } from 'react';
import { Modal, TextInput, Button, Divider } from '@mantine/core';
import { IconCheck, IconSend, IconUserPlus } from '@tabler/icons-react';
import { initials } from '../../../utils/formatters';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Contact {
  name: string;
  type: string;
}

interface InviteUserModalProps {
  opened:           boolean;
  onClose:          () => void;
  existingContacts: Contact[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function InviteUserModal({ opened, onClose, existingContacts }: InviteUserModalProps) {
  const [firstName,   setFirstName]   = useState('');
  const [lastName,    setLastName]    = useState('');
  const [email,       setEmail]       = useState('');
  const [sending,     setSending]     = useState<string | null>(null);
  const [sentInvites, setSentInvites] = useState<Set<string>>(new Set());

  const handleClose = () => {
    setFirstName('');
    setLastName('');
    setEmail('');
    setSending(null);
    setSentInvites(new Set());
    onClose();
  };

  const markSent = (key: string) => {
    setSentInvites(prev => new Set(prev).add(key));
    setSending(null);
  };

  const sendExisting = async (contact: Contact) => {
    const key = `existing:${contact.name}`;
    if (sentInvites.has(key) || sending) return;
    setSending(key);
    await new Promise(r => setTimeout(r, 700));
    markSent(key);
  };

  const sendNew = async () => {
    const key = `new:${email.toLowerCase()}`;
    if (sentInvites.has(key) || sending) return;
    setSending(key);
    await new Promise(r => setTimeout(r, 700));
    markSent(key);
  };

  const newContactKey = `new:${email.toLowerCase()}`;
  const newContactReady = firstName.trim() && lastName.trim() && email.includes('@');

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <div className="flex items-center gap-2">
          <IconUserPlus size={16} />
          <span>Invite User</span>
        </div>
      }
      centered
      size="md"
    >
      <div className="space-y-5">

        {/* ── Existing contacts ────────────────────────────────────────────── */}
        {existingContacts.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3">
              Case Contacts
            </p>
            <div className="space-y-2">
              {existingContacts.map(contact => {
                const key    = `existing:${contact.name}`;
                const isSent = sentInvites.has(key);
                return (
                  <div
                    key={contact.name}
                    className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-bg-elevated border border-border-default"
                  >
                    {/* Avatar + name */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-primary-subtle border border-primary/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-primary">{initials(contact.name)}</span>
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">{contact.name}</p>
                        <p className="text-xs text-text-muted">{contact.type}</p>
                      </div>
                    </div>

                    {/* Action */}
                    {isSent ? (
                      <span className="flex items-center gap-1 text-xs text-success font-medium flex-shrink-0">
                        <IconCheck size={12} strokeWidth={2.5} /> Invited
                      </span>
                    ) : (
                      <button
                        onClick={() => sendExisting(contact)}
                        disabled={!!sending}
                        className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-primary text-primary text-xs font-semibold hover:bg-primary hover:text-white disabled:opacity-40 transition-colors flex-shrink-0"
                      >
                        <IconSend size={11} />
                        {sending === key ? 'Sending…' : 'Send Invite'}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <Divider label="Add New Contact" labelPosition="center" />

        {/* ── New contact form ─────────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <TextInput
              label="First Name"
              placeholder="Jane"
              value={firstName}
              onChange={e => setFirstName(e.currentTarget.value)}
              size="sm"
            />
            <TextInput
              label="Last Name"
              placeholder="Smith"
              value={lastName}
              onChange={e => setLastName(e.currentTarget.value)}
              size="sm"
            />
          </div>
          <TextInput
            label="Email"
            placeholder="jane.smith@example.com"
            type="email"
            value={email}
            onChange={e => setEmail(e.currentTarget.value)}
            size="sm"
          />

          <div className="flex justify-end pt-1">
            {sentInvites.has(newContactKey) ? (
              <span className="flex items-center gap-1.5 text-sm text-success font-medium">
                <IconCheck size={14} strokeWidth={2.5} /> Invite sent to {email}
              </span>
            ) : (
              <Button
                size="sm"
                leftSection={<IconSend size={13} />}
                disabled={!newContactReady || !!sending}
                loading={sending === newContactKey}
                onClick={sendNew}
              >
                Send Invite
              </Button>
            )}
          </div>
        </div>

      </div>
    </Modal>
  );
}
