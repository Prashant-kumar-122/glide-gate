import ProfileCard from '@/features/auth/ProfileCard'

export default function Profile() {
  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">My Profile</h1>
      <ProfileCard />
    </div>
  )
}
