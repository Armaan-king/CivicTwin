import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { GraphEdge, Persona, PersonaOutcome } from "@/types/simulation";

/**
 * The population as a connected graph, with the policy propagating through it.
 *
 * This is the product's own one-line definition made visible: a graph-connected
 * synthetic population, a change entering at one point, and consequences spreading
 * along dependencies. Points and lines are self-luminous, so unlike extruded geometry
 * they stay legible on a dark ground without fighting the lighting.
 *
 * Drag to turn it. It drifts on its own when left alone, and holds still under
 * prefers-reduced-motion.
 */

export interface PolicyNetworkProps {
  personas: Persona[];
  outcomes: Map<string, PersonaOutcome>;
  edges: GraphEdge[];
  height?: number;
  /** how many of the population to plot; the rest would be noise at this scale */
  sample?: number;
}

const QUIET = new THREE.Color("#5a5349");
const WARM = new THREE.Color("#f2b024");
const HOT = new THREE.Color("#ef4e36");

export function PolicyNetwork({
  personas, outcomes, edges, height = 720, sample = 900,
}: PolicyNetworkProps) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el || !personas.length) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(46, el.clientWidth / height, 1, 5000);
    camera.position.set(0, 60, 640);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, height);
    el.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ---- lay the population out as a slab, so it reads as a place, not a ball
    const stride = Math.max(1, Math.floor(personas.length / sample));
    const plotted: Persona[] = [];
    const taken = new Set<string>();
    for (let i = 0; i < personas.length; i += stride) {
      plotted.push(personas[i]);
      taken.add(personas[i].persona_id);
    }
    // both ends of every dependency that fired must be on screen, whatever the stride.
    // those ties are the finding; sampling one end away would quietly delete it.
    const mustKeep = new Set<string>();
    for (const e of edges) {
      if (e.kind === "CARES_FOR" && outcomes.get(e.source)?.second_order) {
        mustKeep.add(e.source);
        mustKeep.add(e.target);
      }
    }
    for (const p of personas) {
      if (mustKeep.has(p.persona_id) && !taken.has(p.persona_id)) {
        plotted.push(p);
        taken.add(p.persona_id);
      }
    }

    const pos = new Float32Array(plotted.length * 3);
    const col = new Float32Array(plotted.length * 3);
    const size = new Float32Array(plotted.length);
    const dist = new Float32Array(plotted.length);
    const index = new Map<string, number>();

    // Normalise the home coordinates against their own bounds before using them.
    // The scatter terms below multiply (xy - 0.5), which only means anything if xy runs
    // 0 to 1. It never has: these are plan coordinates, and once the study area became
    // real they are metres, so 3,474 became 243,000 units of scatter in a scene whose
    // disc is 420 across. Deriving the bounds keeps this correct whatever the units are
    // -- display units, metres, or whatever a future study area brings.
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const p of plotted) {
      minX = Math.min(minX, p.xy[0]); maxX = Math.max(maxX, p.xy[0]);
      minY = Math.min(minY, p.xy[1]); maxY = Math.max(maxY, p.xy[1]);
    }
    const spanX = Math.max(1, maxX - minX);
    const spanY = Math.max(1, maxY - minY);
    const unit = (v: number, lo: number, span: number) => (v - lo) / span;

    // the policy enters here: the removed stop, at one end of the corridor
    const origin = new THREE.Vector3(-210, 0, -60);
    const c = new THREE.Color();

    plotted.forEach((p, i) => {
      index.set(p.persona_id, i);
      // a wide shallow disc with a little vertical scatter reads as a population
      const a = (i / plotted.length) * Math.PI * 2 * 11.6;
      const r = 40 + Math.sqrt(i / plotted.length) * 380;
      const nx = unit(p.xy[0], minX, spanX);
      const ny = unit(p.xy[1], minY, spanY);
      const x = Math.cos(a) * r + (nx - 0.5) * 70;
      const z = Math.sin(a) * r * 0.62 + (ny - 0.5) * 70;
      const y = (ny - 0.5) * 54;

      pos.set([x, y, z], i * 3);
      dist[i] = new THREE.Vector3(x, y, z).distanceTo(origin);

      const sev = outcomes.get(p.persona_id)?.severity ?? "none";
      c.copy(sev === "high" ? HOT : sev === "moderate" ? WARM : QUIET);
      col.set([c.r, c.g, c.b], i * 3);
      size[i] = sev === "high" ? 9 : sev === "moderate" ? 6 : 3.4;
    });

    const maxDist = Math.max(...dist);

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    geo.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
    geo.setAttribute("aDist", new THREE.BufferAttribute(dist, 1));

    // a round, additive point so the field glows instead of looking like confetti
    const mat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: { uWave: { value: 0 } },
      vertexShader: `
        attribute float aSize;
        attribute float aDist;
        varying vec3 vColor;
        varying float vLit;
        uniform float uWave;
        void main() {
          vColor = color;
          vLit = smoothstep(uWave + 90.0, uWave - 40.0, aDist);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * (300.0 / -mv.z) * (0.55 + vLit * 0.75);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vLit;
        void main() {
          float d = length(gl_PointCoord - vec2(0.5));
          if (d > 0.5) discard;
          float edge = smoothstep(0.5, 0.06, d);
          gl_FragColor = vec4(vColor * (0.35 + vLit * 1.5), edge * (0.5 + vLit * 0.5));
        }`,
      vertexColors: true,
    });

    const points = new THREE.Points(geo, mat);
    world.add(points);

    // ---- dependencies that actually fired, drawn between the two people
    const fired = edges.filter(
      (e) => e.kind === "CARES_FOR" && outcomes.get(e.source)?.second_order
    );
    const linePts: number[] = [];
    for (const e of fired) {
      const a = index.get(e.source);
      const b = index.get(e.target);
      if (a === undefined || b === undefined) continue;
      linePts.push(pos[a * 3], pos[a * 3 + 1], pos[a * 3 + 2]);
      linePts.push(pos[b * 3], pos[b * 3 + 1], pos[b * 3 + 2]);
    }
    if (linePts.length) {
      const lg = new THREE.BufferGeometry();
      lg.setAttribute("position", new THREE.Float32BufferAttribute(linePts, 3));
      world.add(new THREE.LineSegments(
        lg,
        new THREE.LineBasicMaterial({
          color: HOT, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending,
        })
      ));
    }

    // ---- the point of entry: a marker and an expanding ring
    const marker = new THREE.Mesh(
      new THREE.RingGeometry(9, 11, 32),
      new THREE.MeshBasicMaterial({ color: HOT, side: THREE.DoubleSide, transparent: true, opacity: 0.9 })
    );
    marker.position.copy(origin);
    marker.rotation.x = -Math.PI / 2;
    world.add(marker);

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(1, 3, 64),
      new THREE.MeshBasicMaterial({
        color: HOT, side: THREE.DoubleSide, transparent: true,
        opacity: 0.4, blending: THREE.AdditiveBlending,
      })
    );
    ring.position.copy(origin);
    ring.rotation.x = -Math.PI / 2;
    world.add(ring);

    // ---- drag to turn
    let dragging = false;
    let lastX = 0;
    let spin = 0.55;
    let velocity = 0;

    const down = (e: PointerEvent) => {
      dragging = true; lastX = e.clientX;
      renderer.domElement.setPointerCapture(e.pointerId);
    };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      velocity = (e.clientX - lastX) * 0.005;
      spin += velocity;
      lastX = e.clientX;
    };
    const up = () => { dragging = false; };
    renderer.domElement.addEventListener("pointerdown", down);
    renderer.domElement.addEventListener("pointermove", move);
    renderer.domElement.addEventListener("pointerup", up);
    renderer.domElement.addEventListener("pointerleave", up);
    renderer.domElement.style.cursor = "grab";
    renderer.domElement.style.touchAction = "pan-y";

    let raf = 0;
    let wave = reduced ? maxDist * 2 : -120;
    const t0 = performance.now();

    const frame = () => {
      const t = (performance.now() - t0) / 1000;

      if (!reduced) {
        // one pass of the consequence spreading outward, then it rests
        if (wave < maxDist * 1.25) wave += maxDist / 150;
        mat.uniforms.uWave.value = wave;

        const phase = (t % 5) / 5;
        ring.scale.setScalar(1 + phase * (maxDist / 3));
        (ring.material as THREE.MeshBasicMaterial).opacity = 0.34 * (1 - phase);

        if (!dragging) {
          velocity *= 0.94;
          spin += velocity + 0.0011;
        }
      } else {
        mat.uniforms.uWave.value = maxDist * 2;
        ring.visible = false;
      }

      world.rotation.y = spin;
      world.rotation.x = -0.42;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(frame);
    };
    frame();

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
      renderer.domElement.removeEventListener("pointerdown", down);
      renderer.domElement.removeEventListener("pointermove", move);
      renderer.domElement.removeEventListener("pointerup", up);
      renderer.domElement.removeEventListener("pointerleave", up);
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh || o instanceof THREE.Points || o instanceof THREE.LineSegments) {
          o.geometry?.dispose?.();
          const m = o.material;
          if (Array.isArray(m)) m.forEach((x) => x.dispose());
          else m?.dispose?.();
        }
      });
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [personas, outcomes, edges, height, sample]);

  return (
    <div
      ref={mount}
      style={{ width: "100%", height }}
      role="img"
      aria-label="The synthetic population as a connected graph. A policy change enters at one point and spreads outward; residents who lose an essential trip light red, and lines join carers to the people they look after."
    />
  );
}
