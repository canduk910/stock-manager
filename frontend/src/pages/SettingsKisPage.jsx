/**
 * /settings/kis — 사용자 본인 KIS 자격증명 등록/조회/삭제/재검증.
 *
 * R8 (KIS 멀티 계좌, 2026-05-15): 카드 그리드 + 라벨별 CRUD.
 * 카드 = 라벨 + 마스킹된 계좌번호 + 검증 상태 + "기본" 배지 + 수정/삭제 버튼.
 * "+ 계좌 추가" 버튼 → 모달.
 */
import { useEffect, useState } from 'react'
import {
  listAccounts,
  createAccount,
  updateAccount,
  deleteAccount,
  setDefaultAccount,
  validateAccount,
} from '../api/me'
import { useAuth } from '../hooks/useAuth'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

const initialForm = {
  label: '',
  app_key: '',
  app_secret: '',
  acnt_no: '',
  acnt_prdt_cd_stk: '',
  acnt_prdt_cd_fno: '',
  hts_id: '',
  base_url: 'https://openapi.koreainvestment.com:9443',
}

export default function SettingsKisPage() {
  const { refreshUser } = useAuth()
  const [accounts, setAccounts] = useState([])
  const [defaultLabel, setDefaultLabel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [busy, setBusy] = useState(false)
  const [modalState, setModalState] = useState(null) // null | {mode:'create'|'edit', label?, form}

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await listAccounts()
      setAccounts(result.accounts || [])
      setDefaultLabel(result.default_label)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const closeModal = () => setModalState(null)

  const openCreate = () => setModalState({ mode: 'create', form: { ...initialForm } })
  const openEdit = (acc) => setModalState({
    mode: 'edit',
    label: acc.label,
    form: {
      label: acc.label,
      app_key: '',
      app_secret: '',
      acnt_no: '',
      acnt_prdt_cd_stk: acc.acnt_prdt_cd_stk || '',
      acnt_prdt_cd_fno: acc.acnt_prdt_cd_fno || '',
      hts_id: acc.hts_id || '',
      base_url: acc.base_url || initialForm.base_url,
    },
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!modalState) return
    setBusy(true)
    setError(null)
    setSuccess(null)
    try {
      const { mode, label, form } = modalState
      const payload = {}
      Object.entries(form).forEach(([k, v]) => {
        if (v === '' || v === null || v === undefined) return
        payload[k] = v
      })
      if (mode === 'create') {
        if (!payload.label) payload.label = '기본'
        await createAccount(payload)
        setSuccess(`계좌 '${payload.label}' 등록되었습니다.`)
      } else {
        await updateAccount(label, payload)
        setSuccess(`계좌 '${payload.label || label}' 갱신되었습니다.`)
      }
      closeModal()
      await load()
      await refreshUser?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const handleValidate = async (label) => {
    setBusy(true); setError(null); setSuccess(null)
    try {
      await validateAccount(label)
      setSuccess(`'${label}' 재검증 성공.`)
      await load()
      await refreshUser?.()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const handleSetDefault = async (label) => {
    setBusy(true); setError(null); setSuccess(null)
    try {
      await setDefaultAccount(label)
      setSuccess(`'${label}' 을 기본 계좌로 설정했습니다.`)
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const handleDelete = async (label) => {
    if (!confirm(`계좌 '${label}' 을 삭제하시겠습니까? (예약/주문 라벨은 NULL 폴백됩니다)`)) return
    setBusy(true); setError(null); setSuccess(null)
    try {
      await deleteAccount(label)
      setSuccess(`'${label}' 삭제되었습니다.`)
      await load()
      await refreshUser?.()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="max-w-5xl mx-auto py-6">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-semibold">KIS 자격증명 설정</h1>
        <button
          onClick={openCreate}
          disabled={busy}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          + 계좌 추가
        </button>
      </div>
      <p className="text-sm text-gray-600 mb-6">
        한국투자증권 OpenAPI 키. 잔고 합산, 계좌별 주문/예약, 체결통보 라벨링에 사용됩니다.
        키는 AES-GCM 으로 암호화되어 저장되며, 응답에는 마스킹된 일부만 노출됩니다.
      </p>

      {error && <ErrorAlert message={error} className="mb-4" />}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
          {success}
        </div>
      )}

      {accounts.length === 0 ? (
        <div className="p-8 text-center bg-gray-50 border border-dashed border-gray-300 rounded-lg">
          <p className="text-gray-600 mb-3">등록된 KIS 계좌가 없습니다.</p>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + 첫 계좌를 등록하세요
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((acc) => (
            <AccountCard
              key={acc.label}
              account={acc}
              isDefault={acc.label === defaultLabel}
              busy={busy}
              onValidate={() => handleValidate(acc.label)}
              onSetDefault={() => handleSetDefault(acc.label)}
              onEdit={() => openEdit(acc)}
              onDelete={() => handleDelete(acc.label)}
            />
          ))}
        </div>
      )}

      {modalState && (
        <AccountModal
          mode={modalState.mode}
          form={modalState.form}
          busy={busy}
          onChange={(updater) => setModalState((m) => m && ({ ...m, form: updater(m.form) }))}
          onSubmit={handleSubmit}
          onClose={closeModal}
        />
      )}
    </div>
  )
}

function AccountCard({ account, isDefault, busy, onValidate, onSetDefault, onEdit, onDelete }) {
  const border = account.is_active ? 'border-gray-200' : 'border-red-300'
  return (
    <div className={`p-4 bg-white border rounded-lg ${border} flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-lg">{account.label}</h3>
          {isDefault && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded">기본</span>
          )}
        </div>
        <span className={account.is_active ? 'text-green-700 text-xs' : 'text-red-700 text-xs'}>
          {account.is_active ? '✓ 활성' : '✗ 재검증 필요'}
        </span>
      </div>
      <dl className="text-xs grid grid-cols-2 gap-y-1">
        <dt className="text-gray-500">앱 키</dt>
        <dd className="font-mono">{account.app_key_masked}</dd>
        <dt className="text-gray-500">계좌번호</dt>
        <dd className="font-mono">{account.acnt_no_masked || '-'}</dd>
        <dt className="text-gray-500">상품(주식)</dt>
        <dd className="font-mono">{account.acnt_prdt_cd_stk}</dd>
        <dt className="text-gray-500">상품(FNO)</dt>
        <dd className="font-mono">{account.acnt_prdt_cd_fno || '-'}</dd>
        <dt className="text-gray-500">검증시각</dt>
        <dd className="font-mono text-[10px]">{account.validated_at || '-'}</dd>
      </dl>
      <div className="flex gap-1 mt-2 flex-wrap">
        <button onClick={onValidate} disabled={busy}
          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          재검증
        </button>
        {!isDefault && (
          <button onClick={onSetDefault} disabled={busy}
            className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50">
            기본 설정
          </button>
        )}
        <button onClick={onEdit} disabled={busy}
          className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded hover:bg-gray-200 disabled:opacity-50">
          수정
        </button>
        <button onClick={onDelete} disabled={busy}
          className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
          삭제
        </button>
      </div>
    </div>
  )
}

function AccountModal({ mode, form, busy, onChange, onSubmit, onClose }) {
  const title = mode === 'create' ? '계좌 추가' : `계좌 수정: ${form.label || ''}`
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onSubmit={onSubmit}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-lg p-6 w-full max-w-md space-y-3 max-h-[90vh] overflow-y-auto"
      >
        <h3 className="font-medium text-lg">{title}</h3>
        <Field label="라벨 (예: 주식, 연금, 미국)" name="label" value={form.label} onChange={onChange} required maxLength={50} />
        <Field label={`App Key${mode === 'edit' ? ' (변경 시만 입력)' : ' (필수)'}`}
          name="app_key" value={form.app_key} onChange={onChange} required={mode === 'create'} />
        <Field label={`App Secret${mode === 'edit' ? ' (변경 시만 입력)' : ' (필수)'}`}
          name="app_secret" value={form.app_secret} onChange={onChange} type="password" required={mode === 'create'} />
        <Field label={`계좌번호 앞 8자리${mode === 'edit' ? ' (변경 시만 입력)' : ' (필수)'}`}
          name="acnt_no" value={form.acnt_no} onChange={onChange} required={mode === 'create'} />
        <Field label="계좌상품코드(주식, 2자리) — 일반 01, 연금/IRP/ISA 등은 02·22 등 KIS 발급값 확인" name="acnt_prdt_cd_stk" value={form.acnt_prdt_cd_stk}
          onChange={onChange} required maxLength={2} />
        <Field label="계좌상품코드(선물옵션, 2자리, 선택)" name="acnt_prdt_cd_fno"
          value={form.acnt_prdt_cd_fno} onChange={onChange} maxLength={2} />
        <Field label="HTS ID (체결통보 WS, 선택)" name="hts_id" value={form.hts_id} onChange={onChange} />
        <Field label="Base URL" name="base_url" value={form.base_url} onChange={onChange} />
        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={busy}
            className="flex-1 px-3 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:opacity-50">
            {busy ? '검증 중...' : '검증 후 저장'}
          </button>
          <button type="button" onClick={onClose} disabled={busy}
            className="px-3 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 disabled:opacity-50">
            취소
          </button>
        </div>
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
        value={value || ''}
        onChange={(e) => onChange((prev) => ({ ...prev, [name]: e.target.value }))}
        required={required}
        maxLength={maxLength}
        className="mt-1 block w-full border border-gray-300 rounded px-3 py-1.5 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
    </label>
  )
}
