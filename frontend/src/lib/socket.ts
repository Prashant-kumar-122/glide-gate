import { io, Socket } from 'socket.io-client'

let _socket: Socket | null = null

export function getSocket(): Socket {
  if (!_socket) {
    _socket = io({ path: '/socket.io', transports: ['websocket', 'polling'], withCredentials: true })
  }
  return _socket
}
