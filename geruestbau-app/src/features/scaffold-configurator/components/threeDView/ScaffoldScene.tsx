/**
 * ScaffoldScene - 3D visualization using IFC.js (@thatopen/components)
 *
 * Uses ThatOpen Components for IFC-compatible 3D rendering with
 * future support for IFC/DXF export to LayPLAN.
 */

import { useRef, useEffect, useState } from 'react';
import * as OBC from '@thatopen/components';
import * as THREE from 'three';
import type { ScaffoldConfiguration, ScaffoldFacade, ScaffoldCorner, View3D, BuildingZone } from '../../types/scaffold.types';
import type { NeighborBuilding, ObjectData } from '../../../../api/geruestbau';
import type { BuildingWall } from '../../../../types/project';
import { createSatteldachGeometry, type Point2D } from '../../utils/roofGeometry';

// NOTE 19.01.2026: calculatePolygonRoofOrientation wurde entfernt nach Objekt-Architektur Refactoring
// Die Funktion wurde nur für Multi-Building-Polygone benötigt, die jetzt als Union im Haupt-Polygon sind.
// Falls wieder benötigt: Siehe Git-History oder createRoofFromPolygon() für ähnliche Logik.

interface ScaffoldSceneProps {
  configuration: ScaffoldConfiguration;
  activeView: View3D;
  onViewChange?: (view: View3D) => void;
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
  // NEU 19.01.2026: Objekt-Architektur - Ein Projekt = Ein Objekt
  objectData?: ObjectData;
  zones?: BuildingZone[];
  complexity?: 'simple' | 'moderate' | 'complex';
  // NEU 18.01.2026: Echte 3D-Wandgeometrie aus swissBUILDINGS3D
  buildingWalls?: BuildingWall[];
}

// Camera position presets for different views
// Camera positions: LV95 Y (Northing) maps to -Z in THREE.js
// So "north" view = camera at -Z looking toward +Z (toward south in LV95)
// This means we swap north/south positions to match real-world orientation
const VIEW_POSITIONS: Record<View3D, { position: THREE.Vector3; target: THREE.Vector3 }> = {
  isometric: { position: new THREE.Vector3(30, 25, 30), target: new THREE.Vector3(0, 8, 0) },
  north: { position: new THREE.Vector3(0, 10, -40), target: new THREE.Vector3(0, 8, 0) },  // Looking from south toward north
  east: { position: new THREE.Vector3(40, 10, 0), target: new THREE.Vector3(0, 8, 0) },
  south: { position: new THREE.Vector3(0, 10, 40), target: new THREE.Vector3(0, 8, 0) },   // Looking from north toward south
  west: { position: new THREE.Vector3(-40, 10, 0), target: new THREE.Vector3(0, 8, 0) },
  top: { position: new THREE.Vector3(0, 50, 0.1), target: new THREE.Vector3(0, 0, 0) },
};

// Helper to normalize LV95 coordinates to local 3D space
function normalizePolygon(polygon: [number, number][]): { normalized: [number, number][]; center: [number, number] } {
  if (!polygon || polygon.length === 0) {
    return { normalized: [], center: [0, 0] };
  }

  // Calculate center
  const sumE = polygon.reduce((acc, p) => acc + p[0], 0);
  const sumN = polygon.reduce((acc, p) => acc + p[1], 0);
  const center: [number, number] = [sumE / polygon.length, sumN / polygon.length];

  // Normalize to center (0, 0)
  const normalized = polygon.map(p => [p[0] - center[0], p[1] - center[1]] as [number, number]);

  return { normalized, center };
}

