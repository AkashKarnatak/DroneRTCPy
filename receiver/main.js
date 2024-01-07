import { createSocket } from './socket.js'

const $ = (x) => document.querySelector(x)
const esc = (x) => {
  const txt = document.createTextNode(x)
  const p = document.createElement('p')
  p.appendChild(txt)
  return p.innerHTML
}

const ws = await createSocket()

let pc

const $videoPeer = $('#video-peer')
const $messageBox = $('#message-box')
const $sendBtn = $('#send-btn')

$sendBtn.addEventListener('click', () => {
  ws.emit('msg', $messageBox.value)
  $messageBox.value = ''
})

const initializeConnection = async () => {
  console.log('creating rtc')

  const iceConfig = {
    iceServers: [
      {
        urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'],
      },
    ],
  }

  pc = new RTCPeerConnection(iceConfig)
  pc.sentRemoteDescription = false

  pc.oniceconnectionstatechange = async function () {
    console.log(pc.iceConnectionState)
    if (
      pc.iceConnectionState === 'disconnected' ||
      pc.iceConnectionState === 'closed'
    ) {
      pc.close()
      await initializeConnection()
    }
  }

  $videoPeer.onchange = () => {
    console.log('changed')
  }

  pc.ontrack = (event) => {
    console.log('received track')
    $videoPeer.srcObject = event.streams[0]
  }

  ws.emit('clientsOnline')
  ws.emit('match', { type: 'receiver', id: 'droneId' }) // TODO: create random id
}

ws.register('clientsOnline', async (data) => {
  console.log(data)
})

ws.register('connected', async (data) => {
  console.log('connected')
})

ws.register('offer', async (data) => {
  console.log('recevied offer')
  await pc.setRemoteDescription(data)
  const answer = await pc.createAnswer()
  await pc.setLocalDescription(answer)
  // TODO: add delay
  ws.emit('answer', pc.localDescription)
})

ws.register('disconnect', async () => {
  console.log('received disconnect request')
  pc.close()
  await initializeConnection()
})

await initializeConnection()
