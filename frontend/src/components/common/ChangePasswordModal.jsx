import { useState } from 'react'
import { changePassword } from '../../api/auth'

export default function ChangePasswordModal({ onClose }) {
  const [form, setForm] = useState({ old: '', new: '', confirm: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.new !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    if (form.new.length < 4) {
      setError('Password must be at least 4 characters.')
      return
    }
    setLoading(true)
    try {
      await changePassword(form.old, form.new)
      setSuccess(true)
      setTimeout(onClose, 1500)
    } catch (err) {
      setError(err.message || 'Password change failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Change Password</h2>

        {success ? (
          <div className="text-green-600 text-sm bg-green-50 rounded-lg px-4 py-3">
            Password changed successfully.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <input
              type="password"
              name="old"
              placeholder="Current password"
              value={form.old}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
            <input
              type="password"
              name="new"
              placeholder="New password"
              value={form.new}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
            <input
              type="password"
              name="confirm"
              placeholder="Confirm new password"
              value={form.confirm}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
            {error && <div className="text-sm text-red-600">{error}</div>}
            <div className="flex gap-2 pt-2">
              <button type="button" onClick={onClose} className="flex-1 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                {loading ? '...' : 'Change'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
