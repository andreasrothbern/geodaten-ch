/**
 * Roof Geometry Utilities
 *
 * Pure functions for calculating roof vertices and indices.
 * Extracted for testability.
 */

export interface Point2D {
  x: number;
  z: number;
}

export interface RoofGeometry {
  vertices: number[];  // [x, y, z, x, y, z, ...]
  indices: number[];   // Triangle indices
}

export type RoofType = 'flachdach' | 'satteldach' | 'pultdach' | 'walmdach';
export type RoofOrientation = 'O-W' | 'E-W' | 'N-S' | 'NW-SO' | 'NO-SW' | string;

/**
 * Calculate bounding box from polygon points
 */
export function calculateBoundingBox(points: Point2D[]) {
  const minX = Math.min(...points.map(p => p.x));
  const maxX = Math.max(...points.map(p => p.x));
  const minZ = Math.min(...points.map(p => p.z));
  const maxZ = Math.max(...points.map(p => p.z));

  return {
    minX,
    maxX,
    minZ,
    maxZ,
    centerX: (minX + maxX) / 2,
    centerZ: (minZ + maxZ) / 2,
    width: maxX - minX,
    depth: maxZ - minZ,
  };
}

/**
 * Determine if ridge should run along Z axis (N-S direction)
 */
export function shouldRidgeRunAlongZ(
  orientation: RoofOrientation | undefined,
  bboxWidth: number,
  bboxDepth: number
): boolean {
  if (orientation === 'O-W' || orientation === 'E-W') {
    // Roof slopes East/West → ridge runs North-South (along Z)
    return true;
  } else if (orientation === 'N-S') {
    // Roof slopes North/South → ridge runs East-West (along X)
    return false;
  }
  // Fallback: ridge along longer building dimension
  return bboxDepth > bboxWidth;
}

/**
 * Create Satteldach (gable roof) geometry
 *
 * For O-W orientation (ridgeAlongZ = true):
 * - Ridge runs from South to North (along Z axis)
 * - Roof slopes down to East and West
 * - Gables face North and South
 *
 * Vertex layout (ridgeAlongZ = true):
 *       Ridge-N (5)
 *          /|\
 *         / | \
 *   NW(1)/  |  \NE(3)
 *        |  |  |
 *   SW(0)\  |  /SE(2)
 *         \ | /
 *          \|/
 *       Ridge-S (4)
 */
export function createSatteldachGeometry(
  points: Point2D[],
  yEaves: number,
  yPeak: number,
  orientation?: RoofOrientation
): RoofGeometry {
  const bbox = calculateBoundingBox(points);
  const ridgeAlongZ = shouldRidgeRunAlongZ(orientation, bbox.width, bbox.depth);

  const vertices: number[] = [];
  const indices: number[] = [];

  if (ridgeAlongZ) {
    // Ridge runs N-S (along Z): roof slopes to East and West
    //
    // Top view (looking down, +Y is up):
    //   -Z (North)
    //      ^
    //      |
    //  NW--+--NE
    //  |   R   |   R = Ridge (centerX)
    //  SW--+--SE
    //      |
    //      v
    //   +Z (South)
    //
    // -X (West) <---> +X (East)

    // Eave corners at trauf height
    vertices.push(bbox.minX, yEaves, bbox.minZ); // 0: NW corner (North-West, low Z, low X)
    vertices.push(bbox.minX, yEaves, bbox.maxZ); // 1: SW corner (South-West, high Z, low X)
    vertices.push(bbox.maxX, yEaves, bbox.minZ); // 2: NE corner (North-East, low Z, high X)
    vertices.push(bbox.maxX, yEaves, bbox.maxZ); // 3: SE corner (South-East, high Z, high X)

    // Ridge points at first height (center X, spanning Z)
    vertices.push(bbox.centerX, yPeak, bbox.minZ); // 4: Ridge North
    vertices.push(bbox.centerX, yPeak, bbox.maxZ); // 5: Ridge South

    // Create triangles (counter-clockwise winding for outward-facing normals)
    indices.push(
      // West roof slope (faces West, -X direction)
      // Quad: NW(0), SW(1), Ridge-S(5), Ridge-N(4)
      0, 4, 5,  // NW, Ridge-N, Ridge-S
      0, 5, 1,  // NW, Ridge-S, SW

      // East roof slope (faces East, +X direction)
      // Quad: NE(2), Ridge-N(4), Ridge-S(5), SE(3)
      2, 5, 4,  // NE, Ridge-S, Ridge-N (reversed winding)
      2, 3, 5,  // NE, SE, Ridge-S

      // North gable (faces North, -Z direction)
      // Triangle: NW(0), NE(2), Ridge-N(4)
      0, 2, 4,  // NW, NE, Ridge-N

      // South gable (faces South, +Z direction)
      // Triangle: SW(1), SE(3), Ridge-S(5)
      1, 5, 3,  // SW, Ridge-S, SE (reversed)
    );
  } else {
    // Ridge runs E-W (along X): roof slopes to North and South
    //
    // Top view:
    //   -Z (North)
    //      ^
    //      |
    //  NW-----NE
    //  |   R   |   R = Ridge (centerZ)
    //  SW-----SE
    //      |
    //      v
    //   +Z (South)

    // Eave corners at trauf height
    vertices.push(bbox.minX, yEaves, bbox.minZ); // 0: NW corner
    vertices.push(bbox.maxX, yEaves, bbox.minZ); // 1: NE corner
    vertices.push(bbox.minX, yEaves, bbox.maxZ); // 2: SW corner
    vertices.push(bbox.maxX, yEaves, bbox.maxZ); // 3: SE corner

    // Ridge points at first height (center Z, spanning X)
    vertices.push(bbox.minX, yPeak, bbox.centerZ); // 4: Ridge West
    vertices.push(bbox.maxX, yPeak, bbox.centerZ); // 5: Ridge East

    indices.push(
      // North roof slope (faces North, -Z direction)
      // Quad: NW(0), NE(1), Ridge-E(5), Ridge-W(4)
      0, 4, 5,  // NW, Ridge-W, Ridge-E
      0, 5, 1,  // NW, Ridge-E, NE

      // South roof slope (faces South, +Z direction)
      // Quad: SW(2), Ridge-W(4), Ridge-E(5), SE(3)
      2, 5, 4,  // SW, Ridge-E, Ridge-W (reversed)
      2, 3, 5,  // SW, SE, Ridge-E

      // West gable (faces West, -X direction)
      // Triangle: NW(0), SW(2), Ridge-W(4)
      0, 2, 4,  // NW, SW, Ridge-W

      // East gable (faces East, +X direction)
      // Triangle: NE(1), SE(3), Ridge-E(5)
      1, 5, 3,  // NE, Ridge-E, SE
    );
  }

  return { vertices, indices };
}

