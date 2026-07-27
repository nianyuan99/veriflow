import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts'

const SEVERITY_COLORS: Record<string, string> = {
  P0: '#ef4444',
  P1: '#eab308',
  P2: '#3b82f6',
  P3: '#71717a',
}

interface FindingsChartProps {
  data: { name: string; count: number }[]
}

export function FindingsBarChart({ data }: FindingsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 0, right: 0, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis
          dataKey="name"
          tick={{ fill: '#a1a1aa', fontSize: 11 }}
          axisLine={{ stroke: '#27272a' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#a1a1aa', fontSize: 11 }}
          axisLine={{ stroke: '#27272a' }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: '#a1a1aa' }}
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={SEVERITY_COLORS[entry.name] || '#71717a'}
              fillOpacity={0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function SeverityPieChart({
  p0,
  p1,
  p2,
  p3,
}: {
  p0: number
  p1: number
  p2: number
  p3: number
}) {
  const data = useMemo(
    () => [
      { name: 'P0', value: p0, color: '#ef4444' },
      { name: 'P1', value: p1, color: '#eab308' },
      { name: 'P2', value: p2, color: '#3b82f6' },
      { name: 'P3', value: p3, color: '#71717a' },
    ].filter((d) => d.value > 0),
    [p0, p1, p2, p3]
  )

  if (data.length === 0) return null

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} stroke="transparent" />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
