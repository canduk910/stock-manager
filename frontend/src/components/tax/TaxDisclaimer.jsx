export default function TaxDisclaimer() {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-800">
      <span className="font-medium">참고용 계산:</span>{' '}
      본 양도세 계산은 yfinance 환율 기준이며, 실제 세금 신고 시{' '}
      <span className="font-semibold">서울외국환중개 공시 매매기준율</span>을 사용하십시오.
      기본공제 250만원, 세율 22% (양도소득세 20% + 지방소득세 2%) 기준.
    </div>
  )
}
