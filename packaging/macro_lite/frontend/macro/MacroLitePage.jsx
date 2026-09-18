import { useEffect } from 'react'
import {
  useMacroCycle, useYieldCurve, useCreditSpread,
  useCurrencies, useCommodities,
} from './hooks/useMacro'
import MacroCycleSection from './components/MacroCycleSection'
import YieldCurveSection from './components/YieldCurveSection'
import CreditSpreadSection from './components/CreditSpreadSection'
import CurrencySection from './components/CurrencySection'
import CommoditySection from './components/CommoditySection'

export default function MacroLitePage() {
  const cycle = useMacroCycle()
  const yieldCurve = useYieldCurve()
  const creditSpread = useCreditSpread()
  const currencies = useCurrencies()
  const commodities = useCommodities()

  useEffect(() => {
    cycle.load()
    yieldCurve.load()
    creditSpread.load()
    currencies.load()
    commodities.load()
  }, [])

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">매크로 분석</h1>
      <MacroCycleSection data={cycle.data} loading={cycle.loading} error={cycle.error} />
      <YieldCurveSection data={yieldCurve.data} loading={yieldCurve.loading} error={yieldCurve.error} />
      <CreditSpreadSection data={creditSpread.data} loading={creditSpread.loading} error={creditSpread.error} />
      <CurrencySection data={currencies.data} loading={currencies.loading} error={currencies.error} />
      <CommoditySection data={commodities.data} loading={commodities.loading} error={commodities.error} />
    </div>
  )
}
