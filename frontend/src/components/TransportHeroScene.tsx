import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Persona, Severity, SimulationRun } from "@/types/simulation";

interface TransportHeroSceneProps {
  run: SimulationRun;
  stage: 0 | 1 | 2;
  onRevealComplete?: () => void;
}

const WORLD_SIZE = 15;

function stableOrder(id: string): number {
  let hash = 0;
  for (let index = 0; index < id.length; index += 1) {
    hash = (hash * 31 + id.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function chooseResidents(run: SimulationRun): Persona[] {
  const outcomeById = new Map(run.outcomes.map((outcome) => [outcome.persona_id, outcome]));
  const affected = run.personas
    .filter((persona) => outcomeById.get(persona.persona_id)?.severity !== "none")
    .sort((a, b) => stableOrder(a.persona_id) - stableOrder(b.persona_id))
    .slice(0, 16);
  const neutral = run.personas
    .filter((persona) => outcomeById.get(persona.persona_id)?.severity === "none")
    .sort((a, b) => stableOrder(a.persona_id) - stableOrder(b.persona_id))
    .slice(0, 18);
  const selected = new Map([...affected, ...neutral].map((persona) => [persona.persona_id, persona]));

  for (const edge of run.graph.edges
    .filter((candidate) => candidate.kind === "CARES_FOR" && outcomeById.get(candidate.source)?.second_order)
    .slice(0, 6)) {
    const source = run.personas.find((persona) => persona.persona_id === edge.source);
    const target = run.personas.find((persona) => persona.persona_id === edge.target);
    if (source) selected.set(source.persona_id, source);
    if (target) selected.set(target.persona_id, target);
  }
  return [...selected.values()];
}

export function TransportHeroScene({ run, stage, onRevealComplete }: TransportHeroSceneProps) {
  const mount = useRef<HTMLDivElement>(null);
  const stageRef = useRef(stage);
  const revealStartedAt = useRef<number | null>(stage >= 2 ? performance.now() : null);
  const revealReported = useRef(false);
  const completeRef = useRef(onRevealComplete);

  useEffect(() => {
    const previous = stageRef.current;
    stageRef.current = stage;
    if (stage >= 2 && previous < 2) {
      revealStartedAt.current = performance.now();
      revealReported.current = false;
    }
    if (stage === 0) {
      revealStartedAt.current = null;
      revealReported.current = false;
    }
  }, [stage]);

  useEffect(() => {
    completeRef.current = onRevealComplete;
  }, [onRevealComplete]);

  useEffect(() => {
    const element = mount.current;
    if (!element) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xe7ecee, 0.032);

    const camera = new THREE.PerspectiveCamera(29, 1, 0.1, 100);
    camera.position.set(10.4, 10.8, 12.7);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.7));
    renderer.setClearColor(0xe7ecee, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.AgXToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    element.appendChild(renderer.domElement);

    const world = new THREE.Group();
    world.rotation.y = -0.17;
    scene.add(world);

    scene.add(new THREE.HemisphereLight(0xdceeff, 0x637068, 1.45));
    scene.add(new THREE.AmbientLight(0xffffff, 0.45));
    const keyLight = new THREE.DirectionalLight(0xfff7e7, 3.25);
    keyLight.position.set(-8, 14, 6);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(1024, 1024);
    keyLight.shadow.camera.near = 2;
    keyLight.shadow.camera.far = 34;
    keyLight.shadow.camera.left = -12;
    keyLight.shadow.camera.right = 12;
    keyLight.shadow.camera.top = 12;
    keyLight.shadow.camera.bottom = -12;
    keyLight.shadow.bias = -0.0004;
    scene.add(keyLight);
    const rimLight = new THREE.PointLight(0x72a9c4, 2.6, 28, 2);
    rimLight.position.set(4, 4, -3);
    scene.add(rimLight);

    const [spanX, spanY] = run.geography.span;
    const centreX = spanX / 2;
    const centreY = spanY / 2;
    const scale = WORLD_SIZE / Math.max(spanX, spanY);
    const project = ([x, y]: [number, number]) => new THREE.Vector3(
      (x - centreX) * scale,
      0,
      (y - centreY) * scale,
    );
    const blockById = new Map(run.geography.blocks.map((block) => [block.block_id, block]));
    const projectResident = (persona: Persona) => {
      const hash = stableOrder(persona.persona_id);
      const block = blockById.get(persona.block_id);
      if (!block) return project(persona.xy);

      const position = project([block.x + block.w / 2, block.y + block.h / 2]);
      const halfWidth = Math.max(0.11, block.w * scale * 0.84) / 2;
      const halfDepth = Math.max(0.11, block.h * scale * 0.84) / 2;
      const side = hash % 4;
      const along = (((hash >>> 4) % 101) / 100 - 0.5) * 1.7;
      const pavement = 0.18;

      if (side === 0 || side === 2) {
        position.x += along * halfWidth;
        position.z += (side === 0 ? -1 : 1) * (halfDepth + pavement);
      } else {
        position.x += (side === 1 ? 1 : -1) * (halfWidth + pavement);
        position.z += along * halfDepth;
      }
      return position;
    };

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(WORLD_SIZE * 2.6, WORLD_SIZE * 2.6),
      new THREE.MeshStandardMaterial({ color: 0xdde4e1, roughness: 1, metalness: 0 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.05;
    ground.receiveShadow = true;
    world.add(ground);

    const makeFacadeTexture = (accent: string) => {
      const canvas = document.createElement("canvas");
      canvas.width = 128;
      canvas.height = 192;
      const context = canvas.getContext("2d");
      if (!context) return null;
      context.fillStyle = "#d9ddda";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = accent;
      context.fillRect(0, 0, canvas.width, 13);
      context.fillRect(0, 88, canvas.width, 8);
      context.fillStyle = "#75848a";
      for (let row = 0; row < 9; row += 1) {
        for (let column = 0; column < 5; column += 1) {
          context.fillRect(9 + column * 24, 22 + row * 18, 10, 7);
        }
      }
      context.fillStyle = "rgba(255,255,255,.62)";
      for (let row = 0; row < 8; row += 1) {
        context.fillRect(0, 35 + row * 18, canvas.width, 2);
      }
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
      return texture;
    };
    const facadeTexture = makeFacadeTexture("#b4513e");
    const alternateFacadeTexture = makeFacadeTexture("#3f7187");
    const buildingMaterial = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      map: facadeTexture,
      roughness: 0.9,
      metalness: 0.01,
    });
    const highlightedBuildingMaterial = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      map: alternateFacadeTexture,
      roughness: 0.88,
      metalness: 0.01,
    });
    const roofMaterial = new THREE.MeshStandardMaterial({ color: 0xaeb9b9, roughness: 0.95 });
    const roofGeometry = new THREE.BoxGeometry(1, 1, 1);
    const buildingGeometries: THREE.BoxGeometry[] = [];
    const edgeMaterials: THREE.LineBasicMaterial[] = [];

    run.geography.blocks.forEach((block, index) => {
      const width = Math.max(0.11, block.w * scale * 0.84);
      const depth = Math.max(0.11, block.h * scale * 0.84);
      const height = 0.16 + Math.min(1.12, block.storeys * 0.03);
      const geometry = new THREE.BoxGeometry(width, height, depth);
      buildingGeometries.push(geometry);
      const facade = index % 11 === 0 ? highlightedBuildingMaterial : buildingMaterial;
      const building = new THREE.Mesh(geometry, [facade, facade, roofMaterial, roofMaterial, facade, facade]);
      const position = project([block.x + block.w / 2, block.y + block.h / 2]);
      building.position.set(position.x, height / 2, position.z);
      building.castShadow = true;
      building.receiveShadow = true;
      world.add(building);

      if (index % 7 === 0) {
        const rooftop = new THREE.Mesh(roofGeometry, roofMaterial);
        rooftop.position.set(position.x, height + 0.035, position.z);
        rooftop.scale.set(Math.max(0.08, width * 0.24), 0.07, Math.max(0.08, depth * 0.25));
        rooftop.castShadow = true;
        world.add(rooftop);
      }

      if (index % 3 === 0) {
        const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x73828a, transparent: true, opacity: 0.32 });
        edgeMaterials.push(edgeMaterial);
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), edgeMaterial);
        edges.position.copy(building.position);
        world.add(edges);
      }
    });

    const treeBlocks = run.geography.blocks.filter((_, index) => index % 8 === 0).slice(0, 36);
    const trunkGeometry = new THREE.CylinderGeometry(0.018, 0.028, 0.23, 7);
    const crownGeometry = new THREE.IcosahedronGeometry(0.14, 1);
    const trunkMaterial = new THREE.MeshStandardMaterial({ color: 0x76614b, roughness: 1 });
    const crownMaterial = new THREE.MeshStandardMaterial({ color: 0x3f7650, roughness: 0.96 });
    const trunks = new THREE.InstancedMesh(trunkGeometry, trunkMaterial, treeBlocks.length);
    const crowns = new THREE.InstancedMesh(crownGeometry, crownMaterial, treeBlocks.length);
    const treeDummy = new THREE.Object3D();
    treeBlocks.forEach((block, index) => {
      const position = project([block.x + block.w / 2, block.y + block.h / 2]);
      const halfWidth = Math.max(0.11, block.w * scale * 0.84) / 2;
      const halfDepth = Math.max(0.11, block.h * scale * 0.84) / 2;
      position.x += (index % 2 === 0 ? 1 : -1) * (halfWidth + 0.2);
      position.z += (index % 3 === 0 ? 1 : -1) * (halfDepth + 0.2);
      const size = 0.86 + (index % 5) * 0.045;
      treeDummy.position.set(position.x, 0.115, position.z);
      treeDummy.scale.set(size, size, size);
      treeDummy.updateMatrix();
      trunks.setMatrixAt(index, treeDummy.matrix);
      treeDummy.position.y = 0.31;
      treeDummy.scale.set(size, size * 0.92, size);
      treeDummy.updateMatrix();
      crowns.setMatrixAt(index, treeDummy.matrix);
    });
    trunks.instanceMatrix.needsUpdate = true;
    crowns.instanceMatrix.needsUpdate = true;
    trunks.castShadow = true;
    crowns.castShadow = true;
    world.add(trunks, crowns);

    const lineMaterials: THREE.Material[] = [];
    const lineGeometries: THREE.BufferGeometry[] = [];
    const addRoad = (points: [number, number][], y: number) => {
      if (points.length < 2) return;
      const projected = points.map((point) => project(point));
      const vertices: number[] = [];
      const indices: number[] = [];
      const halfWidth = 0.052;

      projected.forEach((point, index) => {
        const previous = projected[Math.max(0, index - 1)];
        const next = projected[Math.min(projected.length - 1, index + 1)];
        const dx = next.x - previous.x;
        const dz = next.z - previous.z;
        const length = Math.max(0.001, Math.hypot(dx, dz));
        const normalX = (-dz / length) * halfWidth;
        const normalZ = (dx / length) * halfWidth;
        vertices.push(
          point.x + normalX, y, point.z + normalZ,
          point.x - normalX, y, point.z - normalZ,
        );
        if (index < projected.length - 1) {
          const cursor = index * 2;
          indices.push(cursor, cursor + 1, cursor + 2, cursor + 1, cursor + 3, cursor + 2);
        }
      });

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      const material = new THREE.MeshStandardMaterial({
        color: 0x8f9a9f,
        roughness: 1,
        metalness: 0,
        side: THREE.DoubleSide,
      });
      lineGeometries.push(geometry);
      lineMaterials.push(material);
      const road = new THREE.Mesh(geometry, material);
      road.receiveShadow = true;
      world.add(road);
    };

    run.geography.service_lines
      .slice(0, 8)
      .forEach((service, index) => addRoad(service.points, 0.006 + index * 0.001));
    let focusRouteMaterial: THREE.MeshStandardMaterial | null = null;
    const focusRoutePoints = run.geography.route.map((point) => {
      const projected = project(point);
      projected.y = 0.105;
      return projected;
    });
    if (focusRoutePoints.length > 1) {
      const focusRouteGeometry = new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3(focusRoutePoints),
        Math.max(36, focusRoutePoints.length * 5),
        0.035,
        8,
        false,
      );
      focusRouteMaterial = new THREE.MeshStandardMaterial({
        color: stageRef.current >= 1 ? 0xd92d20 : 0x2e6582,
        roughness: 0.55,
        metalness: 0.08,
      });
      lineGeometries.push(focusRouteGeometry);
      lineMaterials.push(focusRouteMaterial);
      const focusRoute = new THREE.Mesh(focusRouteGeometry, focusRouteMaterial);
      focusRoute.castShadow = true;
      world.add(focusRoute);
    }

    const closedStops = new Set(run.policy.modifications.remove_stops);
    const markerGeometries: THREE.BufferGeometry[] = [];
    const markerMaterials: THREE.Material[] = [];
    const closureObjects: THREE.Object3D[] = [];
    const focusStops: typeof run.geography.stops = [];
    const seenStops = new Set<string>();
    run.geography.route.forEach((routePoint, index) => {
      if (index % 2 !== 0) return;
      const nearest = run.geography.stops
        .map((stop) => ({ stop, distance: Math.hypot(stop.x - routePoint[0], stop.y - routePoint[1]) }))
        .sort((a, b) => a.distance - b.distance)[0];
      if (!nearest || nearest.distance > 70 || seenStops.has(nearest.stop.stop_id)) return;
      seenStops.add(nearest.stop.stop_id);
      focusStops.push(nearest.stop);
    });

    const busStopCanvas = document.createElement("canvas");
    busStopCanvas.width = 128;
    busStopCanvas.height = 128;
    const busStopContext = busStopCanvas.getContext("2d");
    if (busStopContext) {
      busStopContext.fillStyle = "#1f5c83";
      busStopContext.fillRect(9, 9, 110, 110);
      busStopContext.strokeStyle = "#ffffff";
      busStopContext.lineWidth = 6;
      busStopContext.strokeRect(9, 9, 110, 110);
      busStopContext.fillStyle = "#ffffff";
      busStopContext.fillRect(31, 30, 66, 43);
      busStopContext.fillStyle = "#1f5c83";
      busStopContext.fillRect(39, 38, 22, 17);
      busStopContext.fillRect(67, 38, 22, 17);
      busStopContext.fillStyle = "#ffffff";
      busStopContext.beginPath();
      busStopContext.arc(42, 79, 8, 0, Math.PI * 2);
      busStopContext.arc(86, 79, 8, 0, Math.PI * 2);
      busStopContext.fill();
      busStopContext.font = "700 20px Arial";
      busStopContext.textAlign = "center";
      busStopContext.fillText("BUS", 64, 108);
    }
    const busStopTexture = new THREE.CanvasTexture(busStopCanvas);
    busStopTexture.colorSpace = THREE.SRGBColorSpace;
    const busStopMaterial = new THREE.SpriteMaterial({ map: busStopTexture, transparent: true });
    markerMaterials.push(busStopMaterial);
    const poleGeometry = new THREE.CylinderGeometry(0.008, 0.01, 0.24, 7);
    const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x65727a, roughness: 0.86 });
    const poles = new THREE.InstancedMesh(poleGeometry, poleMaterial, focusStops.length);
    const poleDummy = new THREE.Object3D();
    focusStops.forEach((stop, index) => {
      const position = project([stop.x, stop.y]);
      poleDummy.position.set(position.x, 0.12, position.z);
      poleDummy.updateMatrix();
      poles.setMatrixAt(index, poleDummy.matrix);
      const sign = new THREE.Sprite(busStopMaterial);
      sign.position.set(position.x, 0.32, position.z);
      sign.scale.set(0.27, 0.27, 1);
      world.add(sign);
    });
    poles.instanceMatrix.needsUpdate = true;
    poles.castShadow = true;
    markerGeometries.push(poleGeometry);
    markerMaterials.push(poleMaterial);
    world.add(poles);

    run.geography.stops.forEach((stop) => {
      if (!closedStops.has(stop.stop_id)) return;
      const position = project([stop.x, stop.y]);
      const pillarGeometry = new THREE.CylinderGeometry(0.06, 0.06, 0.42, 16);
      const pillarMaterial = new THREE.MeshStandardMaterial({ color: 0xc62828, roughness: 0.68, metalness: 0.08 });
      markerGeometries.push(pillarGeometry);
      markerMaterials.push(pillarMaterial);
      const pillar = new THREE.Mesh(pillarGeometry, pillarMaterial);
      pillar.position.set(position.x, 0.25, position.z);
      pillar.scale.setScalar(stageRef.current >= 1 ? 1 : 0.001);
      closureObjects.push(pillar);
      world.add(pillar);

      const ringGeometry = new THREE.TorusGeometry(0.34, 0.022, 10, 50);
      const ringMaterial = new THREE.MeshBasicMaterial({ color: 0xd92d20, transparent: true, opacity: 0.76 });
      markerGeometries.push(ringGeometry);
      markerMaterials.push(ringMaterial);
      const ring = new THREE.Mesh(ringGeometry, ringMaterial);
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(position.x, 0.04, position.z);
      ring.scale.setScalar(stageRef.current >= 1 ? 1 : 0.001);
      closureObjects.push(ring);
      world.add(ring);
    });

    const residents = chooseResidents(run);
    const outcomes = new Map(run.outcomes.map((outcome) => [outcome.persona_id, outcome]));
    type AvatarTone = Severity;
    const avatarGroups: Record<AvatarTone, Persona[]> = {
      none: [], moderate: [], high: [],
    };
    residents.forEach((persona) => {
      const outcome = outcomes.get(persona.persona_id);
      avatarGroups[outcome?.severity ?? "none"].push(persona);
    });

    const headGeometry = new THREE.SphereGeometry(1, 10, 8);
    const bodyGeometry = new THREE.CapsuleGeometry(0.5, 1, 4, 8);
    const avatarGeometries: THREE.BufferGeometry[] = [headGeometry, bodyGeometry];
    const avatarMaterials: THREE.MeshStandardMaterial[] = [];
    const avatarMaterialByTone: Partial<Record<AvatarTone, THREE.MeshStandardMaterial>> = {};
    const avatarMeshes: THREE.InstancedMesh[] = [];
    const toneColours: Record<AvatarTone, number> = {
      none: 0x68767e,
      moderate: 0xf0a202,
      high: 0xd92d20,
    };
    const parts = [
      { geometry: headGeometry, offset: [0, .74, 0] as const, scale: [.12, .12, .12] as const, lean: 0 },
      { geometry: bodyGeometry, offset: [0, .47, 0] as const, scale: [.16, .19, .12] as const, lean: 0 },
      { geometry: bodyGeometry, offset: [-.17, .46, 0] as const, scale: [.046, .16, .046] as const, lean: -.16 },
      { geometry: bodyGeometry, offset: [.17, .46, 0] as const, scale: [.046, .16, .046] as const, lean: .16 },
      { geometry: bodyGeometry, offset: [-.066, .17, 0] as const, scale: [.054, .19, .054] as const, lean: .055 },
      { geometry: bodyGeometry, offset: [.066, .17, 0] as const, scale: [.054, .19, .054] as const, lean: -.055 },
    ];
    const dummy = new THREE.Object3D();
    const yAxis = new THREE.Vector3(0, 1, 0);

    (Object.keys(avatarGroups) as AvatarTone[]).forEach((tone) => {
      const people = avatarGroups[tone];
      if (!people.length) return;
      const material = new THREE.MeshStandardMaterial({
        color: stageRef.current >= 2 ? toneColours[tone] : toneColours.none,
        roughness: 0.82,
        metalness: 0.06,
      });
      avatarMaterials.push(material);
      avatarMaterialByTone[tone] = material;

      parts.forEach((part) => {
        const mesh = new THREE.InstancedMesh(part.geometry, material, people.length);
        people.forEach((persona, index) => {
          const position = projectResident(persona);
          const facing = ((stableOrder(persona.persona_id) % 628) / 100) - Math.PI;
          const rotatedOffset = new THREE.Vector3(part.offset[0], 0, part.offset[2]).applyAxisAngle(yAxis, facing);
          dummy.position.set(position.x + rotatedOffset.x, 0.04 + part.offset[1], position.z + rotatedOffset.z);
          dummy.rotation.set(0, facing, part.lean);
          dummy.scale.set(part.scale[0], part.scale[1], part.scale[2]);
          dummy.updateMatrix();
          mesh.setMatrixAt(index, dummy.matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
        mesh.castShadow = true;
        avatarMeshes.push(mesh);
        world.add(mesh);
      });
    });

    const personaById = new Map(run.personas.map((persona) => [persona.persona_id, persona]));
    const caregiverMaterials: THREE.LineDashedMaterial[] = [];
    run.graph.edges
      .filter((edge) => edge.kind === "CARES_FOR" && outcomes.get(edge.source)?.second_order)
      .slice(0, 6)
      .forEach((edge) => {
        const source = personaById.get(edge.source);
        const target = personaById.get(edge.target);
        if (!source || !target) return;
        const start = projectResident(source);
        const end = projectResident(target);
        start.y = end.y = 0.28;
        const middle = start.clone().lerp(end, 0.5);
        middle.y = 0.82;
        const curve = new THREE.QuadraticBezierCurve3(start, middle, end);
        const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(24));
        const material = new THREE.LineDashedMaterial({
          color: 0x356bb3,
          transparent: true,
          opacity: stageRef.current >= 2 ? 0.62 : 0,
          dashSize: 0.13,
          gapSize: 0.1,
        });
        const line = new THREE.Line(geometry, material);
        line.computeLineDistances();
        lineGeometries.push(geometry);
        lineMaterials.push(material);
        caregiverMaterials.push(material);
        world.add(line);
      });

    const baselineRouteColour = new THREE.Color(0x2e6582);
    const proposalRouteColour = new THREE.Color(0xd92d20);
    const avatarTargetColours: Record<AvatarTone, THREE.Color> = {
      none: new THREE.Color(toneColours.none),
      moderate: new THREE.Color(toneColours.moderate),
      high: new THREE.Color(toneColours.high),
    };
    let targetRotation = -0.17;

    const resize = () => {
      const width = Math.max(1, element.clientWidth);
      const height = Math.max(1, element.clientHeight);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.position.set(width < 700 ? 10.8 : 10.2, width < 700 ? 13.6 : 10.8, width < 700 ? 16.2 : 12.8);
      world.position.x = width > 1100 ? 1.35 : width > 700 ? 0.45 : 0;
      world.position.y = width < 700 ? 0.7 : 0.85;
      world.position.z = width < 700 ? 0.45 : 0;
      camera.updateProjectionMatrix();
      camera.lookAt(width > 1100 ? 0.55 : 0, 0.55, 0);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();

    let frame = 0;
    const ease = (value: number) => value * value * (3 - 2 * value);
    const progressBetween = (progress: number, start: number, end: number) =>
      ease(THREE.MathUtils.clamp((progress - start) / (end - start), 0, 1));
    const render = () => {
      const activeStage = stageRef.current;
      const started = revealStartedAt.current;
      const rawProgress = activeStage >= 2
        ? reducedMotion ? 1 : THREE.MathUtils.clamp((performance.now() - (started ?? performance.now())) / 2900, 0, 1)
        : 0;
      const routeProgress = activeStage >= 1 ? progressBetween(rawProgress, 0, 0.34) : 0;
      const closureProgress = activeStage >= 1 ? progressBetween(rawProgress, 0.12, 0.46) : 0;
      const avatarProgress = progressBetween(rawProgress, 0.3, 0.86);
      const caregiverProgress = progressBetween(rawProgress, 0.7, 1);
      if (!reducedMotion) targetRotation += 0.0008;
      world.rotation.y += (targetRotation - world.rotation.y) * 0.045;
      focusRouteMaterial?.color.copy(baselineRouteColour).lerp(proposalRouteColour, routeProgress);
      const closureScale = THREE.MathUtils.lerp(0.001, 1, closureProgress);
      closureObjects.forEach((object) => {
        object.scale.setScalar(closureScale);
      });
      (Object.keys(avatarMaterialByTone) as AvatarTone[]).forEach((tone) => {
        const material = avatarMaterialByTone[tone];
        material?.color.copy(avatarTargetColours.none).lerp(avatarTargetColours[tone], avatarProgress);
      });
      caregiverMaterials.forEach((material) => {
        material.opacity = 0.62 * caregiverProgress;
      });
      if (rawProgress >= 1 && !revealReported.current) {
        revealReported.current = true;
        completeRef.current?.();
      }
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      buildingGeometries.forEach((geometry) => geometry.dispose());
      lineGeometries.forEach((geometry) => geometry.dispose());
      markerGeometries.forEach((geometry) => geometry.dispose());
      edgeMaterials.forEach((material) => material.dispose());
      lineMaterials.forEach((material) => material.dispose());
      markerMaterials.forEach((material) => material.dispose());
      avatarGeometries.forEach((geometry) => geometry.dispose());
      avatarMaterials.forEach((material) => material.dispose());
      avatarMeshes.forEach((mesh) => mesh.dispose());
      buildingMaterial.dispose();
      highlightedBuildingMaterial.dispose();
      roofMaterial.dispose();
      roofGeometry.dispose();
      facadeTexture?.dispose();
      alternateFacadeTexture?.dispose();
      trunkGeometry.dispose();
      crownGeometry.dispose();
      trunkMaterial.dispose();
      crownMaterial.dispose();
      trunks.dispose();
      crowns.dispose();
      busStopTexture.dispose();
      poles.dispose();
      ground.geometry.dispose();
      (ground.material as THREE.Material).dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [run]);

  return (
    <div
      ref={mount}
      className="hero-scene"
      role="img"
      aria-label={`Three-dimensional transport simulation of ${run.study_area}, Singapore`}
    />
  );
}
