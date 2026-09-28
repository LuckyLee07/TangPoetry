// Original cover remains the static fallback. Only the isolated foliage is deformed.
export class CoverMotionClock {
  constructor() { this.elapsed = 0; this.startedAt = null; }
  value(now) { return this.elapsed + (this.startedAt === null ? 0 : Math.max(0, now - this.startedAt)); }
  setRunning(running, now) {
    if (running === (this.startedAt !== null)) return;
    this.elapsed = this.value(now);
    this.startedAt = running ? now : null;
  }
}

export function coverCrop(imageWidth, imageHeight, width, height) {
  const scale = Math.max(width / imageWidth, height / imageHeight);
  const x = width / (imageWidth * scale), y = height / (imageHeight * scale);
  return [(1 - x) * 0.5, (1 - y) * 0.3, x, y]; // Matches the poster's object-position: center 30%.
}

const vertexSource = `
attribute vec2 a_position;
varying vec2 v_uv;
void main() { v_uv = (a_position + 1.0) * 0.5; gl_Position = vec4(a_position, 0.0, 1.0); }
`;
const fragmentSource = `
precision highp float;
varying vec2 v_uv;
uniform sampler2D u_original;
uniform sampler2D u_background;
uniform sampler2D u_foliage;
uniform vec2 u_size;
uniform vec4 u_crop;
uniform float u_time;
vec2 branchOffset(vec2 uv) {
  float root = mix(0.18, 0.035, smoothstep(0.0, 0.40, uv.x));
  float tip = mix(0.63, 0.49, smoothstep(0.32, 0.70, uv.x));
  tip = mix(tip, 0.24, smoothstep(0.72, 1.0, uv.x));
  float along = clamp((uv.y - root) / (tip - root), 0.0, 1.0);
  float phase = 1.05 * smoothstep(0.15, 0.42, uv.x) + 0.8 * smoothstep(0.58, 0.87, uv.x);
  float wind = 0.78 * sin(u_time * 0.42 - along * 0.55 + phase)
             + 0.22 * sin(u_time * 0.67 - along * 0.35 + phase * 0.5);
  float sway = min(19.0, u_size.x * 0.048) * along * along * wind * smoothstep(0.0, 3.0, u_time);
  // A smooth arc avoids the vertical velocity cusp that abs(sway) introduces at every crossing.
  return vec2(sway, sway * sway / 300.0 * along) / u_size * u_crop.zw;
}
vec4 sampleImage(sampler2D image, vec2 uv) { return texture2D(image, vec2(uv.x, 1.0 - uv.y)); }
vec3 foliageAt(vec2 uv) {
  if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return vec3(1.0);
  return sampleImage(u_foliage, uv).rgb;
}
void main() {
  vec2 screen = vec2(v_uv.x, 1.0 - v_uv.y);
  vec2 uv = u_crop.xy + screen * u_crop.zw;
  vec3 base = sampleImage(u_background, uv).rgb;
  // Keep the original figures, street and puddles byte-for-byte in their own stationary layer.
  base = mix(base, sampleImage(u_original, uv).rgb, smoothstep(0.63, 0.67, uv.y));
  vec2 leafUV = uv + branchOffset(uv);
  // Soften only the isolated leaf edges, leaving the original scene sharp.
  vec2 feather = 0.4 / u_size * u_crop.zw;
  vec3 matte = foliageAt(leafUV) * 0.40
             + foliageAt(leafUV + vec2(feather.x, 0.0)) * 0.15
             + foliageAt(leafUV - vec2(feather.x, 0.0)) * 0.15
             + foliageAt(leafUV + vec2(0.0, feather.y)) * 0.15
             + foliageAt(leafUV - vec2(0.0, feather.y)) * 0.15;
  float alpha = 1.0 - min(matte.r, min(matte.g, matte.b));
  if (alpha > 0.001) {
    vec3 ink = clamp((matte - vec3(1.0 - alpha)) / alpha, 0.0, 1.0);
    ink = mix(vec3(dot(ink, vec3(0.2126, 0.7152, 0.0722))), ink, 0.54);
    ink = mix(ink, vec3(0.30, 0.32, 0.23), 0.12);
    base = mix(base, ink, alpha * smoothstep(0.01, 0.065, alpha) * 0.56);
  }
  gl_FragColor = vec4(base, 1.0);
}
`;

