/**
 * /settings/kis — 사용자 본인 KIS 자격증명 등록/조회/삭제/재검증.
 *
 * Phase 4 D.4. 모든 폼 입력은 등록 시 즉시 KIS /oauth2/tokenP 호출로 검증됨.
 * 검증 성공 후 AES-GCM 암호화 저장.
 */
import { useEffect, useState } from 'react'
import { getMyKis, saveMyKis, deleteMyKis, validateMyKis } from '../api/me'
import { useAuth } from '../hooks/useAuth'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

const initialForm = {
  app_key: '',
  app_secret: '',
  acnt_no: '',
  acnt_prdt_cd_stk: '01',
  acnt_prdt_cd_fno: '',
  hts_id: '',
  base_url: 'https://openapi.koreainvestment.com:9443',
}

export default function SettingsKisPage() {
  const { refreshUser } = useAuth()
  const [status, setStatus] = useState(null) // {registered, app_key_masked, validated_at, is_active}
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getMyKis()
      setStatus(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const payload = { ...form }
      if (!payload.acnt_prdt_cd_fno) delete payload.acnt_prdt_cd_fno
      if (!payload.hts_id) delete payload.hts_id
      if (!payload.base_url) delete payload.base_url
      await saveMyKis(payload)
      setSuccess('KIS 자격증명이 검증되어 저장되었습니다.')
      setForm(initialForm)
      await load()
      await refreshUser()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleValidate = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await validateMyKis()
      setSuccess('재검증 성공')
      await load()
      await refreshUser()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('KIS 자격증명을 삭제하시겠습니까?')) return
    setSaving(true)
    setError(null)
    try {
      await deleteMyKis()
      setSuccess('삭제되었습니다.')
      await load()
      await refreshUser()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="max-w-3xl mx-auto py-6">
      <h1 className="text-2xl font-semibold mb-2">KIS 자격증명 설정</h1>
      <p className="text-sm text-gray-600 mb-6">
        한국투자증권 OpenAPI 키. 잔고/매매/양도세/포트폴리오 자문에서 사용됩니다.
        키는 AES-GCM으로 암호화되어 저장되며, 응답에는 끝 4자리만 노출됩니다.
      </p>

      {error && <ErrorAlert message={error} className="mb-4" />}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
          {success}
        </div>
      )}

      {status?.registered && (
        <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded">
          <h3 className="font-medium mb-2">현재 등록 상태</h3>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-gray-500">앱 키</dt>
            <dd className="font-mono">{status.app_key_masked}</dd>
            <dt className="text-gray-500">계좌상품코드(주식)</dt>
            <dd className="font-mono">{status.acnt_prdt_cd_stk}</dd>
            {status.acnt_prdt_cd_fno && (
              <>
                <dt className="text-gray-500">계좌상품코드(FNO)</dt>
                <dd className="font-mono">{status.acnt_prdt_cd_fno}</dd>
              </>
            )}
            <dt className="text-gray-500">검증 시각</dt>
            <dd className="font-mono">{status.validated_at || '-'}</dd>
            <dt className="text-gray-500">검증 활성</dt>
            <dd>
              {status.is_active
                ? <span className="text-green-700">✓ 활성 (24h 이내)</span>
                : <span className="text-red-700">✗ 만료 — 재검증 필요</span>}
            </dd>
          </dl>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={handleValidate}
              disabled={saving}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              재검증
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={saving}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              삭제
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleSave} className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="font-medium">{status?.registered ? '재등록 (덮어쓰기)' : '신규 등록'}</h3>
        <Field label="App Key (필수)" name="app_key" value={form.app_key} onChange={setForm} required />
        <Field label="App Secret (필수)" name="app_secret" value={form.app_secret} onChange={setForm} required type="password" />
        <Field label="계좌번호 앞 8자리 (필수)" name="acnt_no" value={form.acnt_no} onChange={setForm} required />
        <Field label="계좌상품코드(주식, 2자리, 예: 01)" name="acnt_prdt_cd_stk" value={form.acnt_prdt_cd_stk} onChange={setForm} required maxLength={2} />
        <Field label="계좌상품코드(선물옵션, 선택, 예: 03)" name="acnt_prdt_cd_fno" value={form.acnt_prdt_cd_fno} onChange={setForm} maxLength={2} />
        <Field label="HTS ID (체결통보 WS, 선택)" name="hts_id" value={form.hts_id} onChange={setForm} />
        <Field label="Base URL (모의투자 시 변경)" name="base_url" value={form.base_url} onChange={setForm} />

        <button
          type="submit"
          disabled={saving}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '검증 중...' : '검증 후 저장'}
        </button>
      </form>
    </div>
  )
}

function Field({ label, name, value, onChange, type = 'text', required = false, maxLength }) {
  return (
    <label className="block text-sm">
      <span className="text-gray-700 font-medium">{label}</span>
      <input
        type={type}
        name={name}
        value={value}
        onChange={(e) => onChange((prev) => ({ ...prev, [name]: e.target.value }))}
        required={required}
        maxLength={maxLength}
        className="mt-1 block w-full border border-gray-300 rounded px-3 py-1.5 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
    </label>
  )
}
