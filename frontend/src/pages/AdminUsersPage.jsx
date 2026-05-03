/**
 * /admin/users — 사용자 관리 페이지 (admin only).
 *
 * Phase 4 단계 4. 검색/페이지네이션 + 역할 변경 + 비밀번호 리셋 + 삭제.
 */
import { useEffect, useState, useCallback } from 'react'
import { fetchUsers, patchUser, deleteUser } from '../api/admin'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

export default function AdminUsersPage() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 20
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchUsers({ q, limit, offset })
      setItems(result.items || [])
      setTotal(result.total || 0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, offset])

  useEffect(() => { load() }, [load])

  const handleRoleToggle = async (user) => {
    const next = user.role === 'admin' ? 'user' : 'admin'
    if (!confirm(`${user.name} 역할을 ${next}로 변경하시겠습니까?`)) return
    try {
      await patchUser(user.id, { role: next })
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleResetPassword = async (user) => {
    const pw = prompt(`${user.name}의 새 비밀번호 (최소 8자):`)
    if (!pw || pw.length < 8) return
    try {
      await patchUser(user.id, { new_password: pw })
      alert('비밀번호가 변경되었습니다.')
    } catch (e) {
      setError(e.message)
    }
  }

  const handleDelete = async (user) => {
    if (!confirm(`${user.name} (#${user.id}) 사용자를 삭제하시겠습니까?`)) return
    try {
      await deleteUser(user.id)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">사용자 관리</h1>

      <div className="flex items-center gap-3">
        <input
          type="text"
          value={q}
          onChange={(e) => { setQ(e.target.value); setOffset(0) }}
          placeholder="username/name 검색"
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-72"
        />
        <span className="text-sm text-gray-500">총 {total}명</span>
      </div>

      {error && <ErrorAlert message={error} />}
      {loading ? <LoadingSpinner /> : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-2.5 text-left">ID</th>
                <th className="px-4 py-2.5 text-left">Username</th>
                <th className="px-4 py-2.5 text-left">이름</th>
                <th className="px-4 py-2.5 text-left">역할</th>
                <th className="px-4 py-2.5 text-center">KIS</th>
                <th className="px-4 py-2.5 text-left">가입일</th>
                <th className="px-4 py-2.5 text-center">작업</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">결과 없음</td></tr>
              ) : items.map(u => (
                <tr key={u.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-xs">{u.id}</td>
                  <td className="px-4 py-2.5">@{u.username}</td>
                  <td className="px-4 py-2.5">{u.name}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded ${u.role === 'admin' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {u.has_kis ? <span className="text-green-600 text-xs">✓ 활성</span> : <span className="text-gray-400 text-xs">미등록</span>}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-500">{u.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-2.5 text-center space-x-2 text-xs">
                    <button onClick={() => handleRoleToggle(u)} className="text-blue-600 hover:text-blue-800">역할변경</button>
                    <button onClick={() => handleResetPassword(u)} className="text-yellow-600 hover:text-yellow-800">PW리셋</button>
                    <button onClick={() => handleDelete(u)} className="text-red-600 hover:text-red-800">삭제</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > limit && (
        <div className="flex justify-center gap-2">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >이전</button>
          <span className="px-3 py-1 text-sm text-gray-500">{offset + 1} - {Math.min(offset + limit, total)} / {total}</span>
          <button
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >다음</button>
        </div>
      )}
    </div>
  )
}
