import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * A policy entering a structure, and the one consequence nobody drew.
 *
 * The previous hero plotted residents at their home coordinates, which made it a map. A
 * map is about a place; this product is about a mechanism, and the mechanism is the same
 * whether the subject is buses, clinics or benefits.
 *
 * So: a lattice of provisions. A change enters at one node and propagates down through
 * the structure along the connections that exist, which is what a policy does. Most nodes
 * take it and settle. Some fall below the line. And one node **off the path entirely** is
 * pulled under by a single thread from a node that was hit, because somebody depends on
 * them.
 *
 * That last thread is the whole product. Everything else here is context for it.
 *
 * Drag to turn. It drifts when left alone and holds still under prefers-reduced-motion.
 */

export interface PolicyLatticeProps {
  height?: number;
  /** severely harmed, from the run. Scales how much of the lattice falls. */
  harmed?: number | null;
  /** harmed through a dependency. Decides how many sideways threads fire. */
  secondOrder?: number | null;
  population?: number | null;
}

const QUIET = new THREE.Color("#3a342c");
const GOLD = new THREE.Color("#f2b024");
const ALERT = new THREE.Color("#ef4e36");

//: the lattice. Wide and shallow reads as a structure; a cube reads as a toy.
const COLS = 13;
const ROWS = 7;
const LAYERS = 3;
const GAP = 58;

