export default function AddStockSlot({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="bg-gray-800 rounded-xl p-3 h-full min-h-[120px] flex flex-col items-center justify-center gap-2 border-2 border-dashed border-gray-600 hover:border-gray-400 hover:bg-gray-750 transition-all text-gray-500 hover:text-gray-300 w-full"
    >
      <span className="text-3xl font-light leading-none">+</span>
      <span className="text-xs">종목 추가</span>
    </button>
  )
}
