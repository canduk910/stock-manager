/**
 * Step 1: 전략 메타데이터 입력.
 *
 * 전략명, 설명, 카테고리, 태그를 입력한다.
 */
import { useState, useCallback } from 'react'

const CATEGORY_LABELS = {
  trend: '추세추종',
  momentum: '모멘텀',
  mean_reversion: '역추세',
  volatility: '변동성',
  composite: '복합',
}

export default function StepMetadata({ metadata, onUpdate }) {
  const [tagInput, setTagInput] = useState('')

  const handleTagKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const tag = tagInput.trim()
      if (tag && !(metadata.tags || []).includes(tag)) {
        onUpdate('tags', [...(metadata.tags || []), tag])
      }
      setTagInput('')
    }
  }, [tagInput, metadata.tags, onUpdate])

  const removeTag = useCallback((idx) => {
    onUpdate('tags', (metadata.tags || []).filter((_, i) => i !== idx))
  }, [metadata.tags, onUpdate])

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-base font-semibold text-gray-900 mb-4">전략 기본 정보</h3>

      {/* 전략명 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          전략명 <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={metadata.name || ''}
          onChange={(e) => onUpdate('name', e.target.value)}
          placeholder="전략 이름을 입력하세요"
          className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          required
        />
      </div>

      {/* 설명 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">설명</label>
        <textarea
          value={metadata.description || ''}
          onChange={(e) => onUpdate('description', e.target.value)}
          placeholder="전략에 대한 간단한 설명"
          rows={3}
          className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
        />
      </div>

      {/* 카테고리 */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">카테고리</label>
        <select
          value={metadata.category || 'trend'}
          onChange={(e) => onUpdate('category', e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* 태그 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">태그</label>
        <input
          type="text"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={handleTagKeyDown}
          placeholder="태그 입력 + Enter"
          className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        {(metadata.tags || []).length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(metadata.tags || []).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
              >
                {tag}
                <button
                  onClick={() => removeTag(idx)}
                  className="hover:text-red-500 transition-colors"
                  type="button"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
