import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * The hero visual: a population as a luminous sphere, with a policy breaking across it.
 *
 * Four earlier attempts optimised for defensibility -- a map, a lattice, an assembly, a
 * ranked grid -- and each was more honest than the last and duller than the last. A hero
 * is not a chart. Its job is to make someone want to look, and the charts are three clicks
 * away doing the arguing.
 *
 * So: eight thousand points on a sphere, a shell of filaments over them, and a shockwave
 * that breaks from one point and races around the whole body, leaving a wake of gold and a
 * scatter of vermilion behind it. Additive blending throughout, which is why it glows
 * without a single light in the scene.
 *
 * Drag to spin it.
 */

export interface PolicyOrbProps {
  height?: number;
  /** severe harm from the run; scales how much vermilion survives the wave */
  harmed?: number | null;
  population?: number | null;
}

const RADIUS = 190;
const POINTS = 8000;
const FILAMENTS = 1400;

export function PolicyOrb({ height = 720, harmed = null, population = null }: PolicyOrbProps) {
  const mount = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = mount.current;
    if (!el) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / height, 1, 3000);
    camera.position.set(0, 40, 560);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, height);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ---------------------------------------------------------------- the body
    // Fibonacci sphere: the only cheap way to scatter points evenly on a sphere. A
    // lat/long grid clumps at the poles and the clumping is all you see.
    const pos = new Float32Array(POINTS * 3);
    const seedAttr = new Float32Array(POINTS);
    const hurt = new Float32Array(POINTS);
    const golden = Math.PI * (3 - Math.sqrt(5));
    const dirs: THREE.Vector3[] = [];

    const harmShare = harmed == null || !population
      ? 0.02 : Math.min(0.12, (harmed / population) * 2.4);

    for (let i = 0; i < POINTS; i++) {
      const y = 1 - (i / (POINTS - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const th = golden * i;
      const v = new THREE.Vector3(Math.cos(th) * r, y, Math.sin(th) * r);
      dirs.push(v);
      // a little thickness, so it reads as a body rather than a paper shell
      const jitter = 1 + (((i * 2654435761) % 1000) / 1000 - 0.5) * 0.055;
      pos.set([v.x * RADIUS * jitter, v.y * RADIUS * jitter, v.z * RADIUS * jitter], i * 3);
      seedAttr[i] = ((i * 40503) % 997) / 997;
      hurt[i] = seedAttr[i] < harmShare ? 1 : 0;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seedAttr, 1));
    geo.setAttribute("aHurt", new THREE.BufferAttribute(hurt, 1));

    const pointMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uWave: { value: -1 },
        uOrigin: { value: new THREE.Vector3(0.72, 0.34, 0.6).normalize() },
      },
      vertexShader: `
        attribute float aSeed;
        attribute float aHurt;
        uniform float uTime;
        uniform float uWave;
        uniform vec3 uOrigin;
        varying float vFlare;
        varying float vHurt;
        varying float vDepth;
        void main() {
          // angular distance from where the policy landed, 0 at the origin, 1 opposite
          float ang = acos(clamp(dot(normalize(position), uOrigin), -1.0, 1.0)) / 3.14159;
          float d = ang - uWave;
          // a sharp front with a long trailing wake
          vFlare = uWave < 0.0 ? 0.0
                 : exp(-d * d * 900.0) + (d < 0.0 ? exp(d * 5.5) * 0.55 : 0.0);
          vHurt = aHurt;

          // the wave physically lifts the surface as it passes
          vec3 p = position * (1.0 + vFlare * 0.09);
          // and everything breathes, slowly, so a still frame is never quite still
          p *= 1.0 + sin(uTime * 0.5 + aSeed * 6.28) * 0.006;

          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          vDepth = clamp((mv.z + 320.0) / 420.0, 0.0, 1.0);
          float base = 1.6 + aSeed * 1.5 + aHurt * 2.2;
          gl_PointSize = (base + vFlare * 7.0) * (300.0 / -mv.z);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying float vFlare;
        varying float vHurt;
        varying float vDepth;
        void main() {
          vec2 d = gl_PointCoord - vec2(0.5);
          float r = length(d);
          if (r > 0.5) discard;
          float core = smoothstep(0.5, 0.0, r);

          vec3 bone = vec3(0.52, 0.49, 0.44);
          vec3 gold = vec3(0.95, 0.69, 0.14);
          vec3 hot  = vec3(0.94, 0.31, 0.21);

          // bone at rest, gold where the wave is passing, vermilion where it left a mark
          vec3 col = mix(bone, gold, clamp(vFlare * 1.7, 0.0, 1.0));
          col = mix(col, hot, vHurt * clamp(vFlare * 2.4, 0.0, 1.0));

          float alpha = core * (0.20 + vFlare * 0.85 + vHurt * vFlare * 0.6);
          alpha *= 0.45 + vDepth * 0.55;          // the far side sits back
          gl_FragColor = vec4(col, alpha);
        }`,
    });
    world.add(new THREE.Points(geo, pointMat));

    // ---------------------------------------------------------------- the filaments
    // Short chords between near neighbours. A connected body, not dust.
    const linePos = new Float32Array(FILAMENTS * 6);
    const lineSeed = new Float32Array(FILAMENTS * 2);
    for (let i = 0; i < FILAMENTS; i++) {
      const a = dirs[(i * 37) % POINTS];
      let b = dirs[(i * 37 + 1 + (i % 5)) % POINTS];
      if (a.distanceTo(b) > 0.42) b = a.clone().lerp(b, 0.3).normalize();
      linePos.set([a.x * RADIUS, a.y * RADIUS, a.z * RADIUS,
                   b.x * RADIUS, b.y * RADIUS, b.z * RADIUS], i * 6);
      lineSeed[i * 2] = lineSeed[i * 2 + 1] = (i % 997) / 997;
    }
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position", new THREE.BufferAttribute(linePos, 3));
    lineGeo.setAttribute("aSeed", new THREE.BufferAttribute(lineSeed, 1));

    const lineMat = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uWave: { value: -1 },
        uOrigin: { value: new THREE.Vector3(0.72, 0.34, 0.6).normalize() },
      },
      vertexShader: `
        attribute float aSeed;
        uniform float uWave;
        uniform vec3 uOrigin;
        varying float vGlow;
        void main() {
          float ang = acos(clamp(dot(normalize(position), uOrigin), -1.0, 1.0)) / 3.14159;
          float d = ang - uWave;
          vGlow = uWave < 0.0 ? 0.0 : exp(-d * d * 420.0);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: `
        varying float vGlow;
        void main() {
          vec3 base = vec3(0.16, 0.14, 0.11);
          vec3 lit  = vec3(0.95, 0.69, 0.14);
          gl_FragColor = vec4(mix(base, lit, vGlow), 0.30 + vGlow * 0.7);
        }`,
    });
    world.add(new THREE.LineSegments(lineGeo, lineMat));

    // ---------------------------------------------------------------- the shock ring
    // The front itself, as a ring expanding over the surface. Cheap, and it is the thing
    // that makes the wave read as an event rather than a colour change.
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.97, 1.0, 128),
      new THREE.MeshBasicMaterial({
        color: 0xf2b024, transparent: true, opacity: 0, side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending, depthWrite: false,
      })
    );
    world.add(ring);
    const origin = new THREE.Vector3(0.72, 0.34, 0.6).normalize();

    // ---------------------------------------------------------------- interaction
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let spinY = 0;
    let spinX = -0.12;
    let targetY = 0;
    let targetX = -0.12;
    const down = (e: PointerEvent) => { dragging = true; lastX = e.clientX; lastY = e.clientY; };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      targetY += (e.clientX - lastX) * 0.005;
      targetX = Math.max(-0.9, Math.min(0.9, targetX + (e.clientY - lastY) * 0.004));
      lastX = e.clientX;
      lastY = e.clientY;
    };
    const up = () => { dragging = false; };
    el.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);

    // ---------------------------------------------------------------- loop
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = (now - start) / 1000;
      const cycle = t % 7.5;
      const wave = reduced ? 0.42 : (cycle < 5.4 ? cycle / 5.4 : -1);

      pointMat.uniforms.uTime.value = t;
      pointMat.uniforms.uWave.value = wave;
      lineMat.uniforms.uWave.value = wave;

      if (wave >= 0) {
        // the ring sits on the surface, at the latitude the front has reached
        const angle = wave * Math.PI;
        const scale = Math.sin(angle) * RADIUS * 1.02;
        ring.scale.setScalar(Math.max(0.001, scale));
        ring.position.copy(origin).multiplyScalar(Math.cos(angle) * RADIUS * 1.02);
        ring.lookAt(ring.position.clone().add(origin));
        (ring.material as THREE.MeshBasicMaterial).opacity =
          Math.sin(angle) * 0.75 * (wave < 0.94 ? 1 : (1 - wave) * 16);
      } else {
        (ring.material as THREE.MeshBasicMaterial).opacity = 0;
      }

      if (!dragging && !reduced) targetY += 0.0016;
      spinY += (targetY - spinY) * 0.055;
      spinX += (targetX - spinX) * 0.055;
      world.rotation.y = spinY;
      world.rotation.x = spinX;

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
      ring.geometry.dispose();
      (ring.material as THREE.Material).dispose();
      pointMat.dispose();
      lineMat.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [height, harmed, population]);

  return <div ref={mount} style={{ width: "100%", height, cursor: "grab" }} />;
}
