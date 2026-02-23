export default function EmptyState({ message = '데이터가 없습니다.' }) {
  return (
    <div className="text-center py-16 text-gray-400 text-sm">{message}</div>
  )
}
