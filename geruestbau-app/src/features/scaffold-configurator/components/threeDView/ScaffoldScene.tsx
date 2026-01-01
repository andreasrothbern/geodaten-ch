/**
 * ScaffoldScene - 3D visualization using IFC.js (@thatopen/components)
 *
 * Uses ThatOpen Components for IFC-compatible 3D rendering with
 * future support for IFC/DXF export to LayPLAN.
 */

import { useRef, useEffect, useState } from 'react';
import * as OBC from '@thatopen/components';
import * as THREE from 'three';
import type { ScaffoldConfiguration, ScaffoldFacade, View3D } from '../../types/scaffold.types';

interface ScaffoldSceneProps {
  configuration: ScaffoldConfiguration;
  activeView: View3D;
  onViewChange?: (view: View3D) => void;
}

// Camera position presets for different views
const VIEW_POSITIONS: Record<View3D, { position: THREE.Vector3; target: THREE.Vector3 }> = {
  isometric: { position: new THREE.Vector3(30, 25, 30), target: new THREE.Vector3(0, 8, 0) },
  north: { position: new THREE.Vector3(0, 10, 40), target: new THREE.Vector3(0, 8, 0) },
  east: { position: new THREE.Vector3(40, 10, 0), target: new THREE.Vector3(0, 8, 0) },
  south: { position: new THREE.Vector3(0, 10, -40), target: new THREE.Vector3(0, 8, 0) },
  west: { position: new THREE.Vector3(-40, 10, 0), target: new THREE.Vector3(0, 8, 0) },
  top: { position: new THREE.Vector3(0, 50, 0.1), target: new THREE.Vector3(0, 0, 0) },
};

