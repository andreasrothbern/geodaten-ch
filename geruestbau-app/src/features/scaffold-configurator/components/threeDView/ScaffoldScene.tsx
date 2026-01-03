/**
 * ScaffoldScene - 3D visualization using IFC.js (@thatopen/components)
 *
 * Uses ThatOpen Components for IFC-compatible 3D rendering with
 * future support for IFC/DXF export to LayPLAN.
 */

import { useRef, useEffect, useState } from 'react';
import * as OBC from '@thatopen/components';
import * as THREE from 'three';
import type { ScaffoldConfiguration, ScaffoldFacade, ScaffoldCorner, View3D } from '../../types/scaffold.types';
import type { NeighborBuilding } from '../../../../api/geruestbau';
import { createSatteldachGeometry, type Point2D } from '../../utils/roofGeometry';

interface ScaffoldSceneProps {
  configuration: ScaffoldConfiguration;
  activeView: View3D;
  onViewChange?: (view: View3D) => void;
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
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

  // Calculate bounding box center (must match building centering)
  const minX = Math.min(...normalized.map(p => p[0]));
  const maxX = Math.max(...normalized.map(p => p[0]));
  const minY = Math.min(...normalized.map(p => p[1]));
  const maxY = Math.max(...normalized.map(p => p[1]));
  const bboxCenterX = (minX + maxX) / 2;
  const bboxCenterY = (minY + maxY) / 2;

  // Transform polygon points to be centered at origin (matching building)
  // Polygon coords: X stays X, Y becomes -Z in THREE.js
  // Apply roof overhang by scaling points outward from center
  const centeredPoints = normalized.map(p => {
    const dx = p[0] - bboxCenterX;
    const dy = p[1] - bboxCenterY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    // Scale outward by adding overhang along the radial direction
    const scale = dist > 0 ? (dist + roofOverhang) / dist : 1;
    return {
      x: dx * scale,
      z: -(dy * scale),  // Negate for THREE.js coordinate system
    };
  });

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

    // DEBUG: Log roof geometry
    console.log('Satteldach Debug:', {
      roofOrientation,
      yEaves,
      yPeak,
      vertexCount: roofGeom.vertices.length / 3,
      vertices: roofGeom.vertices,
      indices: roofGeom.indices,
      centeredPointsBbox: {
        minX: Math.min(...centeredPoints.map(p => p.x)),
        maxX: Math.max(...centeredPoints.map(p => p.x)),
        minZ: Math.min(...centeredPoints.map(p => p.z)),
        maxZ: Math.max(...centeredPoints.map(p => p.z)),
      }
    });

    // DEBUG: Render each triangle SEPARATELY with different colors to see what's happening
    const triangleColors = [
      0xff0000,  // West slope triangle 1: RED
      0xff4444,  // West slope triangle 2: LIGHT RED
      0x0000ff,  // East slope triangle 1: BLUE
      0x4444ff,  // East slope triangle 2: LIGHT BLUE
      0x00ff00,  // North gable: GREEN
      0xffff00,  // South gable: YELLOW
    ];

    // Create separate meshes for each triangle to visualize them
    for (let triIdx = 0; triIdx < roofGeom.indices.length / 3; triIdx++) {
      const i0 = roofGeom.indices[triIdx * 3];
      const i1 = roofGeom.indices[triIdx * 3 + 1];
      const i2 = roofGeom.indices[triIdx * 3 + 2];

      const triGeom = new THREE.BufferGeometry();
      const triVerts = new Float32Array([
        roofGeom.vertices[i0 * 3], roofGeom.vertices[i0 * 3 + 1], roofGeom.vertices[i0 * 3 + 2],
        roofGeom.vertices[i1 * 3], roofGeom.vertices[i1 * 3 + 1], roofGeom.vertices[i1 * 3 + 2],
        roofGeom.vertices[i2 * 3], roofGeom.vertices[i2 * 3 + 1], roofGeom.vertices[i2 * 3 + 2],
      ]);
      triGeom.setAttribute('position', new THREE.BufferAttribute(triVerts, 3));
      triGeom.setIndex([0, 1, 2]);
      triGeom.computeVertexNormals();

      const triMat = new THREE.MeshStandardMaterial({
        color: triangleColors[triIdx % triangleColors.length],
        side: THREE.DoubleSide,
      });
      const triMesh = new THREE.Mesh(triGeom, triMat);
      group.add(triMesh);

      // Log each triangle for debugging
      console.log(`Triangle ${triIdx}:`, {
        indices: [i0, i1, i2],
        v0: [roofGeom.vertices[i0 * 3], roofGeom.vertices[i0 * 3 + 1], roofGeom.vertices[i0 * 3 + 2]],
        v1: [roofGeom.vertices[i1 * 3], roofGeom.vertices[i1 * 3 + 1], roofGeom.vertices[i1 * 3 + 2]],
        v2: [roofGeom.vertices[i2 * 3], roofGeom.vertices[i2 * 3 + 1], roofGeom.vertices[i2 * 3 + 2]],
        color: triangleColors[triIdx % triangleColors.length].toString(16),
      });
    }

