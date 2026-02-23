import DataTable from '../common/DataTable'

function fmtDate(s) {
  if (!s || s.length !== 8) return s || '-'
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
}

const REPORT_TYPE_COLORS = {
  '사업보고서': 'bg-purple-100 text-purple-700',
  '반기보고서': 'bg-blue-100 text-blue-700',
  '분기보고서': 'bg-teal-100 text-teal-700',
}

const COLUMNS = [
  { key: 'stock_code', label: '종목코드', align: 'center' },
  { key: 'corp_name', label: '종목명', align: 'left' },
  {
    key: 'report_type',
    label: '보고서 종류',
    align: 'center',
    render: (v) => {
      const cls = REPORT_TYPE_COLORS[v] || 'bg-gray-100 text-gray-700'
      return <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${cls}`}>{v}</span>
    },
  },
  {
    key: 'report_name',
    label: '보고서명',
    align: 'left',
    render: (v, row) =>
      row.dart_url ? (
        <a
          href={row.dart_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 hover:underline"
        >
          {v}
        </a>
      ) : (
        v
      ),
  },
  { key: 'rcept_dt', label: '제출일', align: 'center', render: fmtDate },
  { key: 'flr_nm', label: '제출인', align: 'left' },
]

export default function FilingsTable({ filings }) {
  return <DataTable columns={COLUMNS} data={filings} rowKey="stock_code" />
}
