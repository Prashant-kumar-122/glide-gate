import { useRef, useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { User, ChevronDown, LogOut } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'

export default function UserMenu() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  if (!user) return null

  function handleSignOut() {
    qc.clear()
    clearAuth()
    navigate('/login')
  }

  const fullName = `${user.firstName} ${user.lastName}`

  return (
    <div ref={ref} className="relative ml-auto">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
      >
        <User className="h-4 w-4" />
        <span className="max-w-[140px] truncate">{fullName}</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-lg border border-gray-100 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">
          <div className="border-b border-gray-100 px-3 py-2 dark:border-gray-700">
            <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{fullName}</p>
            <p className="truncate text-xs capitalize text-gray-400">{user.role}</p>
          </div>

          <Link
            to="/profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            <User className="h-4 w-4 text-gray-400" />
            View Profile
          </Link>

          <button
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  )
}
