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
import type { NeighborBuilding, MultiBuildingData } from '../../../../api/geruestbau';
import { createSatteldachGeometry, type Point2D } from '../../utils/roofGeometry';

// FIX 11.01.2026 02:40 - Dach-Orientierung aus Polygon berechnen
// Gleiche Logik wie Backend (roof.py): First senkrecht zur längsten Seite
function calculatePolygonRoofOrientation(polygon: [number, number][]): 'O-W' | 'N-S' {
  if (!polygon || polygon.length < 3) return 'O-W';

  // Längste Seite finden
  let maxLength = 0;
  let longestSideVector = { dx: 1, dy: 0 };

  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % polygon.length];
    const dx = p2[0] - p1[0];
    const dy = p2[1] - p1[1];
    const length = Math.sqrt(dx * dx + dy * dy);

    if (length > maxLength) {
      maxLength = length;
      longestSideVector = { dx, dy };
    }
  }

  // Azimut berechnen (0° = Nord, 90° = Ost)
  let azimuthDeg = Math.atan2(longestSideVector.dx, longestSideVector.dy) * (180 / Math.PI);
  if (azimuthDeg < 0) azimuthDeg += 360;

  // Klassifizierung: Längste Seite ~O-W (67.5-112.5° oder 247.5-292.5°) → Dach neigt O-W
  if ((azimuthDeg >= 67.5 && azimuthDeg < 112.5) ||
      (azimuthDeg >= 247.5 && azimuthDeg < 292.5)) {
    return 'O-W';
  }
  return 'N-S';
}

