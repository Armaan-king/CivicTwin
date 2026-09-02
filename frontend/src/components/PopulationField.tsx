import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Persona, PersonaOutcome } from "@/types/simulation";

/**
 * Two thousand people, seen straight on.
 *
 * Three earlier attempts failed for the same underlying reason: each added something on
 * top of the population -- a map, a lattice, arcs and threads flying between figures --
 * and the addition became the subject. The population is the subject.
 *
 * So this is a field. Every resident in the run, one figure each, ranked and gridded, lit
 * flat and seen through an orthographic camera so there is no perspective to distort who
 * is near and who is far. No connectors, no arcs, no depth tricks.
 *
 * The image is the ratio. Nearly two thousand people stand in bone; twenty-one stand in
 * vermilion. That is the whole product in one glance, and it is honest in a way a
 * heat-map is not: you can count them.
 *
 * The only motion is a slow pass of light, left to right, the way a policy actually
 * arrives -- somewhere first, everywhere eventually.
 */

export interface PopulationFieldProps {
  personas: Persona[];
  outcomes: Map<string, PersonaOutcome>;
  height?: number;
}

const QUIET = new THREE.Color("#6f685c");
const WARM = new THREE.Color("#f2b024");
const HOT = new THREE.Color("#ef4e36");

/** A person: head, shoulders, a slight taper. Legible at fifteen pixels. */
function figureGeometry(): THREE.BufferGeometry {
  const parts = [
    (() => { const g = new THREE.SphereGeometry(0.26, 8, 6); g.translate(0, 0.86, 0); return g; })(),
    (() => { const g = new THREE.CylinderGeometry(0.2, 0.34, 1.28, 7); g.translate(0, 0.06, 0); return g; })(),
  ];
  const total = parts.reduce((n, g) => n + g.attributes.position.count, 0);
  const pos = new Float32Array(total * 3);
  const idx: number[] = [];
  let v = 0;
  let o = 0;
  for (const g of parts) {
    const a = g.attributes.position.array as ArrayLike<number>;
    for (let i = 0; i < a.length; i++) pos[o + i] = a[i];
    const gi = g.index;
    if (gi) for (let i = 0; i < gi.count; i++) idx.push(gi.array[i] + v);
    v += g.attributes.position.count;
    o += a.length;
    g.dispose();
  }
  const merged = new THREE.BufferGeometry();
  merged.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  merged.setIndex(idx);
  return merged;
}

export function PopulationField({ personas, outcomes, height = 720 }: PopulationFieldProps) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el || !personas.length) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const width = el.clientWidth || 1200;
    const scene = new THREE.Scene();

    // Orthographic, deliberately. A perspective camera makes the back rows smaller, which
    // says the people further away matter less. Here every person is the same size,
    // because that is the claim the product is making.
    const camera = new THREE.OrthographicCamera(0, 1, 1, 0, -100, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ---------------------------------------------------------------- the grid
    // Sized to the frame so the field always fills it, whatever the window is doing.
    const n = personas.length;
    const aspect = width / height;
    const ROW_H = 1.45;                    // figures are taller than wide, so rows are too

    // Solve the column count so the grid's own aspect matches the frame's. Dropping the
    // row-height factor gives a grid 1.27 wide for a frame of 1.84, which letterboxes and
    // then stretches the people to fill it.
    const cols = Math.max(12, Math.round(Math.sqrt(n * ROW_H * aspect)));
    const rows = Math.ceil(n / cols);
    const cell = 1;
    const gridW = cols * cell;
    const gridH = rows * cell * ROW_H;

    // The frustum takes its aspect from the renderer, never from the grid, so a figure is
    // never stretched. Any slack from the rounding becomes margin.
    const halfW = Math.max(gridW, gridH * aspect) / 2 + cell;
    camera.left = -halfW;
    camera.right = halfW;
    camera.top = halfW / aspect;
    camera.bottom = -halfW / aspect;
    camera.updateProjectionMatrix();

    const geo = figureGeometry();
    const instanceColour = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
    geo.setAttribute("aColor", instanceColour);

    const material = new THREE.ShaderMaterial({
      transparent: true,
      uniforms: { uSweep: { value: -2 }, uWidth: { value: gridW } },
      vertexShader: `
        attribute vec3 aColor;
        varying vec3 vColor;
        varying float vFlare;
        uniform float uSweep;
        uniform float uWidth;
        void main() {
          vColor = aColor;
          vec4 world = instanceMatrix * vec4(position, 1.0);
          // where this person sits across the field, 0 at the left edge, 1 at the right
          float across = world.x / uWidth + 0.5;
          float d = abs(across - uSweep);
          vFlare = uSweep < -1.0 ? 0.0 : exp(-d * d * 260.0);
          gl_Position = projectionMatrix * modelViewMatrix * world;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vFlare;
        void main() {
          gl_FragColor = vec4(vColor + vFlare * 0.5, 0.92);
        }`,
    });

    const mesh = new THREE.InstancedMesh(geo, material, n);
    const dummy = new THREE.Object3D();
    const c = new THREE.Color();

    // Ranked, so the coloured figures gather rather than scatter into confetti. Severe
    // first: a reader's eye lands on the top-left corner, and that is where the finding is.
    const order = [...personas].sort((a, b) => {
      const rank = (p: Persona) => {
        const o = outcomes.get(p.persona_id);
        if (o?.second_order) return 0;
        if (o?.severity === "high") return 1;
        if (o?.severity === "moderate") return 2;
        return 3;
      };
      return rank(a) - rank(b) || a.persona_id.localeCompare(b.persona_id);
    });

    order.forEach((p, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      // a whisper of jitter, because a perfect grid of people reads as a cemetery
      const j = ((i * 2654435761) % 1000) / 1000 - 0.5;
      dummy.position.set(
        (col - (cols - 1) / 2) * cell + j * 0.16,
        gridH / 2 - row * cell * ROW_H - 0.7,
        0
      );
      dummy.rotation.set(0, 0, j * 0.05);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      const o = outcomes.get(p.persona_id);
      const sev = o?.second_order || o?.severity === "high" ? HOT
        : o?.severity === "moderate" ? WARM : QUIET;
      c.copy(sev);
      instanceColour.setXYZ(i, c.r, c.g, c.b);
    });
    instanceColour.needsUpdate = true;
    mesh.instanceMatrix.needsUpdate = true;
    world.add(mesh);

    // ---------------------------------------------------------------- the one motion
    // A policy arrives somewhere first and everywhere eventually. That is the only thing
    // worth animating here, and it is the only thing that moves.
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      if (reduced) {
        material.uniforms.uSweep.value = -2;
      } else {
        const t = ((now - start) / 1000) % 7.5;
        material.uniforms.uSweep.value = t < 5 ? t / 5 : -2;
      }
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    const onResize = () => {
      const w = el.clientWidth;
      if (!w) return;
      renderer.setSize(w, height);
      const a = w / height;
      const half = Math.max(gridW, gridH * a) / 2 + cell;
      camera.left = -half;
      camera.right = half;
      camera.top = half / a;
      camera.bottom = -half / a;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      geo.dispose();
      material.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [personas, outcomes, height]);

  return <div ref={mount} style={{ width: "100%", height }} />;
}
