import { create } from 'zustand'
import type { ReviewRun, Finding, WSMessage } from '@/types'

interface AppState {
  // 当前审查
  currentRun: ReviewRun | null
  setCurrentRun: (run: ReviewRun | null) => void

  // 审查历史
  history: ReviewRun[]
  setHistory: (history: ReviewRun[]) => void

  // 发现列表
  findings: Finding[]
  setFindings: (findings: Finding[]) => void

  // WebSocket 实时状态
  wsStatus: string
  setWsStatus: (status: string) => void

  // Sidebar
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentRun: null,
  setCurrentRun: (run) => set({ currentRun: run }),

  history: [],
  setHistory: (history) => set({ history }),

  findings: [],
  setFindings: (findings) => set({ findings }),

  wsStatus: '',
  setWsStatus: (status) => set({ wsStatus: status }),

  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