/**
 * Create Flachdach (flat roof) geometry
 */
export function createFlachdachGeometry(
  points: Point2D[],
  yHeight: number
): RoofGeometry {
  const vertices: number[] = [];
  const indices: number[] = [];

  // Add all polygon points at roof height
  points.forEach(p => {
    vertices.push(p.x, yHeight, p.z);
  });

  // Triangulate using fan triangulation (works for convex polygons)
  for (let i = 1; i < points.length - 1; i++) {
    indices.push(0, i, i + 1);
  }

  return { vertices, indices };
}

/**
 * Create Pultdach (shed/mono-pitch roof) geometry
 */
export function createPultdachGeometry(
  points: Point2D[],
  yLow: number,
  yHigh: number,
  orientation?: RoofOrientation
): RoofGeometry {
  const bbox = calculateBoundingBox(points);
  const vertices: number[] = [];
  const indices: number[] = [];

  // Determine slope direction (default: high at North/-Z, low at South/+Z)
  const slopeAlongZ = orientation === 'N-S' || orientation === undefined;

  // Add polygon points with height based on position
  points.forEach(p => {
    let y: number;
    if (slopeAlongZ) {
      // Height varies with Z: low at maxZ (South), high at minZ (North)
      const t = (p.z - bbox.minZ) / (bbox.maxZ - bbox.minZ);
      y = yHigh + t * (yLow - yHigh);
    } else {
      // Height varies with X: low at maxX (East), high at minX (West)
      const t = (p.x - bbox.minX) / (bbox.maxX - bbox.minX);
      y = yHigh + t * (yLow - yHigh);
    }
    vertices.push(p.x, y, p.z);
  });

  // Triangulate
  for (let i = 1; i < points.length - 1; i++) {
    indices.push(0, i, i + 1);
  }

  return { vertices, indices };
}

/**
 * Validate roof geometry
 */
export function validateRoofGeometry(geometry: RoofGeometry): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check vertex count is multiple of 3
  if (geometry.vertices.length % 3 !== 0) {
    errors.push(`Vertices length ${geometry.vertices.length} is not multiple of 3`);
  }

  // Check index count is multiple of 3 (triangles)
  if (geometry.indices.length % 3 !== 0) {
    errors.push(`Indices length ${geometry.indices.length} is not multiple of 3 (triangles)`);
  }

  // Check all indices are valid
  const vertexCount = geometry.vertices.length / 3;
  const invalidIndices = geometry.indices.filter(i => i < 0 || i >= vertexCount);
  if (invalidIndices.length > 0) {
    errors.push(`Invalid indices found: ${invalidIndices.join(', ')} (vertex count: ${vertexCount})`);
  }

  // Check for degenerate triangles (all same vertex)
  for (let i = 0; i < geometry.indices.length; i += 3) {
    const a = geometry.indices[i];
    const b = geometry.indices[i + 1];
    const c = geometry.indices[i + 2];
    if (a === b || b === c || a === c) {
      errors.push(`Degenerate triangle at index ${i / 3}: [${a}, ${b}, ${c}]`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Get vertex as [x, y, z] tuple
 */
export function getVertex(geometry: RoofGeometry, index: number): [number, number, number] {
  const base = index * 3;
  return [
    geometry.vertices[base],
    geometry.vertices[base + 1],
    geometry.vertices[base + 2],
  ];
}

/**
 * Get all vertices as array of [x, y, z] tuples
 */
export function getVertices(geometry: RoofGeometry): [number, number, number][] {
  const result: [number, number, number][] = [];
  for (let i = 0; i < geometry.vertices.length / 3; i++) {
    result.push(getVertex(geometry, i));
  }
  return result;
}
