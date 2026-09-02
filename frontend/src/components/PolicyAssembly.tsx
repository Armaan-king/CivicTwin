import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { GraphEdge, Persona, PersonaOutcome } from "@/types/simulation";

/**
 * The population, as an assembly.
 *
 * Two earlier attempts were wrong in opposite directions. Plotting residents at their home
 * coordinates made a map, and a map is about a place. Replacing them with an abstract
 * lattice made a diagram, and a diagram is about nothing in particular.
 *
 * This is the thing the product is actually about: people. Two thousand figures in
 * concentric arcs facing a centre, the way a public hearing seats a town. The arrangement
 * is civic rather than geographic, so it says *population* without claiming to say *where*.
 *
 * Fill is severity, per `scenario-v1.md` 13.2. Most of a town is bone-coloured and
 * unaffected, which is true and is the point: harm is a scattered minority, and a picture
 * that made everyone suffer would be a lie told in the first five seconds.
 *
 * The single vermilion thread is the finding. It runs between two figures rows apart --
 * one whose stop closed, one who never went near it -- and it appears only after the
 * policy has swept the room. Everything else is context for that thread.
 */

export interface PolicyAssemblyProps {
  personas: Persona[];
  outcomes: Map<string, PersonaOutcome>;
  edges: GraphEdge[];
  height?: number;
  /** Figures drawn. Solved rather than guessed: at 1,400 the assembly was 921 units wide
   *  in a 725-unit frame, so the ends of every row were cropped off the sides. */
  sample?: number;
}

//: The unaffected majority. Warm grey rather than near-black: at #4a443b on this ground
//: they read as shadows, and a crowd that reads as shadows is not a crowd.
const QUIET = new THREE.Color("#7b7367");
const WARM = new THREE.Color("#f2b024");
const HOT = new THREE.Color("#ef4e36");

/** One person: a head and a tapered body. Small, but unmistakably a figure. */
function figureGeometry(): THREE.BufferGeometry {
  const head = new THREE.SphereGeometry(1.8, 8, 6);
  head.translate(0, 7.2, 0);
  // shoulders wider than feet, so the silhouette reads as a person at fifteen pixels tall
  const body = new THREE.CylinderGeometry(1.2, 2.4, 9.6, 7);
  body.translate(0, 0.8, 0);

  const merged = new THREE.BufferGeometry();
  const parts = [head, body];
  const counts = parts.reduce((n, g) => n + g.attributes.position.count, 0);
  const pos = new Float32Array(counts * 3);
  const idx: number[] = [];
  let vOffset = 0;
  let pOffset = 0;
  for (const g of parts) {
    const p = g.attributes.position.array as ArrayLike<number>;
    for (let i = 0; i < p.length; i++) pos[pOffset + i] = p[i];
    const gi = g.index;
    if (gi) for (let i = 0; i < gi.count; i++) idx.push(gi.array[i] + vOffset);
    vOffset += g.attributes.position.count;
    pOffset += p.length;
    g.dispose();
  }
  merged.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  merged.setIndex(idx);
  merged.computeVertexNormals();
  return merged;
}

