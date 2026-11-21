// Pure sphere math for the overlay, shared by overlay.js and the self-test. No DOM, no Electron.
(function (root) {
  const COUNT = 520;
  const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

  /** n points spread evenly over a unit sphere. */
  function fibonacciSphere(n = COUNT) {
    const points = [];
    for (let i = 0; i < n; i++) {
      const y = 1 - (2 * (i + 0.5)) / n;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const a = i * GOLDEN_ANGLE;
      points.push({ x: Math.cos(a) * r, y, z: Math.sin(a) * r });
    }
    return points;
  }

  /** Rotate a unit vector: yaw around Y, then pitch around X. */
  function rotate(p, yaw, pitch) {
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    const x1 = p.x * cy + p.z * sy;
    const z1 = -p.x * sy + p.z * cy;
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    return { x: x1, y: p.y * cp - z1 * sp, z: p.y * sp + z1 * cp };
  }

  /** One surface ripple band, -1 to 1. */
  function wave(p, t) {
    return Math.sin(p.y * 7 - t * 9) * 0.5 + Math.sin(Math.atan2(p.z, p.x) * 5 + t * 4) * 0.5;
  }

  /** Screen points for one frame. Orthographic, with voice energy moving the surface. */
  function frame(points, { yaw = 0, pitch = 0, t = 0, level = 0, radius, cx, cy }) {
    return points.map((p) => {
      const r = rotate(p, yaw, pitch);
      const k = radius * (1 + wave(p, t) * level * 0.18);
      return { x: cx + r.x * k, y: cy + r.y * k, z: r.z };
    });
  }

  const api = { COUNT, fibonacciSphere, rotate, wave, frame };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Sphere = api;
})(this);
