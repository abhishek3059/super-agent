/**
 * Live view of a bot's browser. Frames arrive as binary JPEGs over the app's WebSocket relay and are
 * drawn on a canvas. In control mode, pointer and key events on the canvas go back as input messages;
 * the server drops anything a watch-mode viewer sends.
 */
type Listener = (clean: boolean) => void;

const mods = (e: MouseEvent | KeyboardEvent | WheelEvent) => (e.altKey ? 1 : 0) | (e.ctrlKey ? 2 : 0) | (e.metaKey ? 4 : 0) | (e.shiftKey ? 8 : 0);
const BUTTONS = ['left', 'middle', 'right'];

export class ScreenStream {
  private ws: WebSocket;
  private canvas = document.createElement('canvas');
  private onConnect: Listener[] = [];
  private onDisconnect: Listener[] = [];
  private closed = false;

  constructor(el: HTMLElement, botId: string, control: boolean, token: string) {
    this.canvas.className = 'screen__frame';
    this.canvas.tabIndex = control ? 0 : -1;
    Object.assign(this.canvas.style, { width: '100%', height: '100%', display: 'block', outline: 'none', cursor: control ? 'default' : 'inherit' });
    el.appendChild(this.canvas);
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const mode = control ? 'control' : 'watch';
    const url = `${protocol}//${location.host}/api/bots/${encodeURIComponent(botId)}/screen?mode=${mode}`;
    this.ws = new WebSocket(url, ['hq-screen', `hq-session.${token}`]);
    this.ws.binaryType = 'blob';
    this.ws.onmessage = (m) => void this.receive(m.data);
    this.ws.onclose = (e) => { if (!this.closed) this.onDisconnect.forEach((f) => f(e.code === 1000)); };
    if (control) this.listen();
  }

  on(event: 'connect' | 'disconnect', f: Listener) { (event === 'connect' ? this.onConnect : this.onDisconnect).push(f); }
  focus() { this.canvas.focus(); }
  disconnect() { this.closed = true; this.ws.close(); this.canvas.remove(); }

  private async receive(data: string | Blob) {
    if (typeof data === 'string') {
      const m = JSON.parse(data);
      if (m.t === 'size') this.onConnect.forEach((f) => f(true));
      return;
    }
    const img = await createImageBitmap(data);
    if (this.canvas.width !== img.width || this.canvas.height !== img.height) { this.canvas.width = img.width; this.canvas.height = img.height; }
    this.canvas.getContext('2d')?.drawImage(img, 0, 0);
    img.close();
  }

  private send(m: object) { if (this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(m)); }

  /** Pointer position in the bot's page (a frame is the page at 1:1), whatever size the canvas is shown at. */
  private at(e: MouseEvent) {
    const r = this.canvas.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * this.canvas.width, y: ((e.clientY - r.top) / r.height) * this.canvas.height };
  }

  private listen() {
    const c = this.canvas;
    const mouse = (type: string) => (e: MouseEvent) => {
      e.preventDefault();
      if (type === 'mousePressed') c.focus();
      const held = type === 'mouseMoved' ? (e.buttons & 1 ? 'left' : 'none') : BUTTONS[e.button] ?? 'none';
      this.send({ t: 'mouse', type, ...this.at(e), button: held, clickCount: type === 'mouseMoved' ? 0 : Math.max(1, e.detail), modifiers: mods(e) });
    };
    c.addEventListener('mousedown', mouse('mousePressed'));
    c.addEventListener('mouseup', mouse('mouseReleased'));
    c.addEventListener('mousemove', mouse('mouseMoved'));
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    c.addEventListener('wheel', (e) => { e.preventDefault(); this.send({ t: 'mouse', type: 'mouseWheel', ...this.at(e), dx: e.deltaX, dy: e.deltaY, modifiers: mods(e) }); }, { passive: false });
    const key = (type: string) => (e: KeyboardEvent) => {
      e.preventDefault();
      const printable = e.key.length === 1 && !e.ctrlKey && !e.metaKey;
      this.send({ t: 'key', type, key: e.key, code: e.code, keyCode: e.keyCode, modifiers: mods(e), ...(type === 'keyDown' && (printable || e.key === 'Enter') ? { text: e.key === 'Enter' ? '\r' : e.key } : {}) });
    };
    c.addEventListener('keydown', key('keyDown'));
    c.addEventListener('keyup', key('keyUp'));
  }
}