export function PolicyAssembly({
  personas, outcomes, edges, height = 720, sample = 620,
}: PolicyAssemblyProps) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el || !personas.length) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, el.clientWidth / height, 1, 4000);
    camera.position.set(0, 118, 580);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, height);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ---------------------------------------------------------------- who is seated
    // Second-order residents are kept whatever the sample size: they are the finding, and
    // sampling the evidence away is how a visual quietly stops being about anything.
    const second = personas.filter((p) => outcomes.get(p.persona_id)?.second_order);
    const keep = new Set(second.map((p) => p.persona_id));
    for (const e of edges) {
      if (e.kind === "CARES_FOR" && keep.has(e.source)) keep.add(e.target);
    }
    const pinned = personas.filter((p) => keep.has(p.persona_id));
    const rest = personas.filter((p) => !keep.has(p.persona_id));
    const stride = Math.max(1, Math.ceil(rest.length / Math.max(1, sample - pinned.length)));
    const seated = [...pinned, ...rest.filter((_, i) => i % stride === 0)];

    // ---------------------------------------------------------------- the seating plan
    // Concentric arcs facing a centre. Rows grow as they go back, the way seating does,
    // so density stays even instead of crowding at the front.
    const seat = new Map<string, THREE.Vector3>();
    // Solved against the frame rather than picked: 20 rows over 1.9 radians puts the
    // assembly 644 units wide inside a 751-unit view, with figures ~15px tall at this
    // height. Wider and the rows run off the sides; tighter and they stop being people.
    const ROWS = 20;
    const SPREAD = 1.9;
    let placed = 0;
    for (let row = 0; row < ROWS && placed < seated.length; row++) {
      const radius = 96 + row * 15;
      const capacity = Math.max(8, Math.round(radius * SPREAD / 15));
      for (let s = 0; s < capacity && placed < seated.length; s++, placed++) {
        const t = capacity === 1 ? 0.5 : s / (capacity - 1);
        const a = -SPREAD / 2 + t * SPREAD;
        // a little jitter, because a perfect grid of people reads as a cemetery
        const jitter = ((placed * 2654435761) % 1000) / 1000 - 0.5;
        seat.set(seated[placed].persona_id, new THREE.Vector3(
          Math.sin(a) * radius + jitter * 5,
          row * 2.2,                       // rows rise slightly, like a rake
          -Math.cos(a) * radius + jitter * 5
        ));
      }
    }
    const shown = seated.filter((p) => seat.has(p.persona_id));

    // ---------------------------------------------------------------- the figures
    const geo = figureGeometry();
    // Instance colour through an attribute we own. MeshBasicMaterial with
    // vertexColors: true reads the geometry's `color` attribute, which this geometry does
    // not have, so every figure rendered black. Owning the shader removes the question.
    const instanceColour = new THREE.InstancedBufferAttribute(
      new Float32Array(shown.length * 3), 3
    );
    geo.setAttribute("aColor", instanceColour);

    const mat = new THREE.ShaderMaterial({
      transparent: true,
      uniforms: { uFade: { value: 1 } },
      vertexShader: `
        attribute vec3 aColor;
        varying vec3 vColor;
        varying float vUp;
        void main() {
          vColor = aColor;
          vUp = position.y;
          vec4 mv = modelViewMatrix * instanceMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying vec3 vColor;
        varying float vUp;
        uniform float uFade;
        void main() {
          // a touch brighter at the head, so a figure has some form without lighting
          float lift = 0.82 + smoothstep(-4.0, 7.0, vUp) * 0.34;
          gl_FragColor = vec4(vColor * lift, uFade);
        }`,
    });
    const mesh = new THREE.InstancedMesh(geo, mat, shown.length);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

    const dummy = new THREE.Object3D();
    const colour = new THREE.Color();
    const arrival = new Float32Array(shown.length);   // when the policy reaches this seat
    const severity: string[] = [];

    shown.forEach((p, i) => {
      const at = seat.get(p.persona_id)!;
      dummy.position.copy(at);
      dummy.rotation.set(0, Math.atan2(-at.x, at.z) + Math.PI, 0);   // all facing the front
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      const o = outcomes.get(p.persona_id);
      const sev = o?.second_order ? "second" : (o?.severity ?? "none");
      severity.push(sev);
      colour.copy(sev === "second" || sev === "high" ? HOT : sev === "moderate" ? WARM : QUIET);
      instanceColour.setXYZ(i, colour.r, colour.g, colour.b);

      // the change sweeps the room from the left, so the wave has a direction to read
      arrival[i] = (at.x + 420) / 840;
    });
    instanceColour.needsUpdate = true;
    world.add(mesh);

    // ---------------------------------------------------------------- the thread
    // one dependency, drawn between two seats. Not all of them: a dozen threads is a
    // cat's cradle, and the claim is about a person, not a volume.
    const threadPts: number[] = [];
    const pairs = edges
      .filter((e) => e.kind === "CARES_FOR" && seat.has(e.source) && seat.has(e.target))
      .filter((e) => outcomes.get(e.source)?.second_order)
      .slice(0, 3);
    for (const e of pairs) {
      const a = seat.get(e.source)!;
      const b = seat.get(e.target)!;
      const steps = 26;
      for (let s = 0; s < steps; s++) {
        const p0 = s / steps;
        const p1 = (s + 1) / steps;
        // Head height, barely arced. At 54 units over an 8-unit figure these read as
        // projectiles flying across the room rather than as a line between two people.
        const lift = (x: number) => 7 + Math.sin(x * Math.PI) * 7;
        threadPts.push(
          a.x + (b.x - a.x) * p0, a.y + (b.y - a.y) * p0 + lift(p0), a.z + (b.z - a.z) * p0,
          a.x + (b.x - a.x) * p1, a.y + (b.y - a.y) * p1 + lift(p1), a.z + (b.z - a.z) * p1
        );
      }
    }
    const threadGeo = new THREE.BufferGeometry();
    threadGeo.setAttribute("position", new THREE.Float32BufferAttribute(threadPts, 3));
    const threadMat = new THREE.LineBasicMaterial({ color: 0xef4e36, transparent: true,
                                                    opacity: 0 });
    world.add(new THREE.LineSegments(threadGeo, threadMat));

    // No floor. A ring under the seats was a wedge of flat colour competing with the
    // figures for attention, and the figures are the subject.

    // ---------------------------------------------------------------- interaction
    let dragging = false;
    let lastX = 0;
    let spin = 0;
    let target = 0;
    const down = (e: PointerEvent) => { dragging = true; lastX = e.clientX; };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      target += (e.clientX - lastX) * 0.004;
      lastX = e.clientX;
    };
    const up = () => { dragging = false; };
    el.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);

    // ---------------------------------------------------------------- the one moment
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = (now - start) / 1000;
      const cycle = reduced ? 9 : t % 11;
      const wave = cycle / 6.5;                       // sweeps the room over ~6.5s

      // a figure straightens as the news reaches it, then the harmed ones stoop
      for (let i = 0; i < shown.length; i++) {
        const d = wave - arrival[i];
        const hit = d > 0 && d < 0.5 ? Math.sin(d * Math.PI * 2) : 0;
        const harmed = severity[i] !== "none" && d > 0;
        const at = seat.get(shown[i].persona_id)!;
        dummy.position.set(at.x, at.y + hit * 3.4, at.z);
        dummy.rotation.set(harmed ? Math.min(0.34, d * 0.5) : 0,
                           Math.atan2(-at.x, at.z) + Math.PI, 0);
        dummy.scale.setScalar(1 + hit * 0.22);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;

      // the thread arrives after the room has already reacted. the order is the argument.
      threadMat.opacity = reduced ? 0.8
        : cycle > 6.2 && cycle < 10.4 ? Math.min(0.8, (cycle - 6.2) * 0.7) : 0;

      if (!reduced) target += 0.0005;
      spin += (target - spin) * 0.06;
      world.rotation.y = spin;

      camera.lookAt(0, 26, -70);
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
      threadGeo.dispose();
      mat.dispose();
      threadMat.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [personas, outcomes, edges, height, sample]);

  return <div ref={mount} style={{ width: "100%", height, cursor: "grab" }} />;
}
