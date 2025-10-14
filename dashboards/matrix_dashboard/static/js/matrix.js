// Matrix Rain Module
const MatrixRain = (() => {
  let canvas, ctx, w, h, columns, drops;
  let config = {};
  let running = true;
  let lastTime = 0;

  const defaultConfig = {
    canvasId: 'matrix-canvas',
    fontSize: 14,
    density: 1.0,
    speed: 1,
    glow: true,
    tint: '#00ff41',
    background: '#050a08',
    charset: 'アカサタナABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  };

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    const fs = config.fontSize;
    columns = Math.floor(w / fs);
    drops = Array.from({ length: Math.floor(columns * config.density) }, () =>
      Math.floor(Math.random() * -50)
    );
  }

  function draw(timestamp) {
    if (!running) return;
    const delta = timestamp - lastTime; // not used now, kept for timing adjustments
    lastTime = timestamp;

    ctx.fillStyle = 'rgba(0, 15, 5, 0.10)';
    ctx.fillRect(0, 0, w, h);

    ctx.font = `${config.fontSize}px monospace`;
    ctx.textBaseline = 'top';

    drops.forEach((y, i) => {
      const x = i * config.fontSize;
      const ch = config.charset.charAt(Math.floor(Math.random() * config.charset.length));
      const baseColor = config.tint;
      ctx.fillStyle = baseColor;
      if (config.glow) {
        ctx.shadowColor = baseColor;
        ctx.shadowBlur = 12;
      } else {
        ctx.shadowBlur = 0;
      }
      ctx.fillText(ch, x, y * config.fontSize);
      drops[i] = y * config.fontSize > h && Math.random() > 0.975 ? 0 : y + config.speed;
    });

    requestAnimationFrame(draw);
  }

  function init(userConfig = {}) {
    config = { ...defaultConfig, ...userConfig };
    canvas = document.getElementById(config.canvasId);
    if (!canvas) {
      console.error('MatrixRain: canvas not found');
      return;
    }
    ctx = canvas.getContext('2d');
    window.addEventListener('resize', resize, { passive: true });
    resize();
    running = true;
    requestAnimationFrame(draw);
  }

  function pause() { running = false; }
  function resume() {
    if (!running) {
      running = true;
      lastTime = performance.now();
      requestAnimationFrame(draw);
    }
  }
  function setSpeed(s) { config.speed = s; }
  function setFontSize(px) { config.fontSize = px; resize(); }
  function setCharset(chars) { config.charset = chars; }
  function setTint(color) { config.tint = color; }
  function toggleGlow(on) { config.glow = on; }

  return { init, pause, resume, setSpeed, setFontSize, setCharset, setTint, toggleGlow };
})();