function willowRenderer(canvas, images) {
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false, depth: false, stencil: false });
  if (!gl) return null;
  const shaders = [], textures = [], program = gl.createProgram();
  let buffer;
  const dispose = () => {
    shaders.forEach(shader => gl.deleteShader(shader));
    textures.forEach(texture => gl.deleteTexture(texture));
    if (buffer) gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
  };
  try {
    for (const [type, source] of [[gl.VERTEX_SHADER, vertexSource], [gl.FRAGMENT_SHADER, fragmentSource]]) {
      const shader = gl.createShader(type); shaders.push(shader);
      gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error('Cover shader unavailable');
      gl.attachShader(program, shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('Cover renderer unavailable');
    gl.useProgram(program);
    buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const names = ['u_original', 'u_background', 'u_foliage'];
    images.forEach((image, index) => {
      const texture = gl.createTexture(); textures.push(texture);
      gl.activeTexture(gl.TEXTURE0 + index); gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      gl.uniform1i(gl.getUniformLocation(program, names[index]), index);
    });
    const size = gl.getUniformLocation(program, 'u_size'), crop = gl.getUniformLocation(program, 'u_crop'), time = gl.getUniformLocation(program, 'u_time');
    return {
      draw(width, height, seconds) {
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.uniform2f(size, width, height);
        gl.uniform4fv(crop, coverCrop(images[0].naturalWidth, images[0].naturalHeight, width, height));
        gl.uniform1f(time, seconds);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
      }, dispose
    };
  } catch { dispose(); return null; }
}

function rainHash(value) { return ((Math.sin(value * 127.1 + 311.7) * 43758.5453) % 1 + 1) % 1; }

// Short exposure streaks follow their actual velocity; each new drop has a new seeded location.
export function coverRainDrop(index, time, width, height) {
  const duration = 2.7 + rainHash(index + 1) * 1.3;
  const life = time / duration + rainHash(index + 80);
  const cycle = Math.floor(life), phase = life - cycle;
  const seed = index * 17 + cycle * 131;
  const vx = 8 + rainHash(seed + 2) * 7, vy = height * 0.85 / duration;
  const age = phase * duration;
  const x = rainHash(seed + 3) * (width + 30) - 30 + vx * age;
  const y = -12 + vy * age;
  const exposure = 0.023 + rainHash(seed + 5) * 0.007;
  const quietTitle = x / width > 0.70 && y / height < 0.53 ? 0.35 : 1;
  const fade = Math.min(1, phase * 15) * Math.max(0, Math.min(1, (0.79 - y / height) / 0.13));
  return {x, y, dx: vx * exposure, dy: vy * exposure,
    alpha: (0.18 + rainHash(seed + 7) * 0.10) * fade * quietTitle * Math.min(1, time / 2),
    width: 0.7 + rainHash(seed + 9) * 0.2};
}

function drawRain(context, width, height, time) {
  context.clearRect(0, 0, width, height);
  context.lineCap = 'round';
  for (let index = 0; index < 48; index++) {
    const drop = coverRainDrop(index, time, width, height);
    const ink = index % 4 === 0 ? '255,255,255' : '90,99,93';
    const gradient = context.createLinearGradient(drop.x, drop.y, drop.x + drop.dx, drop.y + drop.dy);
    gradient.addColorStop(0, `rgba(${ink},0)`);
    gradient.addColorStop(0.30, `rgba(${ink},${drop.alpha})`);
    gradient.addColorStop(0.75, `rgba(${ink},${drop.alpha})`);
    gradient.addColorStop(1, `rgba(${ink},0)`);
    context.strokeStyle = gradient; context.lineWidth = drop.width;
    context.beginPath(); context.moveTo(drop.x, drop.y);
    context.lineTo(drop.x + drop.dx, drop.y + drop.dy); context.stroke();
  }
}

export function setupCoverAtmosphere() {
  const art = document.querySelector('.home-art'), image = art.querySelector('img');
  const setting = document.querySelector('#settingCoverMotion'), hint = document.querySelector('#coverMotionHint');
  const reader = document.querySelector('.reader'), reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const storageKey = 'tang-cover-motion-v1';
  try { setting.checked = localStorage.getItem(storageKey) !== 'false'; } catch { setting.checked = true; }
  const willow = document.createElement('canvas'), rain = document.createElement('canvas');
  willow.className = 'cover-willow'; rain.className = 'cover-rain';
  art.append(willow, rain);
  const context = rain.getContext('2d'), clock = new CoverMotionClock();
  let renderer = null, frame = null, lastFrame = -Infinity, running = false, width = 0, height = 0;
  function draw(time) {
    if (!renderer || !context || !width || !height) return;
    renderer.draw(width, height, time); drawRain(context, width, height, time);
  }
  function tick(now) {
    frame = null;
    if (!running) return;
    if (now - lastFrame >= 1000 / 60 - 0.5) { draw(clock.value(now / 1000)); lastFrame = now; }
    frame = requestAnimationFrame(tick);
  }
  function update() {
    const available = setting.checked && !reduced.matches && renderer && context;
    running = Boolean(available && !document.hidden && document.hasFocus() && reader.dataset.home === 'true' && !document.querySelector('dialog[open]'));
    clock.setRunning(running, performance.now() / 1000);
    art.dataset.atmosphere = available ? (running ? 'playing' : 'paused') : 'still';
    hint.textContent = reduced.matches ? '系统已开启减少动态效果，首页保持静止。' : '柳条轻摆，细雨轻落。默认开启，可随时关闭。';
    if (running && frame === null) frame = requestAnimationFrame(tick);
    if (!running && frame !== null) { cancelAnimationFrame(frame); frame = null; }
  }
  function resize() {
    const bounds = art.getBoundingClientRect(), ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = bounds.width; height = bounds.height;
    if (!width || !height) return;
    for (const canvas of [willow, rain]) {
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    }
    context?.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw(clock.value(performance.now() / 1000));
  }
  async function initialize() {
    try {
      const background = new Image(), foliage = new Image();
      background.src = 'assets/cover-layers/background.png';
      foliage.src = 'assets/cover-layers/willow-matte.png';
      await Promise.all([image.decode(), background.decode(), foliage.decode()]);
      renderer?.dispose(); renderer = willowRenderer(willow, [image, background, foliage]);
      resize(); update();
    } catch { renderer = null; update(); }
  }
  setting.addEventListener('change', () => {
    try { localStorage.setItem(storageKey, String(setting.checked)); } catch {}
    update();
  });
  reduced.addEventListener('change', update);
  document.addEventListener('visibilitychange', update);
  window.addEventListener('focus', update); window.addEventListener('blur', update);
  window.addEventListener('pagehide', () => {
    running = false; clock.setRunning(false, performance.now() / 1000);
    if (frame !== null) cancelAnimationFrame(frame); frame = null;
  });
  window.addEventListener('pageshow', update);
  window.addEventListener('storage', event => {
    if (event.key === storageKey) { setting.checked = event.newValue !== 'false'; update(); }
  });
  willow.addEventListener('webglcontextlost', event => { event.preventDefault(); renderer = null; update(); });
  willow.addEventListener('webglcontextrestored', initialize);
  new MutationObserver(update).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['open', 'data-home'] });
  new ResizeObserver(resize).observe(art);
  update(); void initialize();
}
