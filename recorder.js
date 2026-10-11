// Records the microphone with MediaRecorder, then converts the result to
// 16 kHz mono 16-bit WAV in the browser. That keeps the upload small (good on
// low-bandwidth connections) and means the server needs no audio codecs.
const TARGET_RATE = 16000;

export function micSupported() {
  return !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

export class Recorder {
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    this.chunks = [];
    this.mr = new MediaRecorder(this.stream);
    this.mr.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.mr.start();
  }

  stop() {
    return new Promise((resolve, reject) => {
      this.mr.onstop = async () => {
        this.stream.getTracks().forEach((t) => t.stop());
        try {
          resolve(await toWav(new Blob(this.chunks, { type: this.mr.mimeType })));
        } catch (e) {
          reject(e);
        }
      };
      this.mr.stop();
    });
  }

  cancel() {
    try { this.mr?.state !== "inactive" && this.mr.stop(); } catch { /* already stopped */ }
    this.stream?.getTracks().forEach((t) => t.stop());
  }
}

async function toWav(blob) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  let decoded;
  try {
    decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  } finally {
    ctx.close();
  }
  // Resample + downmix to mono with an offline context.
  const frames = Math.ceil(decoded.duration * TARGET_RATE);
  const offline = new OfflineAudioContext(1, frames, TARGET_RATE);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start();
  const samples = (await offline.startRendering()).getChannelData(0);
  return encodeWav(samples, TARGET_RATE);
}

function encodeWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => {
    const c = Math.max(-1, Math.min(1, s));
    v.setInt16(44 + i * 2, c < 0 ? c * 0x8000 : c * 0x7fff, true);
  });
  return new Blob([buf], { type: "audio/wav" });
}
