import { useEffect } from 'react'
import { useMacroIndices, useMacroSentiment, useMacroNews, useMacroInvestorQuotes } from '../hooks/useMacro'
import IndexSection from '../components/macro/IndexSection'
import SentimentSection from '../components/macro/SentimentSection'
import NewsSection from '../components/macro/NewsSection'
import InvestorSection from '../components/macro/InvestorSection'

export default function MacroPage() {
  const indices = useMacroIndices()
  const sentiment = useMacroSentiment()
  const news = useMacroNews()
  const investors = useMacroInvestorQuotes()

  useEffect(() => {
    indices.load()
    sentiment.load()
    news.load()
    investors.load()
  }, [])

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">매크로 분석</h1>
      <IndexSection data={indices.data} loading={indices.loading} error={indices.error} />
      <SentimentSection data={sentiment.data} loading={sentiment.loading} error={sentiment.error} />
      <NewsSection data={news.data} loading={news.loading} error={news.error} />
      <InvestorSection data={investors.data} loading={investors.loading} error={investors.error} />
    </div>
  )
}
