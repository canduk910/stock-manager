/**
 * 거시 팩터 (주성분 분해) 섹션 — 컨테이너.
 *
 * 거시 10지표 공분산 구조를 롤링 PCA로 5개 직교 주성분 축으로 압축 + 종목 거시베타.
 * 기존 심리/사이클(가중합산)과 차별화: "가중합 아닌 공분산 구조에서 추출한 직교 축".
 *
 * 4 서브카드: 신호등 레이더 / 설명력 추이 / loadings / 종목 베타.
 * status=pending(콜드스타트/배치 전) → EmptyState("매일 00:20 갱신").
 * 무거운 PCA는 일배치(KST 00:20)에서만 — 이 섹션은 read-only 조회.
 */
import LoadingSpinner from '../../common/LoadingSpinner'
import FactorSignalRadar from './FactorSignalRadar'
import FactorExplainedChart from './FactorExplainedChart'
import FactorLoadingsTable from './FactorLoadingsTable'
import FactorBetaTable from './FactorBetaTable'

function Card({ title, subtitle, children }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        {subtitle && <p className="text-[11px] text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

export default function FactorModelSection({ data, loading, error }) {
  const status = data?.status

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-gray-900">거시 팩터 (주성분 분해)</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          거시 10지표 7년 공분산 구조를 롤링 PCA로 5개 직교 축으로 분해 —
          가중합이 아닌 데이터에서 추출한 독립 축 + 내 종목의 거시 민감도
        </p>
      </div>

      {loading && (
        <div className="rounded-lg border bg-white p-8 shadow-sm flex justify-center">
          <LoadingSpinner />
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          거시 팩터 모델을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
        </div>
      )}

      {!loading && !error && status === 'pending' && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-sm text-gray-600 font-medium">데이터 준비 중</p>
          <p className="text-xs text-gray-400 mt-1">
            거시 팩터 모델은 매일 KST 00:20 일배치로 갱신됩니다. 잠시 후 다시 확인해 주세요.
          </p>
        </div>
      )}

      {!loading && !error && status === 'ok' && (
        <div className="space-y-4">
          {/* 상단: 신호등 + 설명력 추이 2컬럼 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card
              title="5축 신호등 (z-score)"
              subtitle={`기준일 ${data.as_of || '-'} · 직교 주성분의 현재 표준화 위치`}
            >
              <FactorSignalRadar signalLights={data.signal_lights} />
            </Card>
            <Card
              title="주성분 설명력 추이"
              subtitle="롤링 윈도우별 각 축이 설명하는 분산 비율 (축 회전 감지)"
            >
              <FactorExplainedChart
                explainedHistory={data.explained_history}
                pcLabels={data.pc_labels}
              />
            </Card>
          </div>

          {/* 중단: loadings */}
          <Card
            title="주성분 구성 (loadings)"
            subtitle="각 축을 구성하는 거시지표 가중치 — PC 라벨(경험칙) 재검증용"
          >
            <FactorLoadingsTable loadings={data.loadings} pcLabels={data.pc_labels} />
          </Card>

          {/* 하단: 종목 베타 */}
          <Card
            title="내 종목의 거시 베타"
            subtitle="관심·자문 종목을 5개 주성분에 회귀 — 거시 민감도(β) + 고유 스토리(1-R²)"
          >
            <FactorBetaTable stockBetas={data.stock_betas} pcLabels={data.pc_labels} />
          </Card>

          {/* 부분 실패 격리 표시 */}
          {Array.isArray(data.errors) && data.errors.length > 0 && (
            <p className="text-[11px] text-amber-600">
              일부 지표 수집 부분 실패: {data.errors.length}건 (나머지 정상 산출)
            </p>
          )}
        </div>
      )}
    </section>
  )
}