    // DEBUG: Add ridge line (CYAN thick line) to visualize first position
    const ridgePoints = [];
    ridgePoints.push(new THREE.Vector3(roofGeom.vertices[12], roofGeom.vertices[13], roofGeom.vertices[14]));
    ridgePoints.push(new THREE.Vector3(roofGeom.vertices[15], roofGeom.vertices[16], roofGeom.vertices[17]));
    const ridgeGeometry = new THREE.BufferGeometry().setFromPoints(ridgePoints);
    const ridgeLine = new THREE.Line(ridgeGeometry, new THREE.LineBasicMaterial({ color: 0x00ffff, linewidth: 10 }));
    group.add(ridgeLine);

    // Add CYAN spheres at ridge points
    const ridgeMarkerGeo = new THREE.SphereGeometry(0.5);
    const ridgeMarkerMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });
    const ridgeN = new THREE.Mesh(ridgeMarkerGeo, ridgeMarkerMat);
    ridgeN.position.set(roofGeom.vertices[12], roofGeom.vertices[13], roofGeom.vertices[14]);
    group.add(ridgeN);
    const ridgeS = new THREE.Mesh(ridgeMarkerGeo, ridgeMarkerMat);
    ridgeS.position.set(roofGeom.vertices[15], roofGeom.vertices[16], roofGeom.vertices[17]);
    group.add(ridgeS);

    // DEBUG: Add eave corner markers (green spheres)
    const markerGeo = new THREE.SphereGeometry(0.3);
    const markerMat = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    for (let i = 0; i < 4; i++) {
      const marker = new THREE.Mesh(markerGeo, markerMat);
      marker.position.set(roofGeom.vertices[i*3], roofGeom.vertices[i*3+1], roofGeom.vertices[i*3+2]);
      group.add(marker);
    }

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
}: ScaffoldSceneProps) {
  // Log neighbors for debugging (will be used for rendering in Phase 2.3)
  if (neighbors.length > 0) {
    console.log(`ScaffoldScene: ${neighbors.length} neighbors, blocked sides: ${blockedSides.join(', ')}`);
  }
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
        addSceneContent(world.scene.three, configuration, neighbors);

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
  }, []);  // Initial scene setup

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
  function addSceneContent(scene: THREE.Scene, config: ScaffoldConfiguration, neighborBuildings: NeighborBuilding[] = []) {
    const allFacades = config.elements.filter((el): el is ScaffoldFacade => el.type === 'facade');
    const enabledFacades = allFacades.filter(f => f.enabled);
    const corners = config.elements.filter((el): el is ScaffoldCorner => el.type === 'corner');
    const fieldWidth = config.settings.field_width_m;
    const levelHeight = config.settings.level_height_m;

    // Building polygon is now always the ORIGINAL from swissBUILDINGS3D
    const polygon3D = config.buildingPolygon;
    const hasPolygon = polygon3D && polygon3D.length >= 3;
    const hasCoordinates = enabledFacades.some(f => f.start_point && f.end_point);

    // DEBUG: Log polygon info
    console.log('=== 3D POLYGON DEBUG ===', {
      polygonPoints: polygon3D?.length || 0,
    });

    if (hasPolygon && hasCoordinates) {
      // NEW: Use actual polygon and facade coordinates
      // Use original polygon for building 3D mesh (more detail)
      const { normalized } = normalizePolygon(polygon3D!);

      // Calculate bounding box center (may differ from centroid)
      // This must match the building's centering logic
      const minX = Math.min(...polygon3D!.map(p => p[0]));
      const maxX = Math.max(...polygon3D!.map(p => p[0]));
      const minY = Math.min(...polygon3D!.map(p => p[1]));
      const maxY = Math.max(...polygon3D!.map(p => p[1]));
      const bboxCenter: [number, number] = [(minX + maxX) / 2, (minY + maxY) / 2];

      // Calculate building height: use actual traufhoehe if available, otherwise estimate
      const maxFacadeHeight = enabledFacades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * levelHeight), 10);
      // Traufhöhe = Gebäudehöhe bis Dachansatz (wo das Dach startet)
      const buildingHeight = config.roof?.traufhoehe_m || Math.max(8, maxFacadeHeight - (config.roof?.trauf_to_first_m || 0));

      // Add building from actual polygon
      scene.add(createBuildingFromPolygon(normalized, buildingHeight));

      // Add roof (always show for visualization)
      // Use roof data from configuration if available
      // Default to 'satteldach' (most common roof type in Switzerland)
      const roofType = config.roof?.roof_type || 'satteldach';
      const roofHeight = config.roof?.trauf_to_first_m || 3;
      // IMPORTANT: For Satteldach we MUST have orientation for correct ridge placement
      // Default to 'O-W' (ridge runs N-S, roof slopes East-West) - most common orientation
      const roofOrientation = config.roof?.roof_orientation || 'O-W';
      const roofOverhang = config.roof?.roof_overhang_m || 0.4;  // Standard 40cm

      // DEBUG: Log ALL roof parameters to find the bug!
      console.log('=== ROOF DEBUG ===', {
        roofType,
        roofOrientation,
        roofHeight,
        roofOverhang,
        buildingHeight,
        'config.roof': config.roof,
        'normalized polygon': normalized,
        'polygon bbox': {
          minX: Math.min(...normalized.map(p => p[0])),
          maxX: Math.max(...normalized.map(p => p[0])),
          minY: Math.min(...normalized.map(p => p[1])),
          maxY: Math.max(...normalized.map(p => p[1])),
        }
      });

      scene.add(createRoofFromPolygon(normalized, buildingHeight, roofHeight, roofType, roofOrientation, roofOverhang));

      // Add scaffolds along actual facade edges (ONLY ENABLED facades)
      // Use bboxCenter instead of centroid for consistent alignment
      enabledFacades.forEach((facade) => {
        scene.add(createScaffoldFacadeAlongEdge(facade, fieldWidth, levelHeight, bboxCenter));
      });

      // Add corners (only if enabled)
      corners.forEach((corner) => {
        const cornerGroup = createScaffoldCorner(corner, enabledFacades, levelHeight, bboxCenter);
        if (cornerGroup) {
          scene.add(cornerGroup);
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
          scene.add(neighborMesh);

          console.log(`Added neighbor ${index + 1}/${neighborBuildings.length} at offset (${offsetX.toFixed(1)}, ${offsetZ.toFixed(1)})`);
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

      const buildingWidth = Math.max(10, nsLength);
      const buildingDepth = Math.max(8, ewLength > 0 ? ewLength : nsLength * 0.6);
      const maxFacadeHeight = enabledFacades.reduce((max, f) => Math.max(max, f.target_height_m || f.levels * levelHeight), 10);
      // Traufhöhe = Gebäudehöhe bis Dachansatz
      const buildingHeight = config.roof?.traufhoehe_m || Math.max(8, maxFacadeHeight - 3);

      // Add simple box building
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

        directionCount[dir] = (directionCount[dir] || 0);
        const stackOffset = directionCount[dir] * 3;
        directionCount[dir]++;

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

      // Add scaffolds (fallback)
      enabledFacades.forEach((facade) => {
        const { offset, dir } = getOffset(facade);
        scene.add(createScaffoldFacade(facade, fieldWidth, levelHeight, offset, dir));
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
