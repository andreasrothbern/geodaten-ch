import { describe, it, expect } from 'vitest';
import {
  calculateBoundingBox,
  shouldRidgeRunAlongZ,
  createSatteldachGeometry,
  createFlachdachGeometry,
  createPultdachGeometry,
  validateRoofGeometry,
  getVertex,
  getVertices,
  calculateTriangleNormal,
  getAllTriangleNormals,
  type Point2D,
} from './roofGeometry';

describe('roofGeometry', () => {
  // Simple rectangular building polygon (10m x 8m)
  const rectangularPolygon: Point2D[] = [
    { x: -5, z: -4 },  // NW
    { x: 5, z: -4 },   // NE
    { x: 5, z: 4 },    // SE
    { x: -5, z: 4 },   // SW
  ];

  describe('calculateBoundingBox', () => {
    it('should calculate correct bounding box', () => {
      const bbox = calculateBoundingBox(rectangularPolygon);

      expect(bbox.minX).toBe(-5);
      expect(bbox.maxX).toBe(5);
      expect(bbox.minZ).toBe(-4);
      expect(bbox.maxZ).toBe(4);
      expect(bbox.centerX).toBe(0);
      expect(bbox.centerZ).toBe(0);
      expect(bbox.width).toBe(10);
      expect(bbox.depth).toBe(8);
    });

    it('should handle offset polygon', () => {
      const offsetPolygon: Point2D[] = [
        { x: 10, z: 20 },
        { x: 20, z: 20 },
        { x: 20, z: 30 },
        { x: 10, z: 30 },
      ];
      const bbox = calculateBoundingBox(offsetPolygon);

      expect(bbox.minX).toBe(10);
      expect(bbox.maxX).toBe(20);
      expect(bbox.minZ).toBe(20);
      expect(bbox.maxZ).toBe(30);
      expect(bbox.centerX).toBe(15);
      expect(bbox.centerZ).toBe(25);
    });
  });

  describe('shouldRidgeRunAlongZ', () => {
    it('should return true for O-W orientation', () => {
      expect(shouldRidgeRunAlongZ('O-W', 10, 8)).toBe(true);
    });

    it('should return true for E-W orientation', () => {
      expect(shouldRidgeRunAlongZ('E-W', 10, 8)).toBe(true);
    });

    it('should return false for N-S orientation', () => {
      expect(shouldRidgeRunAlongZ('N-S', 10, 8)).toBe(false);
    });

    it('should use longer dimension as fallback', () => {
      // Wider building (width > depth) → ridge along shorter axis (Z)
      expect(shouldRidgeRunAlongZ(undefined, 20, 10)).toBe(false);
      // Deeper building (depth > width) → ridge along longer axis (Z)
      expect(shouldRidgeRunAlongZ(undefined, 10, 20)).toBe(true);
    });
  });

  describe('createSatteldachGeometry', () => {
    describe('O-W orientation (ridge runs N-S)', () => {
      const geometry = createSatteldachGeometry(rectangularPolygon, 6, 9, 'O-W');

      it('should create valid geometry', () => {
        const validation = validateRoofGeometry(geometry);
        expect(validation.valid).toBe(true);
        expect(validation.errors).toHaveLength(0);
      });

      it('should have 6 vertices', () => {
        expect(geometry.vertices.length / 3).toBe(6);
      });

      it('should have 8 triangles (24 indices)', () => {
        // 2 slopes × 2 triangles each + 2 gables × 1 triangle each = 6 triangles
        // Wait, let's count: West slope (2) + East slope (2) + North gable (1) + South gable (1) = 6
        expect(geometry.indices.length / 3).toBe(6);
      });

      it('should have ridge at center X', () => {
        const vertices = getVertices(geometry);
        // Vertices 4 and 5 are ridge points
        const ridgeNorth = vertices[4];
        const ridgeSouth = vertices[5];

        expect(ridgeNorth[0]).toBe(0); // centerX
        expect(ridgeSouth[0]).toBe(0); // centerX
      });

      it('should have ridge at peak height', () => {
        const vertices = getVertices(geometry);
        const ridgeNorth = vertices[4];
        const ridgeSouth = vertices[5];

        expect(ridgeNorth[1]).toBe(9); // yPeak
        expect(ridgeSouth[1]).toBe(9); // yPeak
      });

      it('should have ridge spanning full Z extent', () => {
        const vertices = getVertices(geometry);
        const ridgeNorth = vertices[4];
        const ridgeSouth = vertices[5];

        expect(ridgeNorth[2]).toBe(-4); // minZ (North)
        expect(ridgeSouth[2]).toBe(4);  // maxZ (South)
      });

      it('should have eave corners at trauf height', () => {
        const vertices = getVertices(geometry);
        // Vertices 0-3 are eave corners
        for (let i = 0; i < 4; i++) {
          expect(vertices[i][1]).toBe(6); // yEaves
        }
      });

      it('should have West eave at minX', () => {
        const vertices = getVertices(geometry);
        // NW (0) and SW (1) should be at minX
        expect(vertices[0][0]).toBe(-5);
        expect(vertices[1][0]).toBe(-5);
      });

      it('should have East eave at maxX', () => {
        const vertices = getVertices(geometry);
        // NE (2) and SE (3) should be at maxX
        expect(vertices[2][0]).toBe(5);
        expect(vertices[3][0]).toBe(5);
      });
    });

    describe('N-S orientation (ridge runs E-W)', () => {
      const geometry = createSatteldachGeometry(rectangularPolygon, 6, 9, 'N-S');

      it('should create valid geometry', () => {
        const validation = validateRoofGeometry(geometry);
        expect(validation.valid).toBe(true);
      });

      it('should have ridge at center Z', () => {
        const vertices = getVertices(geometry);
        // Vertices 4 and 5 are ridge points
        const ridgeWest = vertices[4];
        const ridgeEast = vertices[5];

        expect(ridgeWest[2]).toBe(0); // centerZ
        expect(ridgeEast[2]).toBe(0); // centerZ
      });

      it('should have ridge spanning full X extent', () => {
        const vertices = getVertices(geometry);
        const ridgeWest = vertices[4];
        const ridgeEast = vertices[5];

        expect(ridgeWest[0]).toBe(-5); // minX (West)
        expect(ridgeEast[0]).toBe(5);  // maxX (East)
      });
    });
  });

  describe('createFlachdachGeometry', () => {
    const geometry = createFlachdachGeometry(rectangularPolygon, 8);

    it('should create valid geometry', () => {
      const validation = validateRoofGeometry(geometry);
      expect(validation.valid).toBe(true);
    });

    it('should have all vertices at same height', () => {
      const vertices = getVertices(geometry);
      vertices.forEach(v => {
        expect(v[1]).toBe(8);
      });
    });

    it('should preserve polygon XZ coordinates', () => {
      const vertices = getVertices(geometry);
      rectangularPolygon.forEach((p, i) => {
        expect(vertices[i][0]).toBe(p.x);
        expect(vertices[i][2]).toBe(p.z);
      });
    });
  });

  describe('createPultdachGeometry', () => {
    const geometry = createPultdachGeometry(rectangularPolygon, 6, 9);

    it('should create valid geometry', () => {
      const validation = validateRoofGeometry(geometry);
      expect(validation.valid).toBe(true);
    });

    it('should have varying heights based on Z position', () => {
      const vertices = getVertices(geometry);

      // North points (minZ = -4) should be at yHigh (9)
      const northPoints = vertices.filter((_, i) =>
        rectangularPolygon[i].z === -4
      );
      northPoints.forEach(v => {
        expect(v[1]).toBeCloseTo(9, 5);
      });

      // South points (maxZ = 4) should be at yLow (6)
      const southPoints = vertices.filter((_, i) =>
        rectangularPolygon[i].z === 4
      );
      southPoints.forEach(v => {
        expect(v[1]).toBeCloseTo(6, 5);
      });
    });
  });

  describe('validateRoofGeometry', () => {
    it('should pass for valid geometry', () => {
      const valid = {
        vertices: [0, 0, 0, 1, 0, 0, 0, 1, 0],
        indices: [0, 1, 2],
      };
      const result = validateRoofGeometry(valid);
      expect(result.valid).toBe(true);
    });

    it('should fail for invalid vertex count', () => {
      const invalid = {
        vertices: [0, 0], // Not multiple of 3
        indices: [0],
      };
      const result = validateRoofGeometry(invalid);
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('not multiple of 3');
    });

    it('should fail for invalid indices', () => {
      const invalid = {
        vertices: [0, 0, 0, 1, 0, 0, 0, 1, 0],
        indices: [0, 1, 5], // Index 5 is out of bounds
      };
      const result = validateRoofGeometry(invalid);
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('Invalid indices');
    });

    it('should fail for degenerate triangles', () => {
      const invalid = {
        vertices: [0, 0, 0, 1, 0, 0, 0, 1, 0],
        indices: [0, 0, 1], // Same vertex twice
      };
      const result = validateRoofGeometry(invalid);
      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('Degenerate');
    });
  });

  describe('getVertex / getVertices', () => {
    const geometry = {
      vertices: [1, 2, 3, 4, 5, 6, 7, 8, 9],
      indices: [0, 1, 2],
    };

    it('should extract single vertex', () => {
      expect(getVertex(geometry, 0)).toEqual([1, 2, 3]);
      expect(getVertex(geometry, 1)).toEqual([4, 5, 6]);
      expect(getVertex(geometry, 2)).toEqual([7, 8, 9]);
    });

    it('should extract all vertices', () => {
      const vertices = getVertices(geometry);
      expect(vertices).toHaveLength(3);
      expect(vertices[0]).toEqual([1, 2, 3]);
      expect(vertices[1]).toEqual([4, 5, 6]);
      expect(vertices[2]).toEqual([7, 8, 9]);
    });
  });

  describe('Real-world scenarios', () => {
    it('should handle Knospenweg 4 scenario (O-W, rectangular)', () => {
      // Simulated building dimensions similar to Knospenweg 4
      const knospenweg: Point2D[] = [
        { x: -6, z: -5 },   // NW
        { x: 6, z: -5 },    // NE
        { x: 6, z: 5 },     // SE
        { x: -6, z: 5 },    // SW
      ];

      const geometry = createSatteldachGeometry(knospenweg, 7.5, 10.5, 'O-W');
      const validation = validateRoofGeometry(geometry);

      expect(validation.valid).toBe(true);

      const vertices = getVertices(geometry);

      // Ridge should be at X=0 (center)
      const ridgeVertices = vertices.filter(v => v[1] === 10.5);
      expect(ridgeVertices).toHaveLength(2);
      ridgeVertices.forEach(v => {
        expect(v[0]).toBe(0); // X = center
      });

      // Ridge should span from Z=-5 to Z=5
      const ridgeZs = ridgeVertices.map(v => v[2]).sort((a, b) => a - b);
      expect(ridgeZs[0]).toBe(-5);
      expect(ridgeZs[1]).toBe(5);

      // Eave vertices should be at corners
      const eaveVertices = vertices.filter(v => v[1] === 7.5);
      expect(eaveVertices).toHaveLength(4);

      // West eave at X=-6
      const westEave = eaveVertices.filter(v => v[0] === -6);
      expect(westEave).toHaveLength(2);

      // East eave at X=6
      const eastEave = eaveVertices.filter(v => v[0] === 6);
      expect(eastEave).toHaveLength(2);
    });

    it('should handle narrow building with auto-orientation', () => {
      // Narrow building (width=4, depth=12)
      const narrow: Point2D[] = [
        { x: -2, z: -6 },
        { x: 2, z: -6 },
        { x: 2, z: 6 },
        { x: -2, z: 6 },
      ];

      // No orientation specified - should auto-detect
      const geometry = createSatteldachGeometry(narrow, 5, 8);
      const validation = validateRoofGeometry(geometry);

      expect(validation.valid).toBe(true);

      // For narrow building (depth > width), ridge should run along Z
      const vertices = getVertices(geometry);
      const ridgeVertices = vertices.filter(v => v[1] === 8);

      // Check ridge runs along Z (X should be center = 0)
      expect(ridgeVertices[0][0]).toBe(0);
      expect(ridgeVertices[1][0]).toBe(0);
    });

    it('should handle wide building with auto-orientation', () => {
      // Wide building (width=12, depth=4)
      const wide: Point2D[] = [
        { x: -6, z: -2 },
        { x: 6, z: -2 },
        { x: 6, z: 2 },
        { x: -6, z: 2 },
      ];

      const geometry = createSatteldachGeometry(wide, 5, 8);
      const validation = validateRoofGeometry(geometry);

      expect(validation.valid).toBe(true);

      // For wide building (width > depth), ridge should run along X
      const vertices = getVertices(geometry);
      const ridgeVertices = vertices.filter(v => v[1] === 8);

      // Check ridge runs along X (Z should be center = 0)
      expect(ridgeVertices[0][2]).toBe(0);
      expect(ridgeVertices[1][2]).toBe(0);
    });
  });

  describe('Triangle normals (winding order validation)', () => {
    describe('O-W orientation (ridge N-S)', () => {
      const geometry = createSatteldachGeometry(rectangularPolygon, 6, 9, 'O-W');
      const normals = getAllTriangleNormals(geometry);

      // Triangle layout for O-W:
      // 0,1: West slope (2 triangles)
      // 2,3: East slope (2 triangles)
      // 4: North gable
      // 5: South gable

      it('should have West slope normals pointing West-Up (-X, +Y)', () => {
        // Triangles 0 and 1 are West slope
        const westNormal1 = normals[0];
        const westNormal2 = normals[1];

        // X component should be negative (pointing West)
        expect(westNormal1[0]).toBeLessThan(0);
        expect(westNormal2[0]).toBeLessThan(0);

        // Y component should be positive (pointing Up)
        expect(westNormal1[1]).toBeGreaterThan(0);
        expect(westNormal2[1]).toBeGreaterThan(0);
      });

      it('should have East slope normals pointing East-Up (+X, +Y)', () => {
        // Triangles 2 and 3 are East slope
        const eastNormal1 = normals[2];
        const eastNormal2 = normals[3];

        // X component should be positive (pointing East)
        expect(eastNormal1[0]).toBeGreaterThan(0);
        expect(eastNormal2[0]).toBeGreaterThan(0);

        // Y component should be positive (pointing Up)
        expect(eastNormal1[1]).toBeGreaterThan(0);
        expect(eastNormal2[1]).toBeGreaterThan(0);
      });

      it('should have North gable normal pointing North (-Z)', () => {
        // Triangle 4 is North gable
        const northNormal = normals[4];

        // Z component should be negative (pointing North)
        expect(northNormal[2]).toBeLessThan(0);
      });

      it('should have South gable normal pointing South (+Z)', () => {
        // Triangle 5 is South gable
        const southNormal = normals[5];

        // Z component should be positive (pointing South)
        expect(southNormal[2]).toBeGreaterThan(0);
      });

      it('should have all roof slope normals with positive Y (pointing upward)', () => {
        // All roof faces (0-3) should point somewhat upward
        for (let i = 0; i < 4; i++) {
          expect(normals[i][1]).toBeGreaterThan(0);
        }
      });
    });

    describe('N-S orientation (ridge E-W)', () => {
      const geometry = createSatteldachGeometry(rectangularPolygon, 6, 9, 'N-S');
      const normals = getAllTriangleNormals(geometry);

      // Triangle layout for N-S:
      // 0,1: North slope (2 triangles)
      // 2,3: South slope (2 triangles)
      // 4: West gable
      // 5: East gable

      it('should have North slope normals pointing North-Up (-Z, +Y)', () => {
        const northNormal1 = normals[0];
        const northNormal2 = normals[1];

        // Z component should be negative (pointing North)
        expect(northNormal1[2]).toBeLessThan(0);
        expect(northNormal2[2]).toBeLessThan(0);

        // Y component should be positive (pointing Up)
        expect(northNormal1[1]).toBeGreaterThan(0);
        expect(northNormal2[1]).toBeGreaterThan(0);
      });

      it('should have South slope normals pointing South-Up (+Z, +Y)', () => {
        const southNormal1 = normals[2];
        const southNormal2 = normals[3];

        // Z component should be positive (pointing South)
        expect(southNormal1[2]).toBeGreaterThan(0);
        expect(southNormal2[2]).toBeGreaterThan(0);

        // Y component should be positive (pointing Up)
        expect(southNormal1[1]).toBeGreaterThan(0);
        expect(southNormal2[1]).toBeGreaterThan(0);
      });

      it('should have West gable normal pointing West (-X)', () => {
        const westNormal = normals[4];
        expect(westNormal[0]).toBeLessThan(0);
      });

      it('should have East gable normal pointing East (+X)', () => {
        const eastNormal = normals[5];
        expect(eastNormal[0]).toBeGreaterThan(0);
      });
    });

    describe('calculateTriangleNormal', () => {
      it('should calculate correct normal for simple triangle', () => {
        // Triangle in XY plane, counter-clockwise from +Z
        const geometry = {
          vertices: [
            0, 0, 0,  // v0: origin
            1, 0, 0,  // v1: +X
            0, 1, 0,  // v2: +Y
          ],
          indices: [0, 1, 2],
        };

        const normal = calculateTriangleNormal(geometry, 0);

        // Normal should point in +Z direction
        expect(normal[0]).toBeCloseTo(0);
        expect(normal[1]).toBeCloseTo(0);
        expect(normal[2]).toBeCloseTo(1);
      });

      it('should return normalized vector', () => {
        const geometry = {
          vertices: [
            0, 0, 0,
            10, 0, 0,  // Large triangle
            0, 10, 0,
          ],
          indices: [0, 1, 2],
        };

        const normal = calculateTriangleNormal(geometry, 0);
        const length = Math.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2);

        expect(length).toBeCloseTo(1);
      });
    });
  });
});