// Helper to create building geometry
function createBuilding(width: number, depth: number, height: number): THREE.Mesh {
  const geometry = new THREE.BoxGeometry(width, height, depth);
  const material = new THREE.MeshStandardMaterial({
    color: 0xe5e7eb,
    transparent: true,
    opacity: 0.7,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(0, height / 2, 0);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

// Helper to create roof geometry
function createRoof(width: number, depth: number, roofHeight: number, buildingHeight: number): THREE.Group {
  const group = new THREE.Group();

  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, 0);
  shape.lineTo(0, roofHeight);
  shape.lineTo(width / 2, 0);
  shape.closePath();

  const extrudeSettings = { depth: depth, bevelEnabled: false };
  const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
  const material = new THREE.MeshStandardMaterial({ color: 0x8b5cf6 });
  const mesh = new THREE.Mesh(geometry, material);

  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(0, buildingHeight, -depth / 2);
  mesh.castShadow = true;

  group.add(mesh);
  return group;
}

// Helper to create scaffold cell
function createScaffoldCell(
  x: number, y: number, z: number,
  width: number, height: number, depth: number,
  color: number
): THREE.Group {
  const group = new THREE.Group();

  // Main frame
  const geometry = new THREE.BoxGeometry(width, height, depth);
  const material = new THREE.MeshStandardMaterial({
    color: color,
    transparent: true,
    opacity: 0.8,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;

  // Wireframe
  const edges = new THREE.EdgesGeometry(geometry);
  const line = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x991b1b })
  );

  group.add(mesh);
  group.add(line);
  group.position.set(x, y, z);

  return group;
}

// Helper to create scaffold facade
function createScaffoldFacade(
  facade: ScaffoldFacade,
  fieldWidth: number,
  levelHeight: number,
  offset: THREE.Vector3,
  direction: 'x' | 'z'
): THREE.Group {
  const group = new THREE.Group();
  const cellDepth = 0.73;
  // Fallback color if facade.color is undefined (can happen with old localStorage data)
  const colorHex = parseInt((facade.color || '#6B7280').replace('#', ''), 16);

  for (let level = 0; level < facade.levels; level++) {
    for (let field = 0; field < facade.fields; field++) {
      const key = `${field}-${level}`;
      if (facade.modifications.removed_cells.has(key)) continue;

      const cellWidth = fieldWidth * 0.95;
      const cellHeight = levelHeight * 0.95;

      let x: number, y: number, z: number;
      let w: number, d: number;

      if (direction === 'x') {
        x = offset.x + field * fieldWidth + fieldWidth / 2;
        y = offset.y + level * levelHeight + levelHeight / 2;
        z = offset.z;
        w = cellWidth;
        d = cellDepth;
      } else {
        x = offset.x;
        y = offset.y + level * levelHeight + levelHeight / 2;
        z = offset.z + field * fieldWidth + fieldWidth / 2;
        w = cellDepth;
        d = cellWidth;
      }

      // Check if this is a lift or stairs column
      let cellColor = colorHex;
      if (facade.modifications.lift_position === field) {
        cellColor = 0xfef3c7; // Yellow tint for lift
      } else if (facade.modifications.stairs_position === field) {
        cellColor = 0xdcfce7; // Green tint for stairs
      }

      const cell = createScaffoldCell(x, y, z, w, cellHeight, d, cellColor);
      group.add(cell);
    }
  }

  return group;
}

// Helper to create access marker (lift/stairs)
function createAccessMarker(
  position: THREE.Vector3,
  height: number,
  type: 'lift' | 'stairs'
): THREE.Group {
  const group = new THREE.Group();
  const color = type === 'lift' ? 0xf59e0b : 0x22c55e;

  // Cylinder
  const cylGeom = new THREE.CylinderGeometry(0.3, 0.3, height, 8);
  const cylMat = new THREE.MeshStandardMaterial({
    color: color,
    transparent: true,
    opacity: 0.6,
  });
  const cylinder = new THREE.Mesh(cylGeom, cylMat);
  cylinder.position.y = height / 2;

  // Sphere on top
  const sphereGeom = new THREE.SphereGeometry(0.5, 16, 16);
  const sphereMat = new THREE.MeshStandardMaterial({ color: color });
  const sphere = new THREE.Mesh(sphereGeom, sphereMat);
  sphere.position.y = height + 0.5;

  group.add(cylinder);
  group.add(sphere);
  group.position.copy(position);

  return group;
}

// Helper to create ground
function createGround(): THREE.Mesh {
  const geometry = new THREE.PlaneGeometry(100, 100);
  const material = new THREE.MeshStandardMaterial({ color: 0xf3f4f6 });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = -0.01;
  mesh.receiveShadow = true;
  return mesh;
}

// Helper to create grid
function createGrid(): THREE.GridHelper {
  const grid = new THREE.GridHelper(100, 100, 0x9ca3af, 0xd1d5db);
  grid.position.y = 0.01;
  return grid;
}

// Main component
export default function ScaffoldScene({ configuration, activeView }: ScaffoldSceneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const componentsRef = useRef<OBC.Components | null>(null);
  const worldRef = useRef<OBC.SimpleWorld<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const initScene = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Create components instance
        const components = new OBC.Components();
        componentsRef.current = components;

        // Create world with scene, camera, renderer
        const worlds = components.get(OBC.Worlds);
        const world = worlds.create<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer>();
        worldRef.current = world;

        // Setup scene
        world.scene = new OBC.SimpleScene(components);
        world.scene.setup();
        world.scene.three.background = new THREE.Color(0xf0f9ff);

        // Setup renderer
        world.renderer = new OBC.SimpleRenderer(components, container);

        // Setup camera
        world.camera = new OBC.SimpleCamera(components);
        world.camera.controls.setLookAt(
          VIEW_POSITIONS[activeView].position.x,
          VIEW_POSITIONS[activeView].position.y,
          VIEW_POSITIONS[activeView].position.z,
          VIEW_POSITIONS[activeView].target.x,
          VIEW_POSITIONS[activeView].target.y,
          VIEW_POSITIONS[activeView].target.z
        );

        // Initialize components
        components.init();

        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(20, 30, 20);
        directionalLight.castShadow = true;
        world.scene.three.add(ambientLight);
        world.scene.three.add(directionalLight);

        // Add ground and grid
        world.scene.three.add(createGround());
        world.scene.three.add(createGrid());

        // Add building and scaffolds
        addSceneContent(world.scene.three, configuration);

        setIsLoading(false);
      } catch (err) {
        console.error('Error initializing 3D scene:', err);
        setError('Fehler beim Laden der 3D-Ansicht');
        setIsLoading(false);
      }
    };

    initScene();

    // Cleanup
    return () => {
      if (componentsRef.current) {
        componentsRef.current.dispose();
        componentsRef.current = null;
      }
    };
  }, []);

  // Update camera when view changes
  useEffect(() => {
    if (!worldRef.current?.camera) return;

    const { position, target } = VIEW_POSITIONS[activeView];
    worldRef.current.camera.controls.setLookAt(
      position.x, position.y, position.z,
      target.x, target.y, target.z,
      true // Enable smooth transition
    );
  }, [activeView]);

  // Add scene content
  function addSceneContent(scene: THREE.Scene, config: ScaffoldConfiguration) {
    const facades = config.elements.filter((el): el is ScaffoldFacade => el.type === 'facade');

    // Calculate building dimensions based on facade directions
    // Group facades by orientation (N/S are width, E/W are depth)
    const nsLength = facades
      .filter(f => ['N', 'S', 'NE', 'NW', 'SE', 'SW'].includes(f.direction))
      .reduce((sum, f) => Math.max(sum, f.length_m), 10);
    const ewLength = facades
      .filter(f => ['E', 'W'].includes(f.direction))
      .reduce((sum, f) => Math.max(sum, f.length_m), 8);

    // Use actual facade lengths for building dimensions
    const buildingWidth = Math.max(10, nsLength);
    const buildingDepth = Math.max(8, ewLength > 0 ? ewLength : nsLength * 0.6);

    // Calculate building height directly from facades (totals may not be ready yet)
    const maxFacadeHeight = facades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * config.settings.level_height_m), 10);
    const buildingHeight = Math.max(8, maxFacadeHeight * 0.8);

    const fieldWidth = config.settings.field_width_m;
    const levelHeight = config.settings.level_height_m;

    // Add building
    scene.add(createBuilding(buildingWidth, buildingDepth, buildingHeight));

    // Add roof if needed
    if (config.settings.work_type === 'roof' || config.settings.work_type === 'full') {
      scene.add(createRoof(buildingWidth + 1, buildingDepth + 1, 3, buildingHeight));
    }

    // Track which directions we've seen to position facades correctly
    const directionCount: Record<string, number> = {};

    // Get scaffold offset based on direction
    const getOffset = (facade: ScaffoldFacade): { offset: THREE.Vector3; dir: 'x' | 'z' } => {
      const gap = 0.5;
      const dir = facade.direction;

      // Count how many of this direction we've seen (for stacking multiple facades)
      directionCount[dir] = (directionCount[dir] || 0);
      const stackOffset = directionCount[dir] * 3; // Stack multiple same-direction facades
      directionCount[dir]++;

      // Map directions to positions around building
      // N, NE, NW = front (positive Z)
      // S, SE, SW = back (negative Z)
      // E = right (positive X)
      // W = left (negative X)
      switch (dir) {
        case 'N':
        case 'NE':
        case 'NW':
          return { offset: new THREE.Vector3(-facade.length_m / 2, 0, buildingDepth / 2 + gap + stackOffset), dir: 'x' };
        case 'S':
        case 'SE':
        case 'SW':
          return { offset: new THREE.Vector3(-facade.length_m / 2, 0, -buildingDepth / 2 - gap - 0.73 - stackOffset), dir: 'x' };
        case 'E':
          return { offset: new THREE.Vector3(buildingWidth / 2 + gap + stackOffset, 0, -facade.length_m / 2), dir: 'z' };
        case 'W':
          return { offset: new THREE.Vector3(-buildingWidth / 2 - gap - 0.73 - stackOffset, 0, -facade.length_m / 2), dir: 'z' };
        default:
          // For unknown directions, distribute facades around the building
          const fallbackIndex = Object.keys(directionCount).filter(k => k === dir).length;
          const side = fallbackIndex % 4;
          switch (side) {
            case 0: return { offset: new THREE.Vector3(-facade.length_m / 2, 0, buildingDepth / 2 + gap), dir: 'x' };
            case 1: return { offset: new THREE.Vector3(buildingWidth / 2 + gap, 0, -facade.length_m / 2), dir: 'z' };
            case 2: return { offset: new THREE.Vector3(-facade.length_m / 2, 0, -buildingDepth / 2 - gap - 0.73), dir: 'x' };
            case 3: return { offset: new THREE.Vector3(-buildingWidth / 2 - gap - 0.73, 0, -facade.length_m / 2), dir: 'z' };
            default: return { offset: new THREE.Vector3(0, 0, 0), dir: 'x' };
          }
      }
    };

    // Add scaffolds
    facades.forEach((facade) => {
      const { offset, dir } = getOffset(facade);
      scene.add(createScaffoldFacade(facade, fieldWidth, levelHeight, offset, dir));

      // Add lift marker
      if (facade.modifications.lift_position !== null) {
        const liftPos = new THREE.Vector3(
          dir === 'x' ? offset.x + facade.modifications.lift_position * fieldWidth + fieldWidth / 2 : offset.x,
          0,
          dir === 'z' ? offset.z + facade.modifications.lift_position * fieldWidth + fieldWidth / 2 : offset.z
        );
        scene.add(createAccessMarker(liftPos, facade.levels * levelHeight, 'lift'));
      }

      // Add stairs marker
      if (facade.modifications.stairs_position !== null) {
        const stairsPos = new THREE.Vector3(
          dir === 'x' ? offset.x + facade.modifications.stairs_position * fieldWidth + fieldWidth / 2 : offset.x,
          0,
          dir === 'z' ? offset.z + facade.modifications.stairs_position * fieldWidth + fieldWidth / 2 : offset.z
        );
        scene.add(createAccessMarker(stairsPos, facade.levels * levelHeight, 'stairs'));
      }
    });
  }

  return (
    <div ref={containerRef} className="w-full h-full min-h-[400px] relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-sky-50">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-600">3D-Szene wird geladen...</p>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-red-50">
          <div className="text-center text-red-600">
            <p className="font-medium">{error}</p>
            <p className="text-sm mt-1">Bitte Seite neu laden</p>
          </div>
        </div>
      )}
    </div>
  );
}