// Helper to create building geometry from actual polygon
function createBuildingFromPolygon(polygon: [number, number][], height: number): THREE.Mesh {
  if (!polygon || polygon.length < 3) {
    // Fallback to simple box
    const geometry = new THREE.BoxGeometry(10, height, 8);
    const material = new THREE.MeshStandardMaterial({
      color: 0xe5e7eb,
      transparent: true,
      opacity: 0.7,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(0, height / 2, 0);
    return mesh;
  }

  // Create shape from polygon (E = X, N = Z in THREE.js)
  const shape = new THREE.Shape();
  shape.moveTo(polygon[0][0], polygon[0][1]);
  for (let i = 1; i < polygon.length; i++) {
    shape.lineTo(polygon[i][0], polygon[i][1]);
  }
  shape.closePath();

  // Extrude to create 3D building
  const extrudeSettings = {
    depth: height,
    bevelEnabled: false,
  };
  const geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);

  const material = new THREE.MeshStandardMaterial({
    color: 0x8b5cf6, // Purple for building
    transparent: true,
    opacity: 0.7,
  });

  const mesh = new THREE.Mesh(geometry, material);
  // Rotate so extrusion goes up (Y axis)
  mesh.rotation.x = -Math.PI / 2;

  // Center the geometry at origin (polygon centroid may not be at bbox center)
  geometry.computeBoundingBox();
  const bbox = geometry.boundingBox!;
  const centerX = (bbox.min.x + bbox.max.x) / 2;
  const centerY = (bbox.min.y + bbox.max.y) / 2;
  // After rotation: geometry X stays X, geometry Y becomes -Z
  mesh.position.set(-centerX, 0, centerY);

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  return mesh;
}

// NEU 18.01.2026: Echte 3D-Wandgeometrie aus swissBUILDINGS3D rendern
// Rendert alle Wand-Polygone mit ihren echten Z-Koordinaten
function createBuildingFrom3DWalls(
  walls: BuildingWall[],
  bboxCenter: [number, number],
  terrainZMin: number
): THREE.Group {
  const group = new THREE.Group();

  if (!walls || walls.length === 0) {
    console.log('[3D-WALLS] Keine building_walls vorhanden');
    return group;
  }

  // FIX 21.01.2026: terrainZMin wird jetzt von außen übergeben (= wallMinZ)
  // Keine interne Berechnung mehr nötig - Konsistenz mit Dach gewährleistet
  const effectiveTerrainZ = terrainZMin;

  console.log(`[3D-WALLS] Rendere ${walls.length} Wände, terrainZ=${effectiveTerrainZ.toFixed(1)}`);

  const material = new THREE.MeshStandardMaterial({
    color: 0x8b5cf6, // Purple (same as main building)
    transparent: true,
    opacity: 0.85,
    side: THREE.DoubleSide,
  });

  // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
  walls.forEach((wall, wallIndex) => {
    if (!wall.geometry) {
      console.log(`[3D-WALLS] Wall ${wallIndex}: keine geometry`);
      return;
    }

    // FIX 20.01.2026: Geometry-Format aus API erkennen
    // Das API liefert eine Liste von Polygon-Ringen (Wandflächen):
    // geometry = [[[x,y,z], ...], [[x,y,z], ...], ...]
    // Jedes Element ist ein Ring (4+ Punkte mit [x,y,z])

    const geom = wall.geometry;

    // Format-Erkennung: Prüfe Tiefe der Verschachtelung
    // Wenn geom[0][0] eine Zahl ist → Format: [[x,y,z], ...] (einzelner Ring)
    // Wenn geom[0][0] ein Array ist → Format: [[[x,y,z], ...], ...] (Liste von Ringen)
    let rings: number[][][] = [];

    if (geom.length > 0 && Array.isArray(geom[0])) {
      if (geom[0].length > 0 && typeof geom[0][0] === 'number') {
        // Format: [[x,y,z], [x,y,z], ...] - einzelner Ring
        rings = [geom as number[][]];
      } else if (geom[0].length > 0 && Array.isArray(geom[0][0])) {
        if (typeof geom[0][0][0] === 'number') {
          // Format: [[[x,y,z], ...], [[x,y,z], ...]] - Liste von Ringen (unser API-Format!)
          rings = geom as number[][][];
        } else {
          // Format: [[[[x,y,z], ...]]] - GeoJSON MultiPolygon (mit Polygon-Wrapper)
          // Flatten: Extrahiere alle Ringe aus allen Polygonen
          rings = (geom as number[][][][]).flatMap(polygon => polygon);
        }
      }
    }

    if (rings.length === 0) {
      console.log(`[3D-WALLS] Wall ${wallIndex}: Konnte geometry nicht parsen`);
      return;
    }

    if (wallIndex === 0) {
      console.log(`[3D-WALLS] Wall 0: ${rings.length} Ringe erkannt`);
    }

    rings.forEach((ring, ringIndex) => {
      if (!ring || ring.length < 3) return;

      // 3D-Vertices aus dem Ring extrahieren
      const vertices: number[] = [];
      const indices: number[] = [];

      ring.forEach((coord) => {
        // coord = [E, N, Z] in LV95
        const e = coord[0];
        const n = coord[1];
        const z = coord[2];

        // Konvertiere zu Three.js Koordinaten (relativ zum bboxCenter)
        // THREE.js: X = E-center, Y = Z-terrain, Z = -(N-center)
        const x = e - bboxCenter[0];
        const y = z - effectiveTerrainZ;  // FIX 21.01.2026: effectiveTerrainZ statt terrainZMin
        const zCoord = -(n - bboxCenter[1]);

        vertices.push(x, y, zCoord);
      });

      // Triangulation: Einfache Fan-Triangulation für konvexe Polygone
      // Für komplexe Polygone wäre earcut.js besser, aber für Wände reicht das meist
      const vertexCount = ring.length;
      for (let i = 1; i < vertexCount - 1; i++) {
        indices.push(0, i, i + 1);
      }

      // BufferGeometry erstellen
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      group.add(mesh);

      if (ringIndex === 0 && wallIndex < 3) {
        console.log(`[3D-WALLS] Wall ${wallIndex} Ring ${ringIndex}: ${vertexCount} vertices, z_min=${wall.z_min?.toFixed(1)}, z_max=${wall.z_max?.toFixed(1)}`);
      }
    });
  });

  console.log(`[3D-WALLS] ${group.children.length} Meshes erstellt`);
  return group;
}

// Zone colors based on zone type
const ZONE_COLORS: Record<string, number> = {
  hauptgebaeude: 0x8b5cf6,  // Purple (same as main building)
  anbau: 0x6366f1,          // Indigo
  turm: 0xf59e0b,           // Amber
  kuppel: 0x10b981,         // Emerald
  arkade: 0x06b6d4,         // Cyan
  vordach: 0x84cc16,        // Lime
  treppenhaus: 0xf97316,    // Orange
  garage: 0x6b7280,         // Gray
};

// Helper to create zone geometry based on zone type and position
function createZoneGeometry(
  zone: BuildingZone,
  _polygon: [number, number][],  // Reserved for future polygon-based zone placement
  mainBuildingHeight: number,
  polygonBbox: { minX: number; maxX: number; minY: number; maxY: number }
): THREE.Group {
  void _polygon; // Reserved for future use
  const group = new THREE.Group();
  group.name = `zone-${zone.id}`;

  const zoneHeight = zone.firsthoehe_m || zone.traufhoehe_m || mainBuildingHeight;
  const color = ZONE_COLORS[zone.zone_type] || 0x8b5cf6;

  // Calculate building dimensions from bbox
  const buildingWidth = polygonBbox.maxX - polygonBbox.minX;
  const buildingDepth = polygonBbox.maxY - polygonBbox.minY;

  // Position offset based on zone position
  let offsetX = 0;
  let offsetZ = 0;
  const positionOffset = Math.max(buildingWidth, buildingDepth) * 0.15; // 15% of building size

  switch (zone.position) {
    case 'vorne':
      offsetZ = positionOffset; // South in THREE.js (front)
      break;
    case 'hinten':
      offsetZ = -positionOffset; // North in THREE.js (back)
      break;
    case 'flankierend':
      offsetX = positionOffset; // Side
      break;
    case 'zentral':
    default:
      // No offset - centered
      break;
  }

  // Create geometry based on zone type
  let mesh: THREE.Mesh;

  if (zone.zone_type === 'turm') {
    // Tower: Cylinder or tall box
    const towerRadius = Math.min(buildingWidth, buildingDepth) * 0.1;
    const geometry = new THREE.CylinderGeometry(towerRadius, towerRadius, zoneHeight, 16);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.8,
    });
    mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(offsetX, zoneHeight / 2, offsetZ);

  } else if (zone.zone_type === 'kuppel') {
    // Dome: Sphere (half)
    const domeRadius = Math.min(buildingWidth, buildingDepth) * 0.2;
    const geometry = new THREE.SphereGeometry(domeRadius, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.8,
    });
    mesh = new THREE.Mesh(geometry, material);
    // Position dome on top of main building
    mesh.position.set(offsetX, mainBuildingHeight, offsetZ);

  } else if (zone.zone_type === 'arkade') {
    // Arcade: Low flat box with columns
    const arcadeHeight = Math.min(zoneHeight, 6);
    const arcadeWidth = buildingWidth * 0.8;
    const arcadeDepth = buildingDepth * 0.3;
    const geometry = new THREE.BoxGeometry(arcadeWidth, arcadeHeight, arcadeDepth);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.6,
    });
    mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(offsetX, arcadeHeight / 2, offsetZ + buildingDepth * 0.35);

  } else if (zone.zone_type === 'anbau' || zone.zone_type === 'garage') {
    // Extension/Garage: Box offset to the side
    const extWidth = buildingWidth * 0.4;
    const extDepth = buildingDepth * 0.5;
    const extHeight = zoneHeight;
    const geometry = new THREE.BoxGeometry(extWidth, extHeight, extDepth);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.7,
    });
    mesh = new THREE.Mesh(geometry, material);
    // Position to the side of the main building
    const sideOffset = (buildingWidth + extWidth) / 2 + 1;
    mesh.position.set(zone.position === 'flankierend' ? sideOffset : offsetX, extHeight / 2, offsetZ);

  } else {
    // Default: Box at zone height (for hauptgebaeude or unknown types)
    // Skip if this is the main building (already rendered)
    if (zone.zone_type === 'hauptgebaeude') {
      return group; // Return empty group - main building already rendered
    }
    const geometry = new THREE.BoxGeometry(buildingWidth * 0.3, zoneHeight, buildingDepth * 0.3);
    const material = new THREE.MeshStandardMaterial({
      color,
      transparent: true,
      opacity: 0.7,
    });
    mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(offsetX, zoneHeight / 2, offsetZ);
  }

  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.name = zone.name;

  // Add label sprite for zone name
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d')!;
  canvas.width = 256;
  canvas.height = 64;
  context.fillStyle = '#333';
  context.font = 'bold 24px Arial';
  context.textAlign = 'center';
  context.fillText(zone.name, 128, 40);

  const texture = new THREE.CanvasTexture(canvas);
  const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.scale.set(8, 2, 1);
  sprite.position.set(mesh.position.x, mesh.position.y + zoneHeight / 2 + 2, mesh.position.z);

  group.add(mesh);
  group.add(sprite);

  return group;
}

// Helper to create building geometry (fallback for no polygon)
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