export function PolicyLattice({
  height = 720, harmed = null, secondOrder = null, population = null,
}: PolicyLatticeProps) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, el.clientWidth / height, 1, 4000);
    camera.position.set(0, 120, 760);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, height);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ---------------------------------------------------------------- the lattice
    const nodes: { pos: THREE.Vector3; col: number; row: number; layer: number }[] = [];
    for (let l = 0; l < LAYERS; l++) {
      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          // a slight stagger per layer stops it reading as a printed grid
          const jx = (l % 2) * GAP * 0.5;
          nodes.push({
            pos: new THREE.Vector3(
              (c - (COLS - 1) / 2) * GAP + jx,
              (l - (LAYERS - 1) / 2) * GAP * 1.5,
              (r - (ROWS - 1) / 2) * GAP * 0.9
            ),
            col: c, row: r, layer: l,
          });
        }
      }
    }

    // the change enters at one provision, near the left of the top layer
    const entry = nodes.findIndex((n) => n.col === 2 && n.row === 3 && n.layer === LAYERS - 1);
    const origin = nodes[entry].pos.clone();

    // how far the change has to travel to reach each node, in lattice steps
    const reach = nodes.map((n) => n.pos.distanceTo(origin) / GAP);
    const maxReach = Math.max(...reach);

    // ---------------------------------------------------------------- who falls
    // the run's own numbers decide the shape: a policy that harms few drops few nodes
    const total = population ?? 2000;
    const harmShare = harmed == null ? 0.02 : Math.min(0.3, harmed / total * 12);
    const fallen = new Set<number>();
    nodes.forEach((_n, i) => {
      // harm concentrates near the entry, the way a closure concentrates on a corridor
      const nearness = 1 - reach[i] / maxReach;
      if (nearness > 1 - harmShare * 3 && (i * 7919) % 100 < 62) fallen.add(i);
    });

    // ---------------------------------------------------------------- the threads
    // nodes far from the entry, pulled under by one connection to a node that was hit.
    // This is the second-order case, and it is deliberately the only thing on screen
    // that moves sideways.
    const threads: { from: number; to: number }[] = [];
    const wanted = Math.max(2, Math.min(6, secondOrder ?? 3));
    const hitList = [...fallen];
    for (let k = 0; k < wanted && hitList.length; k++) {
      const from = hitList[(k * 13) % hitList.length];
      const candidates = nodes
        .map((_n, i) => i)
        .filter((i) => !fallen.has(i) && reach[i] > maxReach * 0.55);
      if (!candidates.length) break;
      const to = candidates[(k * 271) % candidates.length];
      threads.push({ from, to });
      fallen.add(to);
    }
    const secondOrderNodes = new Set(threads.map((t) => t.to));

    // ---------------------------------------------------------------- geometry
    const pos = new Float32Array(nodes.length * 3);
    const col = new Float32Array(nodes.length * 3);
    const siz = new Float32Array(nodes.length);
    const c = new THREE.Color();
    nodes.forEach((n, i) => {
      pos.set([n.pos.x, n.pos.y, n.pos.z], i * 3);
      const tone = secondOrderNodes.has(i) ? ALERT : fallen.has(i) ? GOLD : QUIET;
      c.copy(tone);
      col.set([c.r, c.g, c.b], i * 3);
      siz[i] = secondOrderNodes.has(i) ? 13 : fallen.has(i) ? 9 : 5;
    });

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
    geo.setAttribute("aSize", new THREE.BufferAttribute(siz, 1));
    geo.setAttribute("aReach", new THREE.BufferAttribute(new Float32Array(reach), 1));

    const material = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uWave: { value: -1 } },
      vertexShader: `
        attribute vec3 aColor;
        attribute float aSize;
        attribute float aReach;
        uniform float uWave;
        varying vec3 vColor;
        varying float vFlare;
        void main() {
          vColor = aColor;
          // the propagation front: a node brightens as the change reaches it
          float d = abs(aReach - uWave);
          vFlare = uWave < 0.0 ? 0.0 : exp(-d * d * 0.6);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = (aSize + vFlare * 10.0) * (320.0 / -mv.z);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vFlare;
        void main() {
          vec2 d = gl_PointCoord - vec2(0.5);
          float r = length(d);
          if (r > 0.5) discard;
          float edge = smoothstep(0.5, 0.16, r);
          gl_FragColor = vec4(vColor + vFlare * 0.55, edge * (0.5 + vFlare * 0.5));
        }`,
    });
    world.add(new THREE.Points(geo, material));

    // ---------------------------------------------------------------- structure lines
    const linePts: number[] = [];
    nodes.forEach((n, i) => {
      const right = nodes[i + 1];
      if (right && right.row === n.row && right.layer === n.layer && right.col === n.col + 1) {
        linePts.push(n.pos.x, n.pos.y, n.pos.z, right.pos.x, right.pos.y, right.pos.z);
      }
      const back = nodes[i + COLS];
      if (back && back.layer === n.layer && back.col === n.col) {
        linePts.push(n.pos.x, n.pos.y, n.pos.z, back.pos.x, back.pos.y, back.pos.z);
      }
    });
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(linePts, 3));
    world.add(new THREE.LineSegments(lineGeo, new THREE.LineBasicMaterial({
      color: 0x241f19, transparent: true, opacity: 0.85,
    })));

    // ---------------------------------------------------------------- the threads
    const threadPts: number[] = [];
    for (const t of threads) {
      const a = nodes[t.from].pos;
      const b = nodes[t.to].pos;
      // a shallow arc, so it reads as a connection rather than a grid line
      const steps = 18;
      for (let s = 0; s < steps; s++) {
        const p = s / steps;
        const q = (s + 1) / steps;
        const lift = (x: number) => Math.sin(x * Math.PI) * 46;
        threadPts.push(
          a.x + (b.x - a.x) * p, a.y + (b.y - a.y) * p + lift(p), a.z + (b.z - a.z) * p,
          a.x + (b.x - a.x) * q, a.y + (b.y - a.y) * q + lift(q), a.z + (b.z - a.z) * q
        );
      }
    }
    const threadGeo = new THREE.BufferGeometry();
    threadGeo.setAttribute("position", new THREE.Float32BufferAttribute(threadPts, 3));
    const threadMat = new THREE.LineBasicMaterial({
      color: 0xef4e36, transparent: true, opacity: 0,
    });
    world.add(new THREE.LineSegments(threadGeo, threadMat));

    // ---------------------------------------------------------------- interaction
    let dragging = false;
    let lastX = 0;
    let spin = 0;
    let targetSpin = 0;
    const down = (e: PointerEvent) => { dragging = true; lastX = e.clientX; };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      targetSpin += (e.clientX - lastX) * 0.005;
      lastX = e.clientX;
    };
    const up = () => { dragging = false; };
    el.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);

    // ---------------------------------------------------------------- the one moment
    // A single authored beat: the change enters, travels the lattice, and only after it
    // has passed does the sideways thread appear. The order is the argument.
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = (now - start) / 1000;
      const cycle = reduced ? 6 : (t % 9);

      material.uniforms.uWave.value = cycle < 6 ? (cycle / 6) * maxReach * 1.15 : -1;
      threadMat.opacity = reduced ? 0.75
        : cycle > 3.4 && cycle < 8.4 ? Math.min(0.75, (cycle - 3.4) * 0.9) : 0;

      if (!reduced) targetSpin += 0.0007;
      spin += (targetSpin - spin) * 0.06;
      world.rotation.y = spin;
      world.rotation.x = -0.24;

      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    const onResize = () => {
      if (!el.clientWidth) return;
      camera.aspect = el.clientWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(el.clientWidth, height);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      el.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      geo.dispose();
      lineGeo.dispose();
      threadGeo.dispose();
      material.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [height, harmed, secondOrder, population]);

  return <div ref={mount} style={{ width: "100%", height, cursor: "grab" }} />;
}
