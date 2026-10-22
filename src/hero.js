/* ============================================================
   MuTechLab — 3D hero: muography tracker
   Four planes of triangular-prism plastic scintillator bars
   (alternating apex up / apex down, x/y alternating readout)
   with cosmic muons arriving with a cos²θ angular distribution.
   Adapted from the TDLI Muon Physics Group homepage hero.
   Build: npm run build  →  assets/js/hero.bundle.js
   ============================================================ */
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const CYAN = new THREE.Color(0x2fc8ff);
const BLUE = new THREE.Color(0x2251ff);
const WHITE = new THREE.Color(0xffffff);

const PLANES = 4;
const PLANE_GAP = 1.15;
const BARS = 20;          // triangular bars per plane
const SIZE_X = 5.6;
const SIZE_Z = 5.6;

function glowTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.25, 'rgba(160,230,255,0.85)');
  grd.addColorStop(1, 'rgba(0,120,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/* triangular prism along +z, centred, base width `b`, height `h`, length `L` */
function prismGeometry(b, h, L) {
  const s = new THREE.Shape();
  s.moveTo(-b / 2, -h / 2);
  s.lineTo(b / 2, -h / 2);
  s.lineTo(0, h / 2);
  s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: L, bevelEnabled: false });
  g.translate(0, 0, -L / 2);
  g.computeVertexNormals();
  return g;
}

