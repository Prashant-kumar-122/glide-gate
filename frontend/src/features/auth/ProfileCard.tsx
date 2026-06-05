import { useState } from 'react'
import { User, Mail, Shield } from 'lucide-react'
import { useProfile, useUpdateProfile } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'
import ConfirmationModal from '@/components/ConfirmationModal'

export default function ProfileCard() {
  const { user } = useAuthStore()
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()

  const [editing, setEditing] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)
  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    confirm_password: '',
  })

  function startEdit() {
    setForm({
      email: profile?.email ?? '',
      first_name: profile?.first_name ?? '',
      last_name: profile?.last_name ?? '',
      password: '',
      confirm_password: '',
    })
    setEditing(true)
  }

  function handleSave() {
    if (form.password) {
      setShowPasswordConfirm(true)
    } else {
      submitUpdate()
    }
  }

  function submitUpdate() {
    const payload: Record<string, string> = {
      email: form.email,
      first_name: form.first_name,
      last_name: form.last_name,
    }
    if (form.password) {
      payload.password = form.password
      payload.confirm_password = form.confirm_password
    }
    updateProfile.mutate(payload, {
      onSuccess: () => {
        setEditing(false)
        setShowPasswordConfirm(false)
      },
    })
  }

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4 border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-800">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 rounded bg-gray-100 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  const isClient = user?.role === 'client'
  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : user?.firstName + ' ' + user?.lastName

  return (
    <>
      <div className="border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-800">
        <div className="flex items-center gap-4 border-b border-gray-100 p-6 dark:border-gray-700">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
            <User className="h-7 w-7 text-blue-600 dark:text-blue-300" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{displayName}</h2>
            <span className="inline-block bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {user?.role}
            </span>
          </div>
          {isClient && !editing && (
            <button
              onClick={startEdit}
              className="ml-auto border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Edit profile
            </button>
          )}
        </div>

        <div className="space-y-4 p-6">
          {updateProfile.error && (
            <div className="bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
              {(updateProfile.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Update failed.'}
            </div>
          )}

          {editing ? (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">First name</label>
                  <input
                    type="text"
                    value={form.first_name}
                    onChange={set('first_name')}
                    className="border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Last name</label>
                  <input
                    type="text"
                    value={form.last_name}
                    onChange={set('last_name')}
                    className="border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={set('email')}
                  className="border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
                />
              </div>

              <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
                <p className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">Change password (optional)</p>
                <div className="flex flex-col gap-3">
                  <input
                    type="password"
                    placeholder="New password"
                    value={form.password}
                    onChange={set('password')}
                    className="border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder-gray-500"
                  />
                  <input
                    type="password"
                    placeholder="Confirm new password"
                    value={form.confirm_password}
                    onChange={set('confirm_password')}
                    className="border border-gray-200 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder-gray-500"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleSave}
                  disabled={updateProfile.isPending}
                  className="bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50"
                >
                  {updateProfile.isPending ? 'Saving…' : 'Save changes'}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <>
              <InfoRow icon={<Mail className="h-4 w-4" />} label="Email" value={profile?.email ?? user?.email ?? '—'} />
              <InfoRow icon={<User className="h-4 w-4" />} label="Name" value={displayName} />
              <InfoRow icon={<Shield className="h-4 w-4" />} label="Role" value={user?.role ?? '—'} capitalize />
            </>
          )}
        </div>
      </div>

      <ConfirmationModal
        isOpen={showPasswordConfirm}
        title="Change password?"
        message="You are about to update your password. You will remain signed in with the new credentials."
        confirmLabel="Save changes"
        variant="warning"
        onConfirm={submitUpdate}
        onCancel={() => setShowPasswordConfirm(false)}
        loading={updateProfile.isPending}
      />
    </>
  )
}

function InfoRow({
  icon,
  label,
  value,
  capitalize,
}: {
  icon: React.ReactNode
  label: string
  value: string
  capitalize?: boolean
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400">{icon}</span>
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className={['text-sm font-medium text-gray-900 dark:text-gray-100', capitalize ? 'capitalize' : ''].join(' ')}>
          {value}
        </p>
      </div>
    </div>
  )
}
