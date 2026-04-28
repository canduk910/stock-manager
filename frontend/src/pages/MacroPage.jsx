import { useEffect } from 'react'
import {
  useMacroIndices, useMacroSentiment, useMacroNews, useMacroInvestorQuotes,
  useMacroCycle, useYieldCurve, useCreditSpread,
  useCurrencies, useCommodities, useSectorHeatmap,
} from '../hooks/useMacro'
import MacroCycleSection from '../components/macro/MacroCycleSection'
import IndexSection from '../components/macro/IndexSection'
import SentimentSection from '../components/macro/SentimentSection'
import YieldCurveSection from '../components/macro/YieldCurveSection'
import CreditSpreadSection from '../components/macro/CreditSpreadSection'
import CurrencySection from '../components/macro/CurrencySection'
import CommoditySection from '../components/macro/CommoditySection'
import SectorHeatmapSection from '../components/macro/SectorHeatmapSection'
import NewsSection from '../components/macro/NewsSection'
import InvestorSection from '../components/macro/InvestorSection'

export default function MacroPage() {
  const indices = useMacroIndices()
  const sentiment = useMacroSentiment()
  const news = useMacroNews()
  const investors = useMacroInvestorQuotes()
  const cycle = useMacroCycle()
  const yieldCurve = useYieldCurve()
  const creditSpread = useCreditSpread()
  const currencies = useCurrencies()
  const commodities = useCommodities()
  const sectorHeatmap = useSectorHeatmap()

  useEffect(() => {
    indices.load()
    sentiment.load()
    news.load()
    investors.load()
    cycle.load()
    yieldCurve.load()
    creditSpread.load()
    currencies.load()
    commodities.load()
    sectorHeatmap.load()
  }, [])

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">매크로 분석</h1>
      <MacroCycleSection data={cycle.data} loading={cycle.loading} error={cycle.error} />
      <IndexSection data={indices.data} loading={indices.loading} error={indices.error} />
      <SentimentSection data={sentiment.data} loading={sentiment.loading} error={sentiment.error} />
      <YieldCurveSection data={yieldCurve.data} loading={yieldCurve.loading} error={yieldCurve.error} />
      <CreditSpreadSection data={creditSpread.data} loading={creditSpread.loading} error={creditSpread.error} />
      <CurrencySection data={currencies.data} loading={currencies.loading} error={currencies.error} />
      <CommoditySection data={commodities.data} loading={commodities.loading} error={commodities.error} />
      <SectorHeatmapSection data={sectorHeatmap.data} loading={sectorHeatmap.loading} error={sectorHeatmap.error} />
      <NewsSection data={news.data} loading={news.loading} error={news.error} />
      <InvestorSection data={investors.data} loading={investors.loading} error={investors.error} />
    </div>
  )
}
