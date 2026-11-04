// Records what you see and hear (canvas + master audio bus) to a WebM file in the browser.
export class Recorder {
  constructor(canvas, audio) {
    this.canvas = canvas;
    this.audio = audio;
    this.rec = null;
    this.chunks = [];
  }

  get active() { return !!this.rec && this.rec.state === 'recording'; }

  start() {
    const stream = this.canvas.captureStream(30);
    for (const t of this.audio.recDest.stream.getAudioTracks()) stream.addTrack(t);
    const mime = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4']
      .find((m) => MediaRecorder.isTypeSupported(m));
    this.rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 8_000_000 });
    this.chunks = [];
    this.rec.ondataavailable = (e) => { if (e.data.size) this.chunks.push(e.data); };
    this.rec.start(1000);
    this.startedAt = Date.now();
    this.mime = mime;
  }

  stop() {
    return new Promise((resolve) => {
      if (!this.rec) return resolve(null);
      this.rec.onstop = () => {
        const blob = new Blob(this.chunks, { type: this.mime });
        this.rec = null;
        resolve(blob);
      };
      this.rec.stop();
    });
  }

  download(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);
  }
}