// Helper to create roof geometry that follows the actual polygon shape
// Supports different roof types: flachdach, satteldach, walmdach/zeltdach, pultdach
function createRoofFromPolygon(
  normalized: [number, number][],
  buildingHeight: number,
  roofHeight: number,
  roofType: string = 'walmdach',  // Default to hip roof
  roofOrientation: string = '',   // 'N-S' or 'O-W' for ridge direction
  roofOverhang: number = 0.4      // Dachüberstand in Metern (Standard: 40cm)
): THREE.Group {
  const group = new THREE.Group();

  if (!normalized || normalized.length < 3) {
    return group;
  }

  // FIX 11.01.2026 19:20 - Dach-Alignment: Nur BBox-Drift durch Skalierung korrigieren
  // Problem: Die radiale Skalierung für den Dachüberstand ist NICHT uniform.
  // Das verschiebt die BBox-Mitte, obwohl die Punkte ursprünglich zentriert waren.
  //
  // Lösung: Die Verschiebung der BBox-Mitte durch Skalierung berechnen und mit
  // group.position kompensieren. Die Punkt-Transformation bleibt wie im Original.

  // Step 1: Calculate bounding box center of original polygon
  const minX = Math.min(...normalized.map(p => p[0]));
  const maxX = Math.max(...normalized.map(p => p[0]));
  const minY = Math.min(...normalized.map(p => p[1]));
  const maxY = Math.max(...normalized.map(p => p[1]));
  const bboxCenterX = (minX + maxX) / 2;
  const bboxCenterY = (minY + maxY) / 2;

  // Step 2: Transform points (wie Original) - zentriert zur BBox-Mitte + Überhang
  const centeredPoints = normalized.map(p => {
    const dx = p[0] - bboxCenterX;
    const dy = p[1] - bboxCenterY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const scale = dist > 0 ? (dist + roofOverhang) / dist : 1;
    return {
      x: dx * scale,
      z: -(dy * scale),  // Negate for THREE.js coordinate system
    };
  });

  // Step 3: Calculate how much the BBox center shifted due to non-uniform scaling
  // Original BBox center (vor Skalierung): (0, 0) da wir zur BBox-Mitte zentriert haben
  // Neue BBox center (nach Skalierung): muss neu berechnet werden
  const scaledMinX = Math.min(...centeredPoints.map(p => p.x));
  const scaledMaxX = Math.max(...centeredPoints.map(p => p.x));
  const scaledMinZ = Math.min(...centeredPoints.map(p => p.z));
  const scaledMaxZ = Math.max(...centeredPoints.map(p => p.z));
  const scaledBboxCenterX = (scaledMinX + scaledMaxX) / 2;
  const scaledBboxCenterZ = (scaledMinZ + scaledMaxZ) / 2;

  // Step 4: Kompensiere die BBox-Drift mit group.position
  // Das Dach soll bei (0, 0, 0) zentriert bleiben wie das Gebäude
  group.position.set(-scaledBboxCenterX, 0, -scaledBboxCenterZ);

  // Y positions in THREE.js (Y is up)
  const yEaves = buildingHeight;  // Traufe
  const yPeak = buildingHeight + roofHeight;  // First/Spitze

  const roofMaterial = new THREE.MeshStandardMaterial({
    color: 0x8b5cf6,
    side: THREE.DoubleSide,
  });

  // Different roof geometries based on type
  if (roofType === 'flachdach') {
    // Flat roof - just a plane at building height
    const shape = new THREE.Shape();
    shape.moveTo(centeredPoints[0].x, centeredPoints[0].z);
    for (let i = 1; i < centeredPoints.length; i++) {
      shape.lineTo(centeredPoints[i].x, centeredPoints[i].z);
    }
    shape.closePath();

    const geometry = new THREE.ShapeGeometry(shape);
    const mesh = new THREE.Mesh(geometry, roofMaterial);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = yEaves + 0.1; // Slightly above building
    group.add(mesh);

  } else if (roofType === 'satteldach') {
    // Classic gable roof (Satteldach) - use tested utility function
    const roofGeom = createSatteldachGeometry(
      centeredPoints as Point2D[],
      yEaves,
      yPeak,
      roofOrientation
    );

    // Create roof mesh from geometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(roofGeom.vertices), 3));
    geometry.setIndex(roofGeom.indices);
    geometry.computeVertexNormals();

    const mesh = new THREE.Mesh(geometry, roofMaterial);
    group.add(mesh);

  } else if (roofType === 'pultdach') {
    // Shed roof following actual polygon shape - single slope
    // Low edge at positive Z (front/south), high edge at negative Z (back/north)
    const vertices: number[] = [];
    const indices: number[] = [];

    // Separate points into front (low) and back (high) based on Z position
    const zMin = Math.min(...centeredPoints.map(p => p.z));
    const zMax = Math.max(...centeredPoints.map(p => p.z));

    // Create roof surface - each point's height depends on its Z position
    // Front (positive Z) = yEaves, Back (negative Z) = yPeak
    centeredPoints.forEach(p => {
      // Interpolate height based on Z position
      const t = (p.z - zMin) / (zMax - zMin); // 0 = back (high), 1 = front (low)
      const y = yPeak + t * (yEaves - yPeak);
      vertices.push(p.x, y, p.z);
    });

    // Create roof surface using triangulation from centroid
    // Add centroid vertex at interpolated height
    const centroidX = centeredPoints.reduce((sum, p) => sum + p.x, 0) / centeredPoints.length;
    const centroidZ = centeredPoints.reduce((sum, p) => sum + p.z, 0) / centeredPoints.length;
    const centroidT = (centroidZ - zMin) / (zMax - zMin);
    const centroidY = yPeak + centroidT * (yEaves - yPeak);
    const centroidIdx = centeredPoints.length;
    vertices.push(centroidX, centroidY, centroidZ);

    // Create triangular faces from each edge to centroid
    for (let i = 0; i < centeredPoints.length; i++) {
      const nextI = (i + 1) % centeredPoints.length;
      indices.push(i, nextI, centroidIdx);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vertices), 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    const mesh = new THREE.Mesh(geometry, roofMaterial);
    mesh.castShadow = true;
    group.add(mesh);

  } else {
    // Default: walmdach/zeltdach - hip/pyramid roof (original implementation)
    // All edges slope up to center point
    const vertices: number[] = [];
    const indices: number[] = [];

    // Add eave vertices (at polygon corners)
    centeredPoints.forEach(p => {
      vertices.push(p.x, yEaves, p.z);
    });

    // Add peak vertex (last vertex)
    const peakIndex = centeredPoints.length;
    vertices.push(0, yPeak, 0);  // Peak at center

    // Create triangular roof faces from each edge to the peak
    for (let i = 0; i < centeredPoints.length; i++) {
      const nextI = (i + 1) % centeredPoints.length;
      indices.push(i, nextI, peakIndex);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vertices), 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    const mesh = new THREE.Mesh(geometry, roofMaterial);
    mesh.castShadow = true;
    group.add(mesh);
  }

  return group;
}

// NEU 14.01.2026: Echte 3D-Dachgeometrie aus swissBUILDINGS3D
// Rendert die tatsächliche Dachform basierend auf den importierten 3D-Koordinaten
//
// Y-Berechnung: y = yOffset + (z - zReference)
// - Bei 3D-Wänden: zReference=terrainZ, yOffset=0 → y = z - terrainZ (konsistent mit Wänden)
// - Bei 2D-Extrusion: zReference=roofDachMin, yOffset=buildingHeight → Dach ab Traufe
function createRoofFrom3DGeometry(
  roofCoords: number[][][],  // Array von Polygonen: [[[E, N, Z], ...], ...]
  centerE: number,           // Gebäude-Zentrum E (LV95)
  centerN: number,           // Gebäude-Zentrum N (LV95)
  zReference: number,        // Z-Referenz: terrainZ (3D-Wände) oder roofDachMin (2D-Extrusion)
  yOffset: number            // Y-Offset: 0 (3D-Wände) oder buildingHeight (2D-Extrusion)
): THREE.Group {
  const group = new THREE.Group();

  if (!roofCoords || roofCoords.length === 0) {
    console.warn('[3D-ROOF] Keine Dach-Koordinaten vorhanden');
    return group;
  }

  const roofMaterial = new THREE.MeshStandardMaterial({
    color: 0x8b5cf6,  // Violett wie das heuristische Dach
    side: THREE.DoubleSide,
  });

  // Transformiere jedes Polygon (Dreieck/Fläche)
  roofCoords.forEach((polygon) => {
    if (polygon.length < 3) return;

    // Transformiere Koordinaten von LV95 zu lokalen Three.js Koordinaten
    // X = E - centerE
    // Z = -(N - centerN)  [negiert für Three.js Koordinatensystem]
    // Y = yOffset + (Z_abs - zReference)
    //   - Bei 3D-Wänden: yOffset=0, zReference=terrainZ → y = z - terrainZ
    //   - Bei 2D-Extrusion: yOffset=buildingHeight, zReference=roofDachMin → y = buildingHeight + (z - roofDachMin)
    const transformedPoints = polygon.map(point => {
      const [e, n, z] = point;
      return {
        x: e - centerE,
        y: yOffset + (z - zReference),  // FIX 01.02.2026: Parametrisiert für beide Fälle
        z: -(n - centerN),  // Negiert für Three.js
      };
    });

    // Erstelle BufferGeometry für dieses Polygon
    if (polygon.length === 4) {
      // Dreieck (4 Punkte = 3 Eckpunkte + 1 Schlusspunkt)
      // Verwende nur die ersten 3 Punkte
      const vertices = new Float32Array([
        transformedPoints[0].x, transformedPoints[0].y, transformedPoints[0].z,
        transformedPoints[1].x, transformedPoints[1].y, transformedPoints[1].z,
        transformedPoints[2].x, transformedPoints[2].y, transformedPoints[2].z,
      ]);

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
      geometry.setIndex([0, 1, 2]);  // Ein Dreieck
      geometry.computeVertexNormals();

      const mesh = new THREE.Mesh(geometry, roofMaterial);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);
    } else if (polygon.length === 5) {
      // Quadrilateral (5 Punkte = 4 Eckpunkte + 1 Schlusspunkt)
      // Teile in 2 Dreiecke: [0,1,2] und [0,2,3]
      const vertices = new Float32Array([
        transformedPoints[0].x, transformedPoints[0].y, transformedPoints[0].z,
        transformedPoints[1].x, transformedPoints[1].y, transformedPoints[1].z,
        transformedPoints[2].x, transformedPoints[2].y, transformedPoints[2].z,
        transformedPoints[3].x, transformedPoints[3].y, transformedPoints[3].z,
      ]);

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
      geometry.setIndex([0, 1, 2, 0, 2, 3]);  // Zwei Dreiecke
      geometry.computeVertexNormals();

      const mesh = new THREE.Mesh(geometry, roofMaterial);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);
    } else {
      // FIX 16.01.2026: Komplexere Polygone mit Fan-Triangulation
      // ShapeGeometry war FALSCH - es flacht alle Y-Werte ab!
      // Stattdessen: BufferGeometry mit korrekten 3D-Koordinaten
      const numVertices = transformedPoints.length - 1;  // Letzter Punkt = Schlusspunkt
      const vertices = new Float32Array(numVertices * 3);

      for (let i = 0; i < numVertices; i++) {
        vertices[i * 3] = transformedPoints[i].x;
        vertices[i * 3 + 1] = transformedPoints[i].y;
        vertices[i * 3 + 2] = transformedPoints[i].z;
      }

      // Fan-Triangulation: Alle Dreiecke vom Zentrum (Punkt 0) ausgehend
      const indices: number[] = [];
      for (let i = 1; i < numVertices - 1; i++) {
        indices.push(0, i, i + 1);
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      const mesh = new THREE.Mesh(geometry, roofMaterial);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);
    }
  });

  console.log(`[3D-ROOF] Echte Dachgeometrie gerendert: ${roofCoords.length} Polygone`);
  return group;
}

