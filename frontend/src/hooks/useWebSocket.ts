import type { WSMessage } from '@/types'

type StatusCallback = (msg: WSMessage) => void

const connections = new Map<string, WebSocket>()

export function connectReviewWS(
  runId: string,
  onMessage: StatusCallback
): () => void {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const url = `${protocol}//${host}/ws/review/${runId}`

  if (connections.has(runId)) {
    connections.get(runId)?.close()
  }

  const ws = new WebSocket(url)
  connections.set(runId, ws)

  ws.onmessage = (event) => {
    try {
      const msg: WSMessage = JSON.parse(event.data)
      onMessage(msg)
    } catch {
      // ignore parse errors
    }
  }

  ws.onclose = () => {
    connections.delete(runId)
  }

  // 返回清理函数
  return () => {
    ws.close()
    connections.delete(runId)
  }
}