export function initHero(canvas, opts = {}) {
  const onEvent = opts.onEvent || (() => {});
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = () => window.innerWidth < 860;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch (e) {
    return null; // no WebGL → CSS fallback stays visible
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, small() ? 1.5 : 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x03060b, 0.028);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.32;

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 200);

  // ---------- Lights ----------
  scene.add(new THREE.HemisphereLight(0x9cc4ff, 0x05070c, 0.5));
  const key = new THREE.DirectionalLight(0xe4f0ff, 2.0);
  key.position.set(7, 12, 6);
  key.castShadow = true;
  key.shadow.mapSize.set(small() ? 1024 : 2048, small() ? 1024 : 2048);
  Object.assign(key.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 });
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  key.shadow.radius = 4;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x2f6bff, 3.2);
  rim.position.set(-9, 3, -7);
  scene.add(rim);
  const fill = new THREE.PointLight(0x2fc8ff, 6, 12, 2);
  fill.position.set(-4, 1, 5);
  scene.add(fill);

  // ---------- Materials ----------
  const alu = new THREE.MeshStandardMaterial({ color: 0xb9c3d1, metalness: 1, roughness: 0.28 });
  const aluDark = new THREE.MeshStandardMaterial({ color: 0x3a4352, metalness: 0.9, roughness: 0.38 });
  const anod = new THREE.MeshStandardMaterial({ color: 0x0b0f16, metalness: 0.6, roughness: 0.42 });
  const steel = new THREE.MeshStandardMaterial({ color: 0x222833, metalness: 0.85, roughness: 0.5 });
  const pcb = new THREE.MeshStandardMaterial({ color: 0x0f3b2c, metalness: 0.2, roughness: 0.55 });
  const copper = new THREE.MeshStandardMaterial({ color: 0xd08a4a, metalness: 1, roughness: 0.3 });
  const cableMat = new THREE.MeshStandardMaterial({ color: 0x10141c, metalness: 0.1, roughness: 0.65 });
  const fiberMat = new THREE.MeshStandardMaterial({ color: 0x6fd36a, emissive: 0x2a7a26, emissiveIntensity: 0.35, roughness: 0.4 });
  const ledMat = new THREE.MeshBasicMaterial({ color: 0x3dffb4 });

  const cast = (m) => { m.castShadow = true; m.receiveShadow = true; return m; };
  const box = (w, h, d, mat) => cast(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat));

  // ---------- Detector ----------
  const det = new THREE.Group();
  scene.add(det);
  const planeY = [];
  const strips = [];
  const T = 0.22;          // prism height (scintillator thickness)
  const RAIL = 0.16;
  const RH = 0.3;

  for (let p = 0; p < PLANES; p++) {
    const y = (p - (PLANES - 1) / 2) * PLANE_GAP;
    planeY.push(y);
    const plane = new THREE.Group();
    plane.position.y = y;
    const alongX = p % 2 === 1;                  // bars run along x → measure z
    const span = alongX ? SIZE_Z : SIZE_X;       // measured direction
    const L = alongX ? SIZE_X : SIZE_Z;          // bar length
    const pitch = span / (BARS + 1);             // interleaved triangles: base = 2 × pitch
    const geo = prismGeometry(pitch * 2 * 0.97, T, L);
    const row = [];
    for (let i = 0; i < BARS; i++) {
      const mat = new THREE.MeshPhysicalMaterial({
        color: 0x16233a, metalness: 0.1, roughness: 0.5, clearcoat: 0.4, clearcoatRoughness: 0.4,
        emissive: CYAN, emissiveIntensity: 0,
      });
      const m = cast(new THREE.Mesh(geo, mat));
      const c = -span / 2 + pitch * (i + 1);
      if (i % 2 === 1) m.rotation.z = Math.PI;   // apex down, nests between neighbours
      const holder = new THREE.Group();
      holder.add(m);
      if (alongX) { holder.rotation.y = Math.PI / 2; holder.position.z = c; }
      else holder.position.x = c;
      plane.add(holder);
      // wavelength-shifting fibre through the bar, poking out at the readout end
      const f = cast(new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, L + 0.5, 6), fiberMat));
      f.rotation.x = Math.PI / 2;
      f.position.z = 0.25;
      holder.add(f);
      row.push({ mat, glow: 0, c });
    }
    strips.push({ row, alongX, pitch, span });

    // aluminium tray
    const fx = SIZE_X + RAIL * 2, fz = SIZE_Z + RAIL * 2;
    for (const sz of [-1, 1]) { const r = box(fx, RH, RAIL, alu); r.position.set(0, 0.02, sz * (SIZE_Z / 2 + RAIL / 2)); plane.add(r); }
    for (const sx of [-1, 1]) { const r = box(RAIL, RH, SIZE_Z, alu); r.position.set(sx * (SIZE_X / 2 + RAIL / 2), 0.02, 0); plane.add(r); }
    const base = box(fx, 0.03, fz, aluDark); base.position.y = -T / 2 - 0.03; plane.add(base);

    // SiPM readout box on the fibre end
    const ro = new THREE.Group();
    const housing = box(span * 0.92, 0.34, 0.44, anod); ro.add(housing);
    const board = box(span * 0.86, 0.03, 0.3, pcb); board.position.y = 0.185; ro.add(board);
    for (let k = 0; k < 8; k++) {
      const cyl = cast(new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.12, 12), copper));
      cyl.rotation.x = Math.PI / 2; cyl.position.set(-span * 0.4 + k * (span * 0.8 / 7), 0, 0.27); ro.add(cyl);
    }
    for (let k = 0; k < 3; k++) {
      const led = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.03, 0.06), ledMat);
      led.position.set(span * 0.36 - k * 0.14, 0.21, -0.08); ro.add(led);
    }
    if (alongX) { ro.rotation.y = Math.PI / 2; ro.position.set(SIZE_X / 2 + RAIL + 0.48, 0, 0); }
    else ro.position.set(0, 0, SIZE_Z / 2 + RAIL + 0.48);
    plane.add(ro);
    det.add(plane);
  }

  // corner posts + base
  const postH = PLANE_GAP * (PLANES - 1) + 1.4;
  const baseY = planeY[0] - 0.75;
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    const post = box(0.24, postH, 0.24, alu);
    post.position.set(sx * (SIZE_X / 2 + RAIL + 0.12), baseY + postH / 2, sz * (SIZE_Z / 2 + RAIL + 0.12));
    det.add(post);
    const slot = box(0.05, postH, 0.26, aluDark); slot.position.copy(post.position); det.add(slot);
    const cap = box(0.34, 0.06, 0.34, aluDark); cap.position.set(post.position.x, baseY + postH, post.position.z); det.add(cap);
  }
  const plinth = box(SIZE_X + 1.8, 0.3, SIZE_Z + 1.8, steel);
  plinth.position.y = baseY - 0.15;
  det.add(plinth);

  // cables
  for (let p = 0; p < PLANES; p++) {
    const alongX = p % 2 === 1;
    const start = alongX ? new THREE.Vector3(SIZE_X / 2 + RAIL + 0.75, planeY[p], SIZE_Z * 0.3)
                         : new THREE.Vector3(SIZE_X * 0.3, planeY[p], SIZE_Z / 2 + RAIL + 0.75);
    const end = alongX ? new THREE.Vector3(SIZE_X / 2 + 1.6 + p * 0.12, baseY - 0.3, SIZE_Z * 0.2 + p * 0.1)
                       : new THREE.Vector3(SIZE_X * 0.2 + p * 0.1, baseY - 0.3, SIZE_Z / 2 + 1.6 + p * 0.12);
    const mid = start.clone().lerp(end, 0.5); mid.y -= 0.2;
    mid.add(alongX ? new THREE.Vector3(0.5, 0, 0) : new THREE.Vector3(0, 0, 0.5));
    det.add(cast(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([start, mid, end]), 24, 0.035, 8), cableMat)));
  }

  // floor + grid
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(120, 120),
    new THREE.MeshStandardMaterial({ color: 0x05080e, metalness: 0.1, roughness: 0.85 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = baseY - 0.3;
  floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.GridHelper(80, 80, 0x1c3a66, 0x0e1c33);
  grid.position.y = baseY - 0.295;
  grid.material.transparent = true;
  grid.material.opacity = 0.4;
  scene.add(grid);

  // dust
  const dustN = small() ? 250 : 600;
  const dustPos = new Float32Array(dustN * 3);
  for (let i = 0; i < dustN; i++) {
    dustPos[i * 3] = (Math.random() - 0.5) * 30;
    dustPos[i * 3 + 1] = (Math.random() - 0.5) * 14;
    dustPos[i * 3 + 2] = (Math.random() - 0.5) * 30;
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0x6fa8ff, size: 0.035, transparent: true, opacity: 0.5, depthWrite: false }));
  scene.add(dust);

  // ---------- Muons ----------
  const tex = glowTexture();
  const POOL = 24;
  const muons = [];
  const unitCyl = new THREE.CylinderGeometry(1, 1, 1, 6, 1, true);
  unitCyl.translate(0, 0.5, 0);
  const UP = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < POOL; i++) {
    const trail = new THREE.Mesh(unitCyl, new THREE.MeshBasicMaterial({ color: WHITE, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    const ghost = new THREE.Mesh(unitCyl, new THREE.MeshBasicMaterial({ color: BLUE, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    const head = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: 0xd8f4ff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    head.scale.setScalar(0.45);
    trail.visible = ghost.visible = head.visible = false;
    scene.add(trail, ghost, head);
    muons.push({ active: false, trail, ghost, head, start: new THREE.Vector3(), dir: new THREE.Vector3(), s: 0, len: 0, life: 0, crossed: 0 });
  }
  const hitSprites = [];
  for (let i = 0; i < 60; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: 0x7fe0ff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    sp.visible = false;
    scene.add(sp);
    hitSprites.push({ sp, life: 0 });
  }
  let hitIdx = 0;

  const SPEED = 11;
  const TRAIL = 2.4;
  let evt = 18000 + Math.floor(Math.random() * 800);
  let recent = [];

  function placeCyl(mesh, a, b, r) {
    const d = new THREE.Vector3().subVectors(b, a);
    const L = d.length();
    if (L < 1e-4) { mesh.visible = false; return; }
    mesh.position.copy(a);
    mesh.quaternion.setFromUnitVectors(UP, d.divideScalar(L));
    mesh.scale.set(r, L, r);
  }

  function spawn(base) {
    const m = muons.find(x => !x.active);
    if (!m) return;
    let dir, through;
    if (base) {
      dir = base.dir.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.04, 0, (Math.random() - 0.5) * 0.04)).normalize();
      through = base.through.clone().add(new THREE.Vector3((Math.random() - 0.5) * 2.2, 0, (Math.random() - 0.5) * 1.6));
    } else {
      const cosT = Math.pow(Math.random(), 1 / 3);
      const sinT = Math.sqrt(1 - cosT * cosT);
      const phi = Math.random() * Math.PI * 2;
      dir = new THREE.Vector3(sinT * Math.cos(phi), -cosT, sinT * Math.sin(phi));
      through = new THREE.Vector3((Math.random() - 0.5) * SIZE_X * 1.15, 0, (Math.random() - 0.5) * SIZE_Z * 1.15);
    }
    const back = 9 / Math.max(0.25, -dir.y);
    m.start.copy(through).addScaledVector(dir, -back);
    m.dir.copy(dir);
    m.s = 0; m.len = back * 2; m.life = 0; m.crossed = 0;
    m.theta = Math.acos(-dir.y) * 180 / Math.PI;
    m.active = true;
    m.trail.visible = m.ghost.visible = m.head.visible = true;
    m.trail.material.opacity = 0.9;
    m.ghost.material.opacity = 0;
    m.head.material.opacity = 1;
    return { dir, through };
  }

  // a muon crossing interleaved triangles passes through two neighbouring bars;
  // light both, weighted by path length (the light-sharing trick that gives sub-bar resolution)
  function hit(p, x, z, m) {
    const S = strips[p];
    const coord = S.alongX ? z : x;
    const u = (coord + S.span / 2) / S.pitch - 1;   // continuous bar index
    const i = Math.floor(u), f = u - i;
    let any = false;
    if (i >= 0 && i < BARS) { S.row[i].glow = Math.max(S.row[i].glow, 1 - f * 0.6); any = true; }
    if (i + 1 >= 0 && i + 1 < BARS) { S.row[i + 1].glow = Math.max(S.row[i + 1].glow, 0.4 + f * 0.6); any = true; }
    if (!any) return;
    const h = hitSprites[hitIdx++ % hitSprites.length];
    h.sp.position.set(x, planeY[p] + 0.08, z);
    h.sp.visible = true;
    h.life = 1;
    m.crossed++;
  }

  function step(m, dt) {
    const prev = m.start.clone().addScaledVector(m.dir, m.s);
    m.s += SPEED * dt;
    const pos = m.start.clone().addScaledVector(m.dir, m.s);
    for (let p = 0; p < PLANES; p++) {
      const y = planeY[p];
      if (prev.y > y && pos.y <= y) {
        const t = (prev.y - y) / (prev.y - pos.y);
        const x = prev.x + (pos.x - prev.x) * t;
        const z = prev.z + (pos.z - prev.z) * t;
        if (Math.abs(x) <= SIZE_X / 2 && Math.abs(z) <= SIZE_Z / 2) hit(p, x, z, m);
      }
    }
    const tail = m.start.clone().addScaledVector(m.dir, Math.max(0, m.s - TRAIL));
    placeCyl(m.trail, tail, pos, 0.014);
    m.head.position.copy(pos);
    placeCyl(m.ghost, m.start, pos, 0.006);
    m.ghost.material.opacity = Math.min(0.5, m.ghost.material.opacity + dt * 0.6);
    if (m.s > m.len) {
      m.head.material.opacity = 0;
      m.trail.material.opacity = 0;
      m.life += dt;
      m.ghost.material.opacity = Math.max(0, 0.5 - m.life * 0.35);
      if (m.life === dt) {
        evt++;
        recent.push(performance.now());
        onEvent({ evt, hits: m.crossed, planes: PLANES, theta: m.theta, rate: recent.length / 10 });
      }
      if (m.ghost.material.opacity <= 0) {
        m.active = false;
        m.trail.visible = m.ghost.visible = m.head.visible = false;
      }
    }
  }

  // ---------- Post-processing ----------
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.55, 0.35, 0.85);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  // ---------- Camera & interaction ----------
  const target = new THREE.Vector3(0, -0.2, 0);
  const mobileTarget = new THREE.Vector3(0, -5.2, 0);
  let az = 0.75, mouseX = 0, mouseY = 0, mx = 0, my = 0, scrollP = 0;
  window.addEventListener('pointermove', e => {
    mouseX = (e.clientX / window.innerWidth) * 2 - 1;
    mouseY = (e.clientY / window.innerHeight) * 2 - 1;
  }, { passive: true });
  window.addEventListener('scroll', () => { scrollP = Math.min(1.5, window.scrollY / window.innerHeight); }, { passive: true });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    bloom.setSize(w, h);
    camera.aspect = w / h;
    if (w >= 860) camera.setViewOffset(w, h, -w * 0.25, 0, w, h);
    else camera.clearViewOffset();
    camera.fov = w < 860 ? 42 : 34;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  function placeCamera() {
    mx += (mouseX - mx) * 0.04;
    my += (mouseY - my) * 0.04;
    const portrait = canvas.clientHeight > canvas.clientWidth * 1.1;
    const r = (portrait ? 36 : small() ? 26 : 27) + scrollP * 5;
    const el = 0.42 + my * 0.06 + scrollP * 0.25;
    const a = az + mx * 0.18;
    camera.position.set(Math.cos(a) * Math.cos(el) * r, Math.sin(el) * r, Math.sin(a) * Math.cos(el) * r);
    camera.lookAt(portrait ? mobileTarget : target);
  }

  // ---------- Loop ----------
  let running = true, last = performance.now(), spawnT = 0;
  const io = new IntersectionObserver(([e]) => {
    running = e.isIntersecting;
    if (running) { last = performance.now(); requestAnimationFrame(loop); }
  });
  io.observe(canvas);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && running) { last = performance.now(); requestAnimationFrame(loop); }
  });

  function update(dt) {
    az += dt * 0.05;
    spawnT -= dt;
    if (spawnT <= 0) {
      const b = spawn();
      if (b && Math.random() < 0.14) { spawn(b); spawn(b); if (Math.random() < 0.5) spawn(b); }
      spawnT = 0.25 + Math.random() * 0.55;
    }
    for (const m of muons) if (m.active) step(m, dt);
    for (const S of strips) for (const s of S.row) {
      if (s.glow > 0) s.glow = Math.max(0, s.glow - dt * 1.1);
      s.mat.emissiveIntensity = s.glow * s.glow * 2.2;
    }
    for (const h of hitSprites) if (h.life > 0) {
      h.life = Math.max(0, h.life - dt * 1.6);
      h.sp.material.opacity = h.life;
      h.sp.scale.setScalar(0.25 + (1 - h.life) * 0.5);
      if (!h.life) h.sp.visible = false;
    }
    dust.rotation.y += dt * 0.008;
    const now = performance.now();
    recent = recent.filter(t => now - t < 10000);
  }

  function loop(now) {
    if (!running || document.hidden) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    update(dt);
    placeCamera();
    composer.render();
    requestAnimationFrame(loop);
  }

  if (reduced) {
    for (let i = 0; i < 4; i++) spawn();
    for (let k = 0; k < 60; k++) for (const m of muons) if (m.active && m.s < m.len * 0.62) step(m, 1 / 60);
    for (const S of strips) for (const s of S.row) s.mat.emissiveIntensity = s.glow * s.glow * 2.2;
    placeCamera();
    composer.render();
    window.addEventListener('resize', () => { resize(); composer.render(); });
    return { reduced: true };
  }

  requestAnimationFrame(loop);
  return { rate: () => recent.length / 10 };
}

// auto-start on the page's hero canvas and drive the HUD
const cv = document.getElementById('scene');
if (cv) {
  const $ = id => document.getElementById(id);
  const api = initHero(cv, {
    onEvent: e => {
      if ($('hud-evt')) $('hud-evt').textContent = String(e.evt).padStart(6, '0');
      if ($('hud-hits')) $('hud-hits').textContent = e.hits + '/' + e.planes;
      if ($('hud-theta')) $('hud-theta').textContent = e.theta.toFixed(1) + '°';
      if ($('hud-rate')) $('hud-rate').textContent = e.rate.toFixed(1) + ' Hz';
    },
  });
  if (api) cv.classList.add('on');
}