// Legacy helper to create roof geometry (for fallback box-based buildings)
function createRoof(
  width: number,
  depth: number,
  roofHeight: number,
  buildingHeight: number
): THREE.Group {
  const group = new THREE.Group();

  // Create vertices directly in 3D space for the roof
  const y0 = buildingHeight;
  const yTop = buildingHeight + roofHeight;
  const halfW = width / 2;
  const halfD = depth / 2;

  const vertices = new Float32Array([
    // Front gable
    -halfW, y0, halfD,    // 0
    halfW, y0, halfD,     // 1
    0, yTop, halfD,       // 2

    // Back gable
    -halfW, y0, -halfD,   // 3
    halfW, y0, -halfD,    // 4
    0, yTop, -halfD,      // 5
  ]);

  const indices = [
    0, 2, 1,  // Front gable
    3, 4, 5,  // Back gable
    0, 3, 5, 0, 5, 2,  // Left slope
    1, 2, 5, 1, 5, 4,  // Right slope
  ];

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  const material = new THREE.MeshStandardMaterial({
    color: 0x8b5cf6,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(geometry, material);
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

// Helper to create scaffold facade along actual edge coordinates
// NEU 19.01.2026: Unterstützt originalSegments für exakte 3D-Platzierung entlang Original-Polygon
// FIX 07.02.2026: Unterstützt gemischte Rahmenhöhen (frameHeights) und Feldbreiten (fieldWidths)
function createScaffoldFacadeAlongEdge(
  facade: ScaffoldFacade,
  fieldWidth: number,
  levelHeight: number,
  center: [number, number],
  scaffoldGap: number = 0.5
): THREE.Group {
  const group = new THREE.Group();
  const cellDepth = 0.73;
  const colorHex = parseInt((facade.color || '#6B7280').replace('#', ''), 16);

  // FIX 07.02.2026: Berechne kumulative Höhen für gemischte Rahmenhöhen
  // Wenn frameHeights verfügbar, benutze diese; sonst Fallback auf gleichmäßige Höhe
  const frameHeights = facade.frameHeights || Array(facade.levels).fill(levelHeight);
  const cumulativeHeights: number[] = [0];
  for (let i = 0; i < frameHeights.length; i++) {
    cumulativeHeights.push(cumulativeHeights[i] + frameHeights[i]);
  }

  // FIX 07.02.2026: Berechne kumulative Breiten für gemischte Feldbreiten
  const fieldWidths = facade.fieldWidths || Array(facade.fields).fill(fieldWidth);
  const cumulativeWidths: number[] = [0];
  for (let i = 0; i < fieldWidths.length; i++) {
    cumulativeWidths.push(cumulativeWidths[i] + fieldWidths[i]);
  }

  // NEU 19.01.2026: Verwende originalSegments wenn vorhanden (für exakte 3D-Platzierung)
  // FIX 08.02.2026: Komplett neu geschrieben - kontinuierliche Positionierung statt segment-basiert
  if (facade.originalSegments && facade.originalSegments.length > 0) {
    // Berechne Gesamtlänge und kumulative Längen aller Segmente
    let totalLength = 0;
    const segmentLengths: number[] = [];
    const cumulativeSegmentLengths: number[] = [0];

    facade.originalSegments.forEach(seg => {
      const dx = seg.end[0] - seg.start[0];
      const dy = seg.end[1] - seg.start[1];
      const len = Math.sqrt(dx * dx + dy * dy);
      segmentLengths.push(len);
      totalLength += len;
      cumulativeSegmentLengths.push(totalLength);
    });

    // Berechne kumulative Feldpositionen (Mitte jedes Feldes)
    const fieldCenters: number[] = [];
    let pos = 0;
    for (let f = 0; f < facade.fields; f++) {
      const fieldW = fieldWidths[f] || fieldWidth;
      fieldCenters.push(pos + fieldW / 2);
      pos += fieldW;
    }

    // Für jedes Feld: finde das passende Segment und platziere dort
    for (let field = 0; field < facade.fields; field++) {
      const fieldCenter = fieldCenters[field];

      // Finde welches Segment diese Position enthält
      let segIdx = 0;
      for (let i = 0; i < segmentLengths.length; i++) {
        if (fieldCenter >= cumulativeSegmentLengths[i] && fieldCenter < cumulativeSegmentLengths[i + 1]) {
          segIdx = i;
          break;
        }
        // Letztes Segment für Positionen am Ende
        if (i === segmentLengths.length - 1) {
          segIdx = i;
        }
      }

      const seg = facade.originalSegments[segIdx];
      const segLength = segmentLengths[segIdx];
      const segStart = cumulativeSegmentLengths[segIdx];

      // Position relativ zum Segment (0 bis 1)
      const t = segLength > 0 ? Math.min(1, Math.max(0, (fieldCenter - segStart) / segLength)) : 0.5;

      // FIX 08.02.2026: KEIN swap mehr - verwende Koordinaten direkt
      // Polygon läuft gegen Uhrzeigersinn, Gerüst soll nach außen (rechts der Laufrichtung)
      const segStartX = seg.start[0] - center[0];
      const segStartZ = -(seg.start[1] - center[1]);
      const segEndX = seg.end[0] - center[0];
      const segEndZ = -(seg.end[1] - center[1]);

      // Berechne Richtung für dieses Segment
      const dx = segEndX - segStartX;
      const dz = segEndZ - segStartZ;
      const length = Math.sqrt(dx * dx + dz * dz);
      if (length < 0.01) continue; // Skip sehr kurze Segmente

      const dirX = dx / length;
      const dirZ = dz / length;

      // FIX 08.02.2026: Perpendicular nach RECHTS der Laufrichtung (= nach außen bei CCW Polygon)
      // Rechts von (dirX, dirZ) ist (dirZ, -dirX)
      const perpX = dirZ;
      const perpZ = -dirX;
      const offsetX = perpX * (scaffoldGap + cellDepth / 2);
      const offsetZ = perpZ * (scaffoldGap + cellDepth / 2);

      // Position auf dem Segment
      const baseX = segStartX + dx * t;
      const baseZ = segStartZ + dz * t;

      // Erstelle Gerüst-Zellen für alle Level dieses Feldes
      for (let level = 0; level < facade.levels; level++) {
        const key = `${field}-${level}`;
        if (facade.modifications.removed_cells.has(key)) continue;

        const frameH = frameHeights[level] || levelHeight;
        const cellY = cumulativeHeights[level] + frameH / 2;

        const fieldW = fieldWidths[field] || fieldWidth;
        const cellWidth = fieldW * 0.95;
        const cellHeight = frameH * 0.95;

        let cellColor = colorHex;
        if (facade.modifications.lift_position === field) {
          cellColor = 0xfef3c7;
        } else if (facade.modifications.stairs_position === field) {
          cellColor = 0xdcfce7;
        }

        const cellGroup = new THREE.Group();
        const geometry = new THREE.BoxGeometry(cellWidth, cellHeight, cellDepth);
        const material = new THREE.MeshStandardMaterial({
          color: cellColor,
          transparent: true,
          opacity: 0.8,
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.castShadow = true;

        cellGroup.add(mesh);
        cellGroup.position.set(baseX + offsetX, cellY, baseZ + offsetZ);

        // Rotation: Zelle soll parallel zur Fassade stehen
        const angle = Math.atan2(dz, dx);
        cellGroup.rotation.y = -angle;
        group.add(cellGroup);
      }
    }

    console.log(`[3D-SCAFFOLD] Fassade ${facade.direction}: ${facade.originalSegments.length} Segmente, ${facade.fields} Felder (kontinuierlich)`);
    return group;
  }

  // Fallback: Verwende start_point/end_point (vereinfachtes Polygon)
  // Check if we have actual coordinates
  if (!facade.start_point || !facade.end_point) {
    // Fallback: no positioning (shouldn't happen)
    return group;
  }

  // FIX 08.02.2026: Kein swap mehr - verwende Koordinaten direkt (konsistent mit originalSegments Pfad)
  const startX = facade.start_point[0] - center[0];
  const startZ = -(facade.start_point[1] - center[1]);
  const endX = facade.end_point[0] - center[0];
  const endZ = -(facade.end_point[1] - center[1]);

  // Calculate facade direction vector
  const dx = endX - startX;
  const dz = endZ - startZ;
  const length = Math.sqrt(dx * dx + dz * dz);

  // Normalize direction
  const dirX = dx / length;
  const dirZ = dz / length;

  // FIX 08.02.2026: Perpendicular nach RECHTS der Laufrichtung (= nach außen bei CCW Polygon)
  // Rechts von (dirX, dirZ) ist (dirZ, -dirX)
  const perpX = dirZ;
  const perpZ = -dirX;

  // Offset scaffolds outward from building edge
  const offsetX = perpX * (scaffoldGap + cellDepth / 2);
  const offsetZ = perpZ * (scaffoldGap + cellDepth / 2);

  // Inset scaffolds slightly at corners to avoid overlap (half cell width on each end)
  const cornerInset = 0.5 / facade.fields; // ~half a cell at each end

  // FIX 07.02.2026: Verwende gemischte Rahmenhöhen und Feldbreiten (Fallback-Pfad)
  for (let level = 0; level < facade.levels; level++) {
    // Berechne tatsächliche Höhe und Position für diesen Rahmen
    const frameH = frameHeights[level] || levelHeight;
    const cellY = cumulativeHeights[level] + frameH / 2;

    for (let field = 0; field < facade.fields; field++) {
      const key = `${field}-${level}`;
      if (facade.modifications.removed_cells.has(key)) continue;

      // Position along the facade edge (with corner inset to avoid overlap)
      const tRaw = (field + 0.5) / facade.fields; // 0 to 1 along the edge
      const t = cornerInset + tRaw * (1 - 2 * cornerInset); // Shrink range to avoid corners
      const cellX = startX + dx * t + offsetX;
      const cellZ = startZ + dz * t + offsetZ;

      // FIX 07.02.2026: Verwende gemischte Feldbreite
      const fieldW = fieldWidths[field] || fieldWidth;
      const cellWidth = fieldW * 0.95;
      const cellHeight = frameH * 0.95;

      // Check if this is a lift or stairs column
      let cellColor = colorHex;
      if (facade.modifications.lift_position === field) {
        cellColor = 0xfef3c7; // Yellow tint for lift
      } else if (facade.modifications.stairs_position === field) {
        cellColor = 0xdcfce7; // Green tint for stairs
      }

      // Create cell geometry rotated to align with facade
      const cellGroup = new THREE.Group();
      const geometry = new THREE.BoxGeometry(cellWidth, cellHeight, cellDepth);
      const material = new THREE.MeshStandardMaterial({
        color: cellColor,
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

      cellGroup.add(mesh);
      cellGroup.add(line);

      // Position and rotate to align with facade
      cellGroup.position.set(cellX, cellY, cellZ);
      // Rotate cell so its width aligns with facade direction
      // atan2(dirZ, dirX) gives angle from X-axis to direction vector
      const angle = Math.atan2(dirZ, dirX);
      cellGroup.rotation.y = -angle;  // Negative because Y rotation is clockwise

      group.add(cellGroup);
    }
  }

  return group;
}

// NOTE 19.01.2026: createScaffoldForMultiBuilding wurde entfernt nach Objekt-Architektur Refactoring
// Mit der neuen Architektur ist das Haupt-Polygon die Union aller Gebäude.
// Gerüste werden nur für die Fassaden des Union-Polygons gerendert (enabledFacades).
// Falls wieder benötigt für separate Gebäude: Siehe Git-History.

// Helper to create scaffold facade (legacy - fallback)
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

// Note: createAccessMarker was removed as it's not used in the new polygon-based approach
// It can be re-added later if needed for lift/stairs visualization

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

// Helper to create scaffold corner at intersection of two facades
function createScaffoldCorner(
  corner: ScaffoldCorner,
  facades: ScaffoldFacade[],
  levelHeight: number,
  center: [number, number],
  scaffoldGap: number = 0.5
): THREE.Group | null {
  if (!corner.enabled) return null;

  const group = new THREE.Group();
  const cornerColor = 0xf59e0b; // Amber for corners
  const cellDepth = 0.73;

  // Find the two connected facades
  const facade1 = facades.find(f => f.id === corner.connects[0]);
  const facade2 = facades.find(f => f.id === corner.connects[1]);

  if (!facade1 || !facade2) return null;
  if (!facade1.end_point || !facade2.start_point) return null;

  // Corner position is at facade1's end (which should be facade2's start)
  const cornerX = facade1.end_point[0] - center[0];
  const cornerZ = -(facade1.end_point[1] - center[1]);

  // Calculate outward direction from building center (0,0) to corner
  const distFromCenter = Math.sqrt(cornerX * cornerX + cornerZ * cornerZ);
  const outwardX = distFromCenter > 0 ? cornerX / distFromCenter : 1;
  const outwardZ = distFromCenter > 0 ? cornerZ / distFromCenter : 0;

  // Offset corner outward (same as facades: scaffoldGap + cellDepth/2)
  const offset = scaffoldGap + cellDepth / 2;
  const offsetCornerX = cornerX + outwardX * offset;
  const offsetCornerZ = cornerZ + outwardZ * offset;

  // Get number of levels from connected facades
  const levels = Math.max(facade1.levels, facade2.levels);

  // FIX 07.02.2026: Berechne tatsächliche Höhe aus gemischten Rahmenhöhen
  // Verwende die höhere Fassade für die Eckhöhe
  const facade1Height = facade1.actualHeight ?? (facade1.levels * levelHeight);
  const facade2Height = facade2.actualHeight ?? (facade2.levels * levelHeight);
  const actualCornerHeight = Math.max(facade1Height, facade2Height);

  // Wähle die Fassade mit der größeren Höhe für die Ebenen-Positionen
  const mainFacade = facade1Height >= facade2Height ? facade1 : facade2;
  const frameHeights = mainFacade.frameHeights || Array(levels).fill(levelHeight);
  const cumulativeHeights: number[] = [0];
  for (let i = 0; i < frameHeights.length; i++) {
    cumulativeHeights.push(cumulativeHeights[i] + frameHeights[i]);
  }

  // Create corner posts (vertical cylinders at corner)
  const postRadius = 0.05;
  const postHeight = actualCornerHeight;
  const postGeometry = new THREE.CylinderGeometry(postRadius, postRadius, postHeight, 8);
  const postMaterial = new THREE.MeshStandardMaterial({ color: cornerColor });

  // Position posts around the offset corner position
  const postSpread = 0.3;
  const postPositions = [
    { x: offsetCornerX + postSpread, z: offsetCornerZ + postSpread },
    { x: offsetCornerX + postSpread, z: offsetCornerZ - postSpread },
    { x: offsetCornerX - postSpread, z: offsetCornerZ + postSpread },
    { x: offsetCornerX - postSpread, z: offsetCornerZ - postSpread },
  ];

  postPositions.slice(0, corner.corner_posts).forEach(pos => {
    const post = new THREE.Mesh(postGeometry, postMaterial);
    post.position.set(pos.x, postHeight / 2, pos.z);
    group.add(post);
  });

  // Add diagonal bracing between posts
  // FIX 07.02.2026: Verwende tatsächliche Höhen für Diagonal-Positionen
  if (corner.diagonals > 0) {
    const diagMaterial = new THREE.LineBasicMaterial({ color: cornerColor });
    for (let level = 0; level < levels; level++) {
      const frameH = frameHeights[level] || levelHeight;
      const y = cumulativeHeights[level] + frameH / 2;
      const points = [
        new THREE.Vector3(offsetCornerX + postSpread, y, offsetCornerZ + postSpread),
        new THREE.Vector3(offsetCornerX - postSpread, y, offsetCornerZ - postSpread),
      ];
      const diagGeometry = new THREE.BufferGeometry().setFromPoints(points);
      const diag = new THREE.Line(diagGeometry, diagMaterial);
      group.add(diag);
    }
  }

  return group;
}

// Main component
export default function ScaffoldScene({
  configuration,
  activeView,
  neighbors = [],
  blockedSides = [],
  objectData,
  zones = [],
  complexity = 'simple',
  buildingWalls = [],
}: ScaffoldSceneProps) {
  // Log neighbors for debugging (will be used for rendering in Phase 2.3)
  if (neighbors.length > 0) {
    console.log(`ScaffoldScene: ${neighbors.length} neighbors, blocked sides: ${blockedSides.join(', ')}`);
  }
  // NEU 19.01.2026: Objekt-Architektur - projectBuildings sind nur Metadaten
  if (objectData?.projectBuildings && objectData.projectBuildings.length > 1) {
    console.log(`ScaffoldScene: Multi-building object with ${objectData.projectBuildings.length} buildings (polygon is UNION)`);
  }
  // Log zones for complex buildings
  if (zones.length > 0) {
    console.log(`ScaffoldScene: ${zones.length} zones, complexity: ${complexity}`);
    zones.forEach(z => console.log(`  - ${z.name}: type=${z.zone_type}, position=${z.position || 'default'}, trauf=${z.traufhoehe_m}m`));
  }
  const containerRef = useRef<HTMLDivElement>(null);
  const componentsRef = useRef<OBC.Components | null>(null);
  const worldRef = useRef<OBC.SimpleWorld<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track content objects for cleanup
  const contentGroupRef = useRef<THREE.Group | null>(null);

  // Initialize scene (only once)
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

        // FIX 14.01.2026 17:30 - Camera controls aktivieren für Zoom/Rotation
        // SimpleCamera verwendet yomotsu's camera-controls
        // Zoom funktioniert über DOLLY (Mausrad) - muss explizit enabled sein
        world.camera.controls.enabled = true;

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

        // Create content group for building/scaffolds (will be updated separately)
        const contentGroup = new THREE.Group();
        contentGroup.name = 'scene-content';
        contentGroupRef.current = contentGroup;
        world.scene.three.add(contentGroup);

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
  }, []);  // Initial scene setup - only once

  // Update scene content when configuration, neighbors, or objectData change
  useEffect(() => {
    const contentGroup = contentGroupRef.current;
    if (!contentGroup || !worldRef.current?.scene?.three) return;

    // Clear previous content
    while (contentGroup.children.length > 0) {
      const child = contentGroup.children[0];
      contentGroup.remove(child);
      // Dispose geometry and materials
      if (child instanceof THREE.Mesh) {
        child.geometry?.dispose();
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose());
        } else {
          child.material?.dispose();
        }
      }
    }

    // Add new content
    // NEU 19.01.2026: objectData statt additionalBuildings (polygon ist bereits Union)
    addSceneContent(contentGroup, configuration, neighbors, objectData, zones, complexity);

    // Scene update log (minimiert)
    // DEBUG 21.01.2026: Detailliertes Logging für 3D-Walls-Problem
    const wallsWithGeometry = buildingWalls.filter(w => w.geometry && w.geometry.length > 0);
    console.log('[ScaffoldScene] Scene content updated:', {
      neighbors: neighbors.length,
      facades: configuration.elements.filter(e => e.type === 'facade' && e.enabled).length,
      buildingWalls: buildingWalls.length,
      wallsWithGeometry: wallsWithGeometry.length,
    });
    if (buildingWalls.length > 0 && wallsWithGeometry.length === 0) {
      console.log('[ScaffoldScene] DEBUG: Erste Wall OHNE geometry:', buildingWalls[0]);
    }
  // FIX 20.01.2026 BUG: buildingWalls fehlte im dependency array!
  // Ohne buildingWalls wird useEffect nicht getriggert wenn 3D-Wände geladen werden
  }, [configuration, neighbors, objectData, zones, complexity, buildingWalls]);

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

  // Add scene content (works with Scene or Group)
  // NEU 19.01.2026: objectData statt multiBuildingData (Objekt-Architektur)
  function addSceneContent(
    parent: THREE.Object3D,
    config: ScaffoldConfiguration,
    neighborBuildings: NeighborBuilding[] = [],
    objectData: ObjectData | undefined,
    buildingZones: BuildingZone[] = [],
    buildingComplexity: 'simple' | 'moderate' | 'complex' = 'simple'
  ) {
    const allFacades = config.elements.filter((el): el is ScaffoldFacade => el.type === 'facade');
    const enabledFacades = allFacades.filter(f => f.enabled);
    const corners = config.elements.filter((el): el is ScaffoldCorner => el.type === 'corner');
    const fieldWidth = config.settings.field_width_m;
    const levelHeight = config.settings.level_height_m;

    // Building polygon is now always the ORIGINAL from swissBUILDINGS3D
    const polygon3D = config.buildingPolygon;
    const hasPolygon = polygon3D && polygon3D.length >= 3;

    // DEBUG: Log polygon info
    console.log('=== 3D POLYGON DEBUG ===', {
      polygonPoints: polygon3D?.length || 0,
    });

    if (hasPolygon) {
      // Use actual polygon for building visualization (always if available)
      // Use original polygon for building 3D mesh (more detail)
      const { normalized } = normalizePolygon(polygon3D!);

      // Calculate bounding box center (may differ from centroid)
      // This must match the building's centering logic
      const minX = Math.min(...polygon3D!.map(p => p[0]));
      const maxX = Math.max(...polygon3D!.map(p => p[0]));
      const minY = Math.min(...polygon3D!.map(p => p[1]));
      const maxY = Math.max(...polygon3D!.map(p => p[1]));
      const bboxCenter: [number, number] = [(minX + maxX) / 2, (minY + maxY) / 2];

      // NEU 14.01.2026 13:35: Echte 3D-Dachgeometrie IMMER priorisieren, unabhängig von Komplexität
      // FIX 21.01.2026: roof_dach_min_m ist OPTIONAL - Geometrie kann auch ohne gerendert werden
      const hasReal3DGeometry = config.roof?.has_roof_geometry &&
                                 config.roof?.roof_geometry_coords &&
                                 config.roof.roof_geometry_coords.length > 0;

      console.log('[3D-ROOF] hasReal3DGeometry Check:', {
        has_roof_geometry: config.roof?.has_roof_geometry,
        roof_geometry_coords_length: config.roof?.roof_geometry_coords?.length,
        roof_dach_min_m: config.roof?.roof_dach_min_m,
        terrain_z_min: config.roof?.terrain_z_min,
        hasReal3DGeometry,
      });

      // FIX 16.01.2026 14:50: Konsistente Höhenberechnung für Gebäude und Dach
      // Wenn echte 3D-Dachgeometrie vorhanden, berechne buildingHeight aus dach_min - terrain
      // Dies stellt sicher, dass das Dach korrekt auf dem Gebäude sitzt
      let buildingHeight: number;
      if (hasReal3DGeometry && config.roof?.roof_dach_min_m !== undefined && config.roof?.terrain_z_min !== undefined) {
        // Echte Traufhöhe aus 3D-Daten: dach_min (m ü.M.) - terrain (m ü.M.)
        buildingHeight = config.roof.roof_dach_min_m - config.roof.terrain_z_min;
        console.log('[3D-ROOF] Verwende konsistente Höhenberechnung', {
          dachMin: config.roof.roof_dach_min_m,
          terrainZMin: config.roof.terrain_z_min,
          buildingHeight: buildingHeight.toFixed(2),
          alteTraufhoehe: config.roof?.traufhoehe_m,
        });
      } else {
        // Fallback: Alte Berechnung
        const maxFacadeHeight = enabledFacades.length > 0
          ? enabledFacades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * levelHeight), 10)
          : 10;
        buildingHeight = config.roof?.traufhoehe_m || Math.max(8, maxFacadeHeight - (config.roof?.trauf_to_first_m || 0));
      }

      // NEU 18.01.2026: Echte 3D-Wände wenn verfügbar, sonst Extrusion als Fallback
      // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
      const has3DWalls = buildingWalls && buildingWalls.length > 0 &&
        buildingWalls.some(w => w.geometry && w.geometry.length > 0);

      if (has3DWalls) {
        // Echte 3D-Wandgeometrie aus swissBUILDINGS3D - zeigt echte Turmformen, Anbauten, etc.

        // FIX 20.01.2026: Berechne wallCenter aus den 3D-Walls selbst (nicht aus Union-Polygon!)
        // Bei Multi-Building Projekten hat das Union-Polygon ein anderes Zentrum als die Walls
        let wallMinE = Infinity, wallMaxE = -Infinity;
        let wallMinN = Infinity, wallMaxN = -Infinity;
        let wallMinZ = Infinity;  // FIX 21.01.2026: Auch Z-Min für Terrain berechnen
        let wallMaxZ = -Infinity; // FIX 31.01.2026: Z-Max für echte Gebäudehöhe (nicht roof_dach_min_m!)
        buildingWalls.forEach(wall => {
          if (!wall.geometry) return;
          // Iteriere durch alle Koordinaten um Bbox zu finden
          const processCoord = (coord: number[]) => {
            if (coord.length >= 2) {
              wallMinE = Math.min(wallMinE, coord[0]);
              wallMaxE = Math.max(wallMaxE, coord[0]);
              wallMinN = Math.min(wallMinN, coord[1]);
              wallMaxN = Math.max(wallMaxN, coord[1]);
            }
            if (coord.length >= 3) {
              wallMinZ = Math.min(wallMinZ, coord[2]);
              wallMaxZ = Math.max(wallMaxZ, coord[2]); // FIX 31.01.2026
            }
          };
          // Rekursiv durch alle Verschachtelungsebenen
          const processGeom = (geom: unknown) => {
            if (Array.isArray(geom)) {
              if (geom.length > 0 && typeof geom[0] === 'number') {
                processCoord(geom as number[]);
              } else {
                geom.forEach(g => processGeom(g));
              }
            }
          };
          processGeom(wall.geometry);
        });

        const wallCenter: [number, number] = wallMinE !== Infinity
          ? [(wallMinE + wallMaxE) / 2, (wallMinN + wallMaxN) / 2]
          : bboxCenter;

        // FIX 21.01.2026: effectiveTerrainZ für BEIDE - Wände UND Dach
        // WICHTIG: Bei 3D-Walls IMMER wallMinZ verwenden für Konsistenz!
        // Die API terrain_z_min kann anders sein als der niedrigste Wand-Punkt
        // → Dach würde sonst nicht auf den Wänden sitzen
        const effectiveTerrainZ = wallMinZ !== Infinity ? wallMinZ : (config.roof?.terrain_z_min || 0);

        // FIX 31.01.2026: buildingHeight aus Walls berechnen, NICHT aus roof_dach_min_m!
        // Bei Flachdächern ist roof_dach_min_m nur das Attika-Niveau (z.B. 2.98m),
        // während die echte Gebäudehöhe viel grösser ist (z.B. 11.52m).
        // wallMaxZ - wallMinZ = echte Gebäudehöhe aus 3D-Daten
        const effectiveBuildingHeight = wallMaxZ !== -Infinity
          ? wallMaxZ - effectiveTerrainZ  // Echte Höhe aus 3D-Walls
          : (hasReal3DGeometry && config.roof?.roof_dach_min_m
              ? config.roof.roof_dach_min_m - effectiveTerrainZ
              : buildingHeight);

        console.log('[3D-WALLS] Verwende echte 3D-Wandgeometrie', {
          wallCount: buildingWalls.length,
          wallMinZ: wallMinZ !== Infinity ? wallMinZ.toFixed(1) : 'undefined',
          wallMaxZ: wallMaxZ !== -Infinity ? wallMaxZ.toFixed(1) : 'undefined', // FIX 31.01.2026
          apiTerrainZ: config.roof?.terrain_z_min?.toFixed(1) ?? 'undefined',
          apiRoofDachMin: config.roof?.roof_dach_min_m?.toFixed(1) ?? 'undefined', // Für Vergleich
          effectiveTerrainZ: effectiveTerrainZ.toFixed(1),
          effectiveBuildingHeight: effectiveBuildingHeight.toFixed(2),
          heightSource: wallMaxZ !== -Infinity ? 'walls (z_max - z_min)' : 'roof_dach_min_m fallback',
          complexity: buildingComplexity,
          wallCenter: `${wallCenter[0].toFixed(0)}, ${wallCenter[1].toFixed(0)}`,
        });
        parent.add(createBuildingFrom3DWalls(buildingWalls, wallCenter, effectiveTerrainZ));

        // FIX 21.01.2026: Dach auch mit wallCenter und effectiveTerrainZ
        // Sonst passen Wände und Dach bei Multi-Building nicht zusammen
        if (hasReal3DGeometry) {
          // FIX 21.01.2026: Fallback für roof_dach_min_m - aus Geometrie berechnen
          let roofDachMinM = config.roof!.roof_dach_min_m;
          if (roofDachMinM === undefined || roofDachMinM === null) {
            // Berechne min Z aus der Dach-Geometrie
            const allZValues = config.roof!.roof_geometry_coords!.flatMap(
              polygon => polygon.map(point => point[2])  // Z ist der dritte Wert
            );
            roofDachMinM = Math.min(...allZValues);
            console.log('[3D-ROOF] roof_dach_min_m aus Geometrie berechnet:', roofDachMinM.toFixed(2));
          }

          // FIX 01.02.2026: Dach verwendet dieselbe Terrain-Referenz wie Wände
          // VORHER: y = buildingHeight + (z - roofDachMinM) → Dach schwebt wenn roofDachMinM != wallMaxZ
          // NACHHER: y = 0 + (z - effectiveTerrainZ) = z - effectiveTerrainZ → konsistent mit Wänden!
          console.log('[3D-ROOF] Verwende echte 3D-Dachgeometrie (mit wallCenter)', {
            polygons: config.roof!.roof_geometry_coords!.length,
            dachMin: roofDachMinM,
            dachMax: config.roof!.roof_dach_max_m,
            effectiveTerrainZ: effectiveTerrainZ.toFixed(2),
            center: `${wallCenter[0].toFixed(0)}, ${wallCenter[1].toFixed(0)}`,
          });
          parent.add(createRoofFrom3DGeometry(
            config.roof!.roof_geometry_coords!,
            wallCenter[0],  // FIX: wallCenter statt bboxCenter
            wallCenter[1],
            effectiveTerrainZ,  // FIX 01.02.2026: Terrain statt roofDachMinM - konsistent mit Wänden
            0  // FIX 01.02.2026: Kein Offset mehr - die Formel wird y = z - terrainZ
          ));
        } else {
          // FIX 21.01.2026: Fallback auf heuristisches Dach wenn 3D-Walls aber keine 3D-Roof-Daten
          const hasSpecialZones = buildingZones.some(z =>
            z.zone_type === 'turm' || z.zone_type === 'kuppel' || z.zone_type === 'treppenhaus'
          );
          const shouldRenderHeuristicRoof = !hasSpecialZones || buildingComplexity === 'simple';

          if (shouldRenderHeuristicRoof) {
            console.log('[3D-ROOF] Fallback: Heuristisches Dach (3D-Walls ohne 3D-Roof)', {
              effectiveBuildingHeight: effectiveBuildingHeight.toFixed(2),
              complexity: buildingComplexity,
            });
            const roofType = config.roof?.roof_type || 'satteldach';
            const roofHeight = config.roof?.trauf_to_first_m || 3;
            const roofOrientation = config.roof?.roof_orientation || 'O-W';
            const roofOverhang = config.roof?.roof_overhang_m || 0.4;
            parent.add(createRoofFromPolygon(normalized, effectiveBuildingHeight, roofHeight, roofType, roofOrientation, roofOverhang));
          } else {
            console.log('[3D-ROOF] Kein Dach: Komplexes Gebäude ohne 3D-Roof-Daten', { complexity: buildingComplexity, hasSpecialZones });
          }
        }
      } else {
        // Fallback: 2D-Polygon Extrusion (alle Wände gleiche Höhe)
        console.log('[3D-WALLS] Fallback: 2D-Extrusion (keine 3D-Wände)', {
          buildingHeight: buildingHeight.toFixed(2),
        });
        parent.add(createBuildingFromPolygon(normalized, buildingHeight));

        // Dach für 2D-Extrusion (ohne 3D-Walls)
        if (hasReal3DGeometry) {
          // Echte 3D-Geometrie aus swissBUILDINGS3D - IMMER verwenden wenn verfügbar
          console.log('[3D-ROOF] Verwende echte 3D-Dachgeometrie', {
            polygons: config.roof!.roof_geometry_coords!.length,
            dachMin: config.roof!.roof_dach_min_m,
            dachMax: config.roof!.roof_dach_max_m,
            complexity: buildingComplexity,
          });
          parent.add(createRoofFrom3DGeometry(
            config.roof!.roof_geometry_coords!,
            bboxCenter[0],  // center_e (LV95)
            bboxCenter[1],  // center_n (LV95)
            config.roof!.roof_dach_min_m!,
            buildingHeight
          ));
        } else {
          // Fallback: Heuristisches Dach NUR für einfache Gebäude (ohne 3D-Walls)
          const hasSpecialZones = buildingZones.some(z =>
            z.zone_type === 'turm' || z.zone_type === 'kuppel' || z.zone_type === 'treppenhaus'
          );
          const shouldRenderHeuristicRoof = !hasSpecialZones || buildingComplexity === 'simple';

          if (shouldRenderHeuristicRoof) {
            console.log('[3D-ROOF] Fallback: Heuristisches Dach (2D-Extrusion)', { complexity: buildingComplexity });
            const roofType = config.roof?.roof_type || 'satteldach';
            const roofHeight = config.roof?.trauf_to_first_m || 3;
            const roofOrientation = config.roof?.roof_orientation || 'O-W';
            const roofOverhang = config.roof?.roof_overhang_m || 0.4;
            parent.add(createRoofFromPolygon(normalized, buildingHeight, roofHeight, roofType, roofOrientation, roofOverhang));
          } else {
            console.log('[3D-ROOF] Kein Dach: Komplexes Gebäude ohne 3D-Daten', { complexity: buildingComplexity, hasSpecialZones });
          }
        }
      }

      // Add zones for complex buildings (Türme, Kuppeln, Anbauten, etc.)
      if (buildingZones.length > 0 && buildingComplexity !== 'simple') {
        console.log('=== ADDING ZONES ===', { count: buildingZones.length, complexity: buildingComplexity });
        // Calculate bounding box for normalized polygon (used for zone positioning)
        const normalizedBbox = {
          minX: Math.min(...normalized.map(p => p[0])),
          maxX: Math.max(...normalized.map(p => p[0])),
          minY: Math.min(...normalized.map(p => p[1])),
          maxY: Math.max(...normalized.map(p => p[1])),
        };

        buildingZones.forEach((zone) => {
          // Skip hauptgebaeude as it's already rendered as the main building
          if (zone.zone_type === 'hauptgebaeude') {
            console.log(`  - Skipping ${zone.name} (hauptgebaeude already rendered)`);
            return;
          }

          console.log(`  - Adding zone: ${zone.name}, type=${zone.zone_type}, position=${zone.position || 'default'}`);
          const zoneGroup = createZoneGeometry(zone, normalized, buildingHeight, normalizedBbox);
          parent.add(zoneGroup);
        });
      }

      // Add scaffolds along actual facade edges (ONLY ENABLED facades)
      // Use bboxCenter instead of centroid for consistent alignment
      // FIX 06.02.2026: Dynamischer scaffoldGap basierend auf work_type und roof_overhang_m
      // Die Offset-Berechnung ist: offset = scaffoldGap + cellDepth/2
      // → Gerüst-Innenkante = scaffoldGap, Gerüst-Aussenkante = scaffoldGap + cellDepth
      // Für Dacharbeiten: Gerüst-Innenkante muss AUSSERHALB des Dachvorstands sein!
      const workType = config.settings.work_type;
      const roofOverhang = config.roof?.roof_overhang_m ?? 0.4;
      const cellDepth = 0.73; // Gerüst-Tiefe (Layher Blitz 70)
      const workingMargin = 0.1; // 10cm Arbeitsraum zwischen Dach und Gerüst

      let scaffoldGap: number;
      if (workType === 'roof' || workType === 'roofer') {
        // Dacharbeiten: Gerüst-Innenkante = Dachvorstand + Arbeitsraum
        // scaffoldGap = Abstand Fassade bis Gerüst-Mitte
        // → scaffoldGap = roofOverhang + workingMargin + cellDepth/2
        scaffoldGap = roofOverhang + workingMargin + cellDepth / 2;
      } else {
        // Fassadenarbeit: Standard-Abstand (nah am Gebäude)
        scaffoldGap = 0.4;
      }

      console.log('[3D-SCAFFOLD] Scaffold gap calculated:', {
        workType,
        roofOverhang: roofOverhang.toFixed(2),
        cellDepth,
        workingMargin,
        scaffoldGap: scaffoldGap.toFixed(2),
        innerEdge: (scaffoldGap - cellDepth / 2).toFixed(2),
        outerEdge: (scaffoldGap + cellDepth / 2).toFixed(2),
      });

      enabledFacades.forEach((facade) => {
        parent.add(createScaffoldFacadeAlongEdge(facade, fieldWidth, levelHeight, bboxCenter, scaffoldGap));
      });

      // Add corners (only if enabled)
      // FIX 05.02.2026: scaffoldGap auch für Ecken übergeben
      corners.forEach((corner) => {
        const cornerGroup = createScaffoldCorner(corner, enabledFacades, levelHeight, bboxCenter, scaffoldGap);
        if (cornerGroup) {
          parent.add(cornerGroup);
        }
      });

      // Add neighbor buildings (Phase 2.3)
      // FIX 21.01.2026: Echte Höhe und heuristisches Dach für Nachbarn
      if (neighborBuildings.length > 0) {
        const mainCenter = bboxCenter;
        neighborBuildings.forEach((neighbor, index) => {
          if (!neighbor.polygon || neighbor.polygon.length < 3) return;

          // Calculate neighbor polygon center
          const neighborMinX = Math.min(...neighbor.polygon.map(p => p[0]));
          const neighborMaxX = Math.max(...neighbor.polygon.map(p => p[0]));
          const neighborMinY = Math.min(...neighbor.polygon.map(p => p[1]));
          const neighborMaxY = Math.max(...neighbor.polygon.map(p => p[1]));
          const neighborCenter: [number, number] = [(neighborMinX + neighborMaxX) / 2, (neighborMinY + neighborMaxY) / 2];

          // Offset from main building center
          const offsetX = neighborCenter[0] - mainCenter[0];
          const offsetZ = -(neighborCenter[1] - mainCenter[1]); // Y in LV95 -> -Z in THREE.js

          // Normalize neighbor polygon relative to its own center
          const normalizedNeighbor = neighbor.polygon.map(p =>
            [p[0] - neighborCenter[0], p[1] - neighborCenter[1]] as [number, number]
          );

          // FIX 21.01.2026: Echte Höhe aus Nachbar-Daten verwenden
          // Priorität: 1) dach_min - terrain, 2) gebaeudehoehe_m, 3) Fallback 8m
          let neighborHeight = 8; // Fallback
          let neighborRoofHeight = 2.5; // Heuristisch: ~2.5m Dachhöhe

          if (neighbor.roof_dach_min_m != null && neighbor.terrain_z_min != null) {
            // Beste Option: Echte Traufhöhe berechnen
            neighborHeight = neighbor.roof_dach_min_m - neighbor.terrain_z_min;
            if (neighbor.roof_dach_max_m != null) {
              neighborRoofHeight = neighbor.roof_dach_max_m - neighbor.roof_dach_min_m;
            }
          } else if (neighbor.gebaeudehoehe_m != null) {
            // Fallback: Gesamthöhe verwenden (Trauf ≈ 70% der Gesamthöhe)
            neighborHeight = neighbor.gebaeudehoehe_m * 0.7;
            neighborRoofHeight = neighbor.gebaeudehoehe_m * 0.3;
          }

          // Create semi-transparent building for neighbor
          const neighborMesh = createBuildingFromPolygon(normalizedNeighbor, neighborHeight);

          // Make it semi-transparent gray
          neighborMesh.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.material = new THREE.MeshLambertMaterial({
                color: 0x888888,
                transparent: true,
                opacity: 0.4,
              });
            }
          });

          // Position relative to main building
          neighborMesh.position.set(offsetX, 0, offsetZ);
          parent.add(neighborMesh);

          // FIX 21.01.2026: Heuristisches Dach für Nachbarn hinzufügen
          // Einfaches Satteldach mit O-W Orientierung (Standard)
          const neighborRoof = createRoofFromPolygon(
            normalizedNeighbor,
            neighborHeight,
            neighborRoofHeight,
            'satteldach',
            'O-W',  // Standard-Orientierung
            0.3     // Kleiner Dachüberstand
          );

          // Dach auch semi-transparent grau machen
          neighborRoof.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.material = new THREE.MeshLambertMaterial({
                color: 0x666666,  // Etwas dunkler als Wände
                transparent: true,
                opacity: 0.5,
              });
            }
          });

          neighborRoof.position.set(offsetX, 0, offsetZ);
          parent.add(neighborRoof);

          console.log(`Added neighbor ${index + 1}/${neighborBuildings.length}: height=${neighborHeight.toFixed(1)}m, roof=${neighborRoofHeight.toFixed(1)}m`);
        });
      }

      // NEU 19.01.2026: Objekt-Architektur - Multi-Building-Projekte
      // Das Haupt-Polygon IST bereits die Union aller Gebäude.
      // objectData.projectBuildings enthält nur Metadaten (egid, address, center) - KEINE Polygone mehr.
      // Daher werden zusätzliche Gebäude nicht mehr separat gerendert.
      // Die Fassaden des Union-Polygons werden oben mit enabledFacades gerendert.
      if (objectData?.projectBuildings && objectData.projectBuildings.length > 1) {
        console.log(`Multi-building object: ${objectData.projectBuildings.length} buildings in union polygon`);
        objectData.projectBuildings.forEach((building, index) => {
          console.log(`  - Building ${index + 1}: ${building.address} (EGID: ${building.egid})`);
        });
      }

    } else {
      // FALLBACK: Use old box-based approach (for backwards compatibility)
      const nsLength = enabledFacades
        .filter(f => ['N', 'S', 'NE', 'NW', 'SE', 'SW'].includes(f.direction))
        .reduce((sum, f) => Math.max(sum, f.length_m), 10);
      const ewLength = enabledFacades
        .filter(f => ['E', 'W'].includes(f.direction))
        .reduce((sum, f) => Math.max(sum, f.length_m), 8);

      const fallbackBuildingWidth = Math.max(10, nsLength);
      const fallbackBuildingDepth = Math.max(8, ewLength > 0 ? ewLength : nsLength * 0.6);
      const maxFacadeHeight = enabledFacades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * levelHeight), 10);
      // Traufhöhe = Gebäudehöhe bis Dachansatz
      const fallbackBuildingHeight = config.roof?.traufhoehe_m || Math.max(8, maxFacadeHeight - 3);

      // Add simple box building
      parent.add(createBuilding(fallbackBuildingWidth, fallbackBuildingDepth, fallbackBuildingHeight));

      // Add roof if needed
      // FIX 27.01.2026: 'full' ersetzt durch 'roofer' (Spengler)
      if (config.settings.work_type === 'roof' || config.settings.work_type === 'roofer') {
        parent.add(createRoof(fallbackBuildingWidth + 1, fallbackBuildingDepth + 1, 3, fallbackBuildingHeight));
      }

      // Track which directions we've seen to position facades correctly
      const directionCount: Record<string, number> = {};

      // Get scaffold offset based on direction
      const getOffset = (facade: ScaffoldFacade): { offset: THREE.Vector3; dir: 'x' | 'z' } => {
        const gap = 0.5;
        const dir = facade.direction;

        directionCount[dir] = (directionCount[dir] || 0);
        const stackOffset = directionCount[dir] * 3;
        directionCount[dir]++;

        switch (dir) {
          case 'N':
          case 'NE':
          case 'NW':
            return { offset: new THREE.Vector3(-facade.length_m / 2, 0, fallbackBuildingDepth / 2 + gap + stackOffset), dir: 'x' };
          case 'S':
          case 'SE':
          case 'SW':
            return { offset: new THREE.Vector3(-facade.length_m / 2, 0, -fallbackBuildingDepth / 2 - gap - 0.73 - stackOffset), dir: 'x' };
          case 'E':
            return { offset: new THREE.Vector3(fallbackBuildingWidth / 2 + gap + stackOffset, 0, -facade.length_m / 2), dir: 'z' };
          case 'W':
            return { offset: new THREE.Vector3(-fallbackBuildingWidth / 2 - gap - 0.73 - stackOffset, 0, -facade.length_m / 2), dir: 'z' };
          default:
            const fallbackIndex = Object.keys(directionCount).filter(k => k === dir).length;
            const side = fallbackIndex % 4;
            switch (side) {
              case 0: return { offset: new THREE.Vector3(-facade.length_m / 2, 0, fallbackBuildingDepth / 2 + gap), dir: 'x' };
              case 1: return { offset: new THREE.Vector3(fallbackBuildingWidth / 2 + gap, 0, -facade.length_m / 2), dir: 'z' };
              case 2: return { offset: new THREE.Vector3(-facade.length_m / 2, 0, -fallbackBuildingDepth / 2 - gap - 0.73), dir: 'x' };
              case 3: return { offset: new THREE.Vector3(-fallbackBuildingWidth / 2 - gap - 0.73, 0, -facade.length_m / 2), dir: 'z' };
              default: return { offset: new THREE.Vector3(0, 0, 0), dir: 'x' };
            }
        }
      };

      // Add scaffolds (fallback)
      enabledFacades.forEach((facade) => {
        const { offset, dir } = getOffset(facade);
        parent.add(createScaffoldFacade(facade, fieldWidth, levelHeight, offset, dir));
      });
    }
  }

  return (
    // FIX 14.01.2026 17:30 - touch-action: none für Touch-Zoom, user-select: none für Drag
    <div ref={containerRef} className="w-full h-full min-h-[400px] relative" style={{ touchAction: 'none', userSelect: 'none' }}>
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