interface ScaffoldSceneProps {
  configuration: ScaffoldConfiguration;
  activeView: View3D;
  onViewChange?: (view: View3D) => void;
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
  additionalBuildings?: MultiBuildingData[];
  zones?: BuildingZone[];
  complexity?: 'simple' | 'moderate' | 'complex';
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
function createRoofFrom3DGeometry(
  roofCoords: number[][][],  // Array von Polygonen: [[[E, N, Z], ...], ...]
  centerE: number,           // Gebäude-Zentrum E (LV95)
  centerN: number,           // Gebäude-Zentrum N (LV95)
  roofDachMinM: number,      // Niedrigste Z-Höhe (Traufe) in m ü.M.
  buildingHeight: number     // Traufhöhe im lokalen Koordinatensystem (Y-Offset)
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
    // Y = buildingHeight + (Z_abs - roofDachMinM)  [relative Höhe über Traufe]
    const transformedPoints = polygon.map(point => {
      const [e, n, z] = point;
      return {
        x: e - centerE,
        y: buildingHeight + (z - roofDachMinM),  // Relative Höhe
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
    } else {
      // Komplexeres Polygon - verwende ShapeGeometry
      const shape = new THREE.Shape();
      shape.moveTo(transformedPoints[0].x, transformedPoints[0].z);
      for (let i = 1; i < transformedPoints.length - 1; i++) {
        shape.lineTo(transformedPoints[i].x, transformedPoints[i].z);
      }
      shape.closePath();

      const geometry = new THREE.ShapeGeometry(shape);
      const mesh = new THREE.Mesh(geometry, roofMaterial);

      // Rotiere für horizontale Ausrichtung und setze Y-Position
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = transformedPoints[0].y;  // Verwende die Höhe des ersten Punkts
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

  // Check if we have actual coordinates
  if (!facade.start_point || !facade.end_point) {
    // Fallback: no positioning (shouldn't happen)
    return group;
  }

  // Normalize coordinates relative to center
  // Swap start/end to match polygon winding order
  const startX = facade.end_point[0] - center[0];
  const startZ = -(facade.end_point[1] - center[1]);
  const endX = facade.start_point[0] - center[0];
  const endZ = -(facade.start_point[1] - center[1]);

  // Calculate facade direction vector
  const dx = endX - startX;
  const dz = endZ - startZ;
  const length = Math.sqrt(dx * dx + dz * dz);

  // Normalize direction
  const dirX = dx / length;
  const dirZ = dz / length;

  // Perpendicular direction (outward from building)
  const perpX = -dirZ;
  const perpZ = dirX;

  // Offset scaffolds outward from building edge
  const offsetX = perpX * (scaffoldGap + cellDepth / 2);
  const offsetZ = perpZ * (scaffoldGap + cellDepth / 2);

  // Inset scaffolds slightly at corners to avoid overlap (half cell width on each end)
  const cornerInset = 0.5 / facade.fields; // ~half a cell at each end

  for (let level = 0; level < facade.levels; level++) {
    for (let field = 0; field < facade.fields; field++) {
      const key = `${field}-${level}`;
      if (facade.modifications.removed_cells.has(key)) continue;

      // Position along the facade edge (with corner inset to avoid overlap)
      const tRaw = (field + 0.5) / facade.fields; // 0 to 1 along the edge
      const t = cornerInset + tRaw * (1 - 2 * cornerInset); // Shrink range to avoid corners
      const cellX = startX + dx * t + offsetX;
      const cellZ = startZ + dz * t + offsetZ;
      const cellY = level * levelHeight + levelHeight / 2;

      const cellWidth = fieldWidth * 0.95;
      const cellHeight = levelHeight * 0.95;

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

  // Create corner posts (vertical cylinders at corner)
  const postRadius = 0.05;
  const postHeight = levels * levelHeight;
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
  if (corner.diagonals > 0) {
    const diagMaterial = new THREE.LineBasicMaterial({ color: cornerColor });
    for (let level = 0; level < levels; level++) {
      const y = level * levelHeight + levelHeight / 2;
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
  additionalBuildings = [],
  zones = [],
  complexity = 'simple',
}: ScaffoldSceneProps) {
  // Log neighbors for debugging (will be used for rendering in Phase 2.3)
  if (neighbors.length > 0) {
    console.log(`ScaffoldScene: ${neighbors.length} neighbors, blocked sides: ${blockedSides.join(', ')}`);
  }
  if (additionalBuildings.length > 0) {
    console.log(`ScaffoldScene: ${additionalBuildings.length} additional buildings for multi-building view`);
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

  // Update scene content when configuration, neighbors, or additionalBuildings change
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
    addSceneContent(contentGroup, configuration, neighbors, additionalBuildings, zones, complexity);

    console.log('Scene content updated:', {
      neighbors: neighbors.length,
      additionalBuildings: additionalBuildings.length,
      facades: configuration.elements.filter(e => e.type === 'facade' && e.enabled).length,
      zones: zones.length,
      complexity,
    });
  }, [configuration, neighbors, additionalBuildings, zones, complexity]);

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
  function addSceneContent(
    parent: THREE.Object3D,
    config: ScaffoldConfiguration,
    neighborBuildings: NeighborBuilding[] = [],
    multiBuildingData: MultiBuildingData[] = [],
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

      // Calculate building height: use actual traufhoehe if available, otherwise estimate from facades or default
      const maxFacadeHeight = enabledFacades.length > 0
        ? enabledFacades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * levelHeight), 10)
        : 10;
      // Traufhöhe = Gebäudehöhe bis Dachansatz (wo das Dach startet)
      // Priority: config.roof.traufhoehe_m > facade height estimate > default 8m
      const buildingHeight = config.roof?.traufhoehe_m || Math.max(8, maxFacadeHeight - (config.roof?.trauf_to_first_m || 0));

      // Add building from actual polygon
      parent.add(createBuildingFromPolygon(normalized, buildingHeight));

      // Check if building has towers or domes - skip standard roof for complex buildings
      // Complex buildings with separate height zones (churches, public buildings) should NOT get a single roof
      const hasSpecialZones = buildingZones.some(z =>
        z.zone_type === 'turm' || z.zone_type === 'kuppel' || z.zone_type === 'treppenhaus'
      );
      const shouldRenderRoof = !hasSpecialZones || buildingComplexity === 'simple';

      if (shouldRenderRoof) {
        // NEU 14.01.2026: Echte 3D-Dachgeometrie priorisieren wenn verfügbar
        const hasReal3DGeometry = config.roof?.has_roof_geometry &&
                                   config.roof?.roof_geometry_coords &&
                                   config.roof.roof_geometry_coords.length > 0 &&
                                   config.roof?.roof_dach_min_m;

        if (hasReal3DGeometry) {
          // Echte 3D-Geometrie aus swissBUILDINGS3D verwenden
          console.log('[3D-ROOF] Verwende echte 3D-Dachgeometrie', {
            polygons: config.roof!.roof_geometry_coords!.length,
            dachMin: config.roof!.roof_dach_min_m,
            dachMax: config.roof!.roof_dach_max_m,
          });
          parent.add(createRoofFrom3DGeometry(
            config.roof!.roof_geometry_coords!,
            bboxCenter[0],  // center_e (LV95)
            bboxCenter[1],  // center_n (LV95)
            config.roof!.roof_dach_min_m!,
            buildingHeight
          ));
        } else {
          // Fallback: Heuristisches Dach basierend auf Polygon-Form
          const roofType = config.roof?.roof_type || 'satteldach';
          const roofHeight = config.roof?.trauf_to_first_m || 3;
          const roofOrientation = config.roof?.roof_orientation || 'O-W';
          const roofOverhang = config.roof?.roof_overhang_m || 0.4;
          parent.add(createRoofFromPolygon(normalized, buildingHeight, roofHeight, roofType, roofOrientation, roofOverhang));
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
      enabledFacades.forEach((facade) => {
        parent.add(createScaffoldFacadeAlongEdge(facade, fieldWidth, levelHeight, bboxCenter));
      });

      // Add corners (only if enabled)
      corners.forEach((corner) => {
        const cornerGroup = createScaffoldCorner(corner, enabledFacades, levelHeight, bboxCenter);
        if (cornerGroup) {
          parent.add(cornerGroup);
        }
      });

      // Add neighbor buildings (Phase 2.3)
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

          // Create semi-transparent building for neighbor
          const neighborHeight = 8; // Default height for neighbors (no height data)
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

          console.log(`Added neighbor ${index + 1}/${neighborBuildings.length} at offset (${offsetX.toFixed(1)}, ${offsetZ.toFixed(1)})`);
        });
      }

      // Add additional selected buildings (Phase 3.4 - Multi-Building View)
      if (multiBuildingData.length > 0) {
        const mainCenter = bboxCenter;
        multiBuildingData.forEach((building, index) => {
          if (!building.polygon || building.polygon.length < 3) return;

          // Use building.center from API (LV95 coordinates)
          const buildingCenterE = building.center[0];
          const buildingCenterN = building.center[1];

          // Offset from main building center
          const offsetX = buildingCenterE - mainCenter[0];
          const offsetZ = -(buildingCenterN - mainCenter[1]); // Y in LV95 -> -Z in THREE.js

          // Normalize building polygon relative to its own center
          const normalizedBuilding = building.polygon.map(p =>
            [p[0] - buildingCenterE, p[1] - buildingCenterN] as [number, number]
          );

          // Create building mesh with full opacity (blue-purple tint for additional buildings)
          const addBuildingHeight = building.traufhoehe_m || 10;
          const buildingMesh = createBuildingFromPolygon(normalizedBuilding, addBuildingHeight);

          // Apply distinct color for additional buildings
          buildingMesh.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.material = new THREE.MeshStandardMaterial({
                color: 0x6366f1, // Indigo/purple for additional buildings
                transparent: true,
                opacity: 0.7,
              });
            }
          });

          // Position relative to main building
          buildingMesh.position.set(offsetX, 0, offsetZ);
          parent.add(buildingMesh);

          // Add roof for additional buildings
          // FIX 11.01.2026 02:40 - Dach-Typ und Orientierung pro Gebäude berechnen
          const addRoofHeight = (building.firsthoehe_m || addBuildingHeight + 3) - addBuildingHeight;
          // Dachtyp aus Höhendifferenz: < 0.5m = flachdach, sonst satteldach
          const addRoofType = addRoofHeight < 0.5 ? 'flachdach' : 'satteldach';
          const addRoofOrientation = calculatePolygonRoofOrientation(building.polygon);
          const additionalRoof = createRoofFromPolygon(normalizedBuilding, addBuildingHeight, addRoofHeight, addRoofType, addRoofOrientation);
          additionalRoof.position.set(offsetX, 0, offsetZ);
          parent.add(additionalRoof);

          console.log(`Added additional building ${index + 1}/${multiBuildingData.length}: ${building.address} at offset (${offsetX.toFixed(1)}, ${offsetZ.toFixed(1)})`);
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
      if (config.settings.work_type === 'roof' || config.settings.work_type === 'full') {
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
