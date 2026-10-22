/**
 * Builds an illustrative 3D model of a property's building from its public details (style,
 * floors, area). Sizes are in metres; the street is on the +z side. THREE and the shared
 * materials are passed in because three.js is loaded on demand.
 */

const FLOOR_HEIGHT = 3.1;

function clamp(value, low, high) {
    return Math.min(high, Math.max(low, value));
}

// Deterministic pseudo-random numbers, so a property always looks the same.
function randomGenerator(seed) {
    let state = Math.floor(seed * 9973) % 2147483647 || 1;
    return () => {
        state = (state * 16807) % 2147483647;
        return (state - 1) / 2147483646;
    };
}

export function buildPropertyModel(THREE, spec, M) {
    const group = new THREE.Group();
    const random = randomGenerator((spec.area || 0) + (spec.land || 0) * 3 + (spec.floors || 0) * 7 + 11);

    function mesh(geometry, mat, x, y, z, parent = group) {
        const m = new THREE.Mesh(geometry, mat);
        m.position.set(x, y, z);
        m.castShadow = true;
        m.receiveShadow = true;
        parent.add(m);
        return m;
    }
    // A box whose texture is scaled to its real size.
    function box(w, h, d, mat, x, y, z, parent = group) {
        return mesh(new THREE.BoxGeometry(w, h, d), M.fit(mat, Math.max(w, d), h), x, y, z, parent);
    }
    // Many identical boxes (windows, frames, posts) drawn in one call.
    function instanced(w, h, d, mat, positions) {
        if (!positions.length) {
            return null;
        }
        const m = new THREE.InstancedMesh(new THREE.BoxGeometry(w, h, d), mat, positions.length);
        const matrix = new THREE.Matrix4();
        positions.forEach(([x, y, z, rotation = 0], index) => {
            matrix.makeRotationY(rotation);
            matrix.setPosition(x, y, z);
            m.setMatrixAt(index, matrix);
        });
        m.castShadow = true;
        m.receiveShadow = true;
        group.add(m);
        return m;
    }
    function surroundings(object) {
        object.userData.surroundings = true;
        return object;
    }

    // Framed windows with sills on the four faces of a block centred at (0, 0) with its floor at `base`.
    function windows(width, depth, floors, base, { size = [1.4, 1.6], spacing = 3.2, litShare = 0.3, skipGround = false, floorHeight = FLOOR_HEIGHT } = {}) {
        const [ww, wh] = size;
        const lit = [];
        const dark = [];
        const frames = [];
        const sills = [];
        for (let floor = skipGround ? 1 : 0; floor < floors; floor++) {
            const y = base + floor * floorHeight + floorHeight * 0.55;
            for (const [length, along, offset, rotation] of [
                [width, "x", depth / 2, 0],
                [width, "x", -depth / 2, 0],
                [depth, "z", width / 2, Math.PI / 2],
                [depth, "z", -width / 2, Math.PI / 2],
            ]) {
                const count = Math.max(1, Math.floor(length / spacing));
                const sign = Math.sign(offset);
                for (let i = 0; i < count; i++) {
                    const position = -length / 2 + (length / count) * (i + 0.5);
                    const at = (out, dy = 0) => (along === "x" ? [position, y + dy, offset + sign * out, rotation] : [offset + sign * out, y + dy, position, rotation]);
                    frames.push(at(0.02));
                    (random() < litShare ? lit : dark).push(at(0.07));
                    sills.push(at(0.1, -wh / 2 - 0.05));
                }
            }
        }
        instanced(ww + 0.16, wh + 0.16, 0.1, M.frame, frames);
        instanced(ww, wh, 0.04, M.glassLit, lit);
        instanced(ww, wh, 0.04, M.glassFacade, dark);
        instanced(ww + 0.3, 0.06, 0.2, M.frameWhite, sills);
    }

    function tree(x, z, scale = 1) {
        surroundings(mesh(new THREE.CylinderGeometry(0.16 * scale, 0.24 * scale, 2.2 * scale, 8), M.trunk, x, 1.1 * scale, z));
        const leaves = random() < 0.5 ? M.leaf : M.leafLight;
        surroundings(mesh(new THREE.IcosahedronGeometry(1.5 * scale, 1), leaves, x, 3.2 * scale, z));
        surroundings(mesh(new THREE.IcosahedronGeometry(1.1 * scale, 1), leaves, x + 0.6 * scale, 3.9 * scale, z - 0.3 * scale));
    }

    function streetLamp(x, z) {
        surroundings(mesh(new THREE.CylinderGeometry(0.06, 0.08, 5, 8), M.metalDark, x, 2.5, z));
        surroundings(mesh(new THREE.BoxGeometry(0.9, 0.08, 0.2), M.metalDark, x + 0.4, 5, z));
        surroundings(mesh(new THREE.BoxGeometry(0.4, 0.06, 0.18), M.lamp, x + 0.7, 4.95, z));
    }

    function car(x, z, color) {
        const body = new THREE.MeshStandardMaterial({ color, roughness: 0.25, metalness: 0.6 });
        const g = surroundings(new THREE.Group());
        g.position.set(x, 0, z);
        group.add(g);
        mesh(new THREE.BoxGeometry(4.2, 0.7, 1.8), body, 0, 0.6, 0, g);
        mesh(new THREE.BoxGeometry(2.3, 0.6, 1.6), body, -0.2, 1.2, 0, g);
        mesh(new THREE.BoxGeometry(2.25, 0.5, 1.65), M.glass, -0.2, 1.2, 0, g);
        for (const [wx, wz] of [[-1.4, 0.85], [1.4, 0.85], [-1.4, -0.85], [1.4, -0.85]]) {
            const wheel = mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.24, 16), M.screen, wx, 0.34, wz, g);
            wheel.rotation.x = Math.PI / 2;
        }
    }

    function gableRoof(width, depth, height, y, mat, overhang = 0.6) {
        const w = width / 2 + overhang;
        const shape = new THREE.Shape();
        shape.moveTo(-w, 0);
        shape.lineTo(w, 0);
        shape.lineTo(0, height);
        shape.lineTo(-w, 0);
        const geometry = new THREE.ExtrudeGeometry(shape, { depth: depth + overhang * 2, bevelEnabled: false });
        geometry.translate(0, 0, -(depth + overhang * 2) / 2);
        // Texture coordinates of the roof slopes, scaled to metres.
        const uv = geometry.attributes.uv;
        for (let i = 0; i < uv.count; i++) {
            uv.setXY(i, uv.getX(i) / 3, uv.getY(i) / 3);
        }
        const roofMat = mat.clone();
        if (roofMat.map) {
            roofMat.map = mat.map.clone();
            roofMat.map.needsUpdate = true;
            roofMat.map.repeat.set(1, 1);
        }
        return mesh(geometry, roofMat, 0, y, 0);
    }

    function entrance(x, z, width = 1.4, height = 2.5) {
        box(width + 0.4, height + 0.3, 0.2, M.frame, x, height / 2 + 0.15, z);
        box(width, height, 0.24, M.door, x, height / 2, z);
        box(width + 1.2, 0.18, 1.4, M.concrete, x, height + 0.5, z + 0.7);
        box(width + 1.6, 0.12, 1.6, M.paving, x, 0.06, z + 0.8);
    }

    let footprint = 20;

    const builders = {
        apartment() {
            const floors = clamp(spec.floors || 8, 1, 60);
            const width = clamp(16 + (spec.bedrooms || 2) * 2, 16, 30);
            const depth = width * 0.62;
            const height = floors * FLOOR_HEIGHT;
            box(width + 2.4, 0.6, depth + 2.4, M.paving, 0, 0.3, 0);
            box(width, FLOOR_HEIGHT, depth, M.concrete, 0, 0.6 + FLOOR_HEIGHT / 2, 0);
            box(width, height - FLOOR_HEIGHT, depth, M.plaster, 0, 0.6 + FLOOR_HEIGHT + (height - FLOOR_HEIGHT) / 2, 0);
            instanced(width + 0.3, 0.22, depth + 0.3, M.trim,
                Array.from({ length: floors }, (_, floor) => [0, 0.6 + (floor + 1) * FLOOR_HEIGHT - 0.11, 0]));
            windows(width, depth, floors, 0.6, { skipGround: true });
            // Balconies with glass railings on the street side
            const balconies = [];
            const count = Math.max(1, Math.floor(width / 6.4));
            for (let floor = 1; floor < floors; floor++) {
                for (let i = 0; i < count; i++) {
                    balconies.push([-width / 2 + (width / count) * (i + 0.5), 0.6 + floor * FLOOR_HEIGHT + 0.1, depth / 2 + 0.75]);
                }
            }
            instanced(3.6, 0.2, 1.5, M.concrete, balconies);
            instanced(3.6, 1.0, 0.04, M.glass, balconies.map(([x, y, z]) => [x, y + 0.6, z + 0.72]));
            instanced(3.62, 0.06, 0.08, M.railing, balconies.map(([x, y, z]) => [x, y + 1.12, z + 0.72]));
            // Shop-front glazing on the ground floor
            instanced(2.6, 2.3, 0.06, M.glassFacade,
                Array.from({ length: Math.floor(width / 3.5) }, (_, i) => [-width / 2 + 1.75 + i * 3.5, 0.6 + 1.4, depth / 2 + 0.04]));
            entrance(0, depth / 2 + 0.1, 2, 2.6);
            // Roof
            box(width + 0.4, 1, depth + 0.4, M.trim, 0, 0.6 + height + 0.5, 0);
            box(width * 0.25, 3, depth * 0.35, M.plasterGrey, width * 0.2, 0.6 + height + 1.5, 0);
            box(3, 2, 3, M.metal, -width * 0.25, 0.6 + height + 1, -depth * 0.15);
            footprint = Math.max(width, depth);
        },
        office() {
            const floors = clamp(spec.floors || 6, 1, 60);
            const side = clamp(Math.sqrt(Math.max(spec.area, 400)) * 0.9, 18, 40);
            const width = side;
            const depth = side * 0.7;
            const storey = FLOOR_HEIGHT * 1.15;
            const height = floors * storey;
            box(width + 6, 0.4, depth + 6, M.paving, 0, 0.2, 0);
            box(width, height, depth, M.glassFacade, 0, 0.4 + height / 2, 0);
            instanced(width + 0.25, 0.4, depth + 0.25, M.metalDark,
                Array.from({ length: floors + 1 }, (_, floor) => [0, 0.4 + floor * storey, 0]));
            const fins = [];
            for (let x = -width / 2; x <= width / 2 + 0.01; x += 2.4) {
                fins.push([x, 0.4 + height / 2, depth / 2 + 0.12], [x, 0.4 + height / 2, -depth / 2 - 0.12]);
            }
            for (let z = -depth / 2; z <= depth / 2 + 0.01; z += 2.4) {
                fins.push([width / 2 + 0.12, 0.4 + height / 2, z], [-width / 2 - 0.12, 0.4 + height / 2, z]);
            }
            instanced(0.14, height, 0.22, M.metal, fins);
            box(9, 0.35, 4.5, M.metalDark, 0, 4.4, depth / 2 + 2.2);
            for (const dx of [-4, 4]) {
                box(0.2, 4.2, 0.2, M.metal, dx, 2.3, depth / 2 + 4.2);
            }
            box(width * 0.35, 3.5, depth * 0.4, M.concrete, 0, 0.4 + height + 1.75, 0);
            footprint = Math.max(width, depth);
        },
        house() {
            const floors = clamp(spec.floors || 2, 1, 3);
            const side = clamp(Math.sqrt(Math.max(spec.area, 90) / floors), 8, 22);
            const width = side * 1.25;
            const depth = side * 0.85;
            const storey = 3.0;
            const height = floors * storey;
            box(width + 1, 0.45, depth + 1, M.paving, 0, 0.22, 0);
            box(width, 1.0, depth, M.brick, 0, 0.45 + 0.5, 0);
            box(width - 0.02, height - 1.0, depth - 0.02, M.plaster, 0, 0.45 + 1 + (height - 1) / 2, 0);
            instanced(width + 0.15, 0.15, depth + 0.15, M.trim,
                Array.from({ length: floors - 1 }, (_, floor) => [0, 0.45 + (floor + 1) * storey, 0]));
            windows(width, depth, floors, 0.45, { size: [1.3, 1.4], spacing: 3.4, litShare: 0.45, floorHeight: storey });
            gableRoof(width, depth, Math.max(2.4, width * 0.28), 0.45 + height, M.roofTiles);
            entrance(width * 0.18, depth / 2 + 0.1, 1.2, 2.3);
            if (spec.area > 160) {
                // Garage wing with a flat roof and a roller door
                const gx = width * 0.5 + 2.6;
                box(5.2, storey, depth * 0.75, M.plasterWarm, gx, 0.45 + storey / 2, depth * 0.12);
                box(4.2, 2.4, 0.12, M.metal, gx, 0.45 + 1.2, depth * 0.12 + depth * 0.375 + 0.07);
                box(5.6, 0.25, depth * 0.85, M.roofSlate, gx, 0.45 + storey + 0.12, depth * 0.12);
                box(4.4, 0.05, 6, M.paving, gx, 0.03, depth / 2 + 3);
            }
            // Garden: path, hedges and a fence around the land
            const plot = clamp(Math.sqrt(Math.max(spec.land, spec.area * 2, 300)), side * 2, 60);
            box(1.6, 0.05, plot / 2 - depth / 2, M.paving, width * 0.18, 0.03, depth / 2 + (plot / 2 - depth / 2) / 2);
            const posts = [];
            for (let t = -plot / 2; t <= plot / 2 + 0.01; t += 2) {
                posts.push([t, 0.6, plot / 2], [t, 0.6, -plot / 2], [plot / 2, 0.6, t], [-plot / 2, 0.6, t]);
            }
            instanced(0.12, 1.2, 0.12, M.fence, posts);
            instanced(plot, 0.1, 0.05, M.fence, [[0, 0.95, plot / 2], [0, 0.95, -plot / 2], [0, 0.45, plot / 2], [0, 0.45, -plot / 2]]);
            instanced(0.05, 0.1, plot, M.fence, [[plot / 2, 0.95, 0], [-plot / 2, 0.95, 0], [plot / 2, 0.45, 0], [-plot / 2, 0.45, 0]]);
            instanced(width * 0.4, 0.9, 0.8, M.hedge, [[-width * 0.25, 0.45, depth / 2 + 1.6], [width * 0.6, 0.45, depth / 2 + 1.6]]);
            footprint = plot;
        },
        shop() {
            const floors = clamp(spec.floors || 2, 1, 4);
            const width = clamp(Math.sqrt(Math.max(spec.area, 60)) * 1.4, 10, 30);
            const depth = width * 0.7;
            const height = floors * FLOOR_HEIGHT + 1;
            box(width + 4, 0.25, depth + 6, M.paving, 0, 0.12, 1);
            box(width, height, depth, M.plasterWarm, 0, 0.25 + height / 2, 0);
            box(width * 0.92, FLOOR_HEIGHT * 0.82, 0.12, M.glassFacade, 0, 0.25 + FLOOR_HEIGHT * 0.45, depth / 2 + 0.04);
            instanced(0.16, FLOOR_HEIGHT * 0.82, 0.2, M.frame,
                Array.from({ length: 6 }, (_, i) => [-width * 0.46 + (width * 0.92 / 5) * i, 0.25 + FLOOR_HEIGHT * 0.45, depth / 2 + 0.1]));
            const stripes = Math.max(6, Math.floor(width / 1.2));
            const stripeWidth = width / stripes;
            const a = [];
            const b = [];
            for (let i = 0; i < stripes; i++) {
                (i % 2 ? b : a).push([-width / 2 + stripeWidth * (i + 0.5), 0.25 + FLOOR_HEIGHT + 0.1, depth / 2 + 0.9]);
            }
            instanced(stripeWidth, 0.1, 1.8, M.awningA, a);
            instanced(stripeWidth, 0.1, 1.8, M.awningB, b);
            box(width * 0.6, 1.1, 0.2, M.sign, 0, 0.25 + height - 0.75, depth / 2 + 0.12);
            box(width * 0.5, 0.5, 0.05, M.lamp, 0, 0.25 + height - 0.75, depth / 2 + 0.24);
            if (floors > 1) {
                windows(width, depth, floors, 0.25, { skipGround: true, litShare: 0.5 });
            }
            footprint = Math.max(width, depth);
        },
        warehouse() {
            const width = clamp(Math.sqrt(Math.max(spec.area, 400)) * 1.2, 20, 60);
            const depth = width * 0.6;
            const height = 8 + clamp((spec.floors || 1) - 1, 0, 3) * 4;
            box(width + 10, 0.25, depth + 14, M.concrete, 0, 0.12, 2);
            box(width, 1.2, depth, M.concrete, 0, 0.25 + 0.6, 0);
            box(width, height - 1.2, depth, M.metal, 0, 0.25 + 1.2 + (height - 1.2) / 2, 0);
            gableRoof(depth, width, 2.5, 0.25 + height, M.roofSlate, 0.4).rotation.y = Math.PI / 2;
            const shutters = Math.max(2, Math.floor(width / 8));
            instanced(4.4, 4.8, 0.25, M.frame,
                Array.from({ length: shutters }, (_, i) => [-width / 2 + (width / shutters) * (i + 0.5), 2.6, depth / 2 + 0.08]));
            instanced(4.0, 4.4, 0.25, M.metalDark,
                Array.from({ length: shutters }, (_, i) => [-width / 2 + (width / shutters) * (i + 0.5), 2.45, depth / 2 + 0.12]));
            instanced(2.4, 0.7, 0.1, M.glassFacade,
                Array.from({ length: shutters * 2 }, (_, i) => [-width / 2 + (width / (shutters * 2)) * (i + 0.5), height - 0.8, depth / 2 + 0.06]));
            footprint = Math.max(width, depth);
        },
        plot() {
            const side = clamp(Math.sqrt(Math.max(spec.land, spec.area, 200)), 15, 90);
            box(side, 0.1, side, M.soil, 0, 0.05, 0);
            const posts = [];
            for (let t = -side / 2; t <= side / 2 + 0.01; t += 2.5) {
                posts.push([t, 0.7, side / 2], [t, 0.7, -side / 2], [side / 2, 0.7, t], [-side / 2, 0.7, t]);
            }
            instanced(0.16, 1.4, 0.16, M.fence, posts);
            instanced(side, 0.06, 0.04, M.metal, [[0, 1.1, side / 2], [0, 1.1, -side / 2], [0, 0.6, side / 2], [0, 0.6, -side / 2]]);
            instanced(0.04, 0.06, side, M.metal, [[side / 2, 1.1, 0], [-side / 2, 1.1, 0], [side / 2, 0.6, 0], [-side / 2, 0.6, 0]]);
            instanced(0.8, 0.8, 0.8, M.concrete, [[side / 2, 0.4, side / 2], [-side / 2, 0.4, side / 2], [side / 2, 0.4, -side / 2], [-side / 2, 0.4, -side / 2]]);
            box(0.15, 2.4, 0.15, M.fence, side * 0.3, 1.2, side / 2 + 1.2);
            box(2.6, 1.4, 0.12, M.sign, side * 0.3, 2.6, side / 2 + 1.2);
            footprint = side;
        },
    };

    (builders[spec.kind] || builders.apartment)();

    // Surroundings: lawn, a road with a pavement, street lamps, trees and a parked car.
    const radius = footprint * 1.6 + 25;
    const ground = surroundings(new THREE.Mesh(new THREE.CircleGeometry(radius, 64), M.fit(M.grass, radius * 2, radius * 2)));
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    group.add(ground);
    const roadZ = footprint / 2 + 10;
    const road = surroundings(new THREE.Mesh(new THREE.PlaneGeometry(radius * 2, 7), M.fit(M.asphalt, radius * 2, 7)));
    road.rotation.x = -Math.PI / 2;
    road.position.set(0, 0.02, roadZ);
    road.receiveShadow = true;
    group.add(road);
    const pavement = surroundings(new THREE.Mesh(new THREE.BoxGeometry(radius * 2, 0.15, 2.4), M.fit(M.paving, radius * 2, 2.4)));
    pavement.position.set(0, 0.075, roadZ - 4.7);
    pavement.receiveShadow = true;
    group.add(pavement);
    for (let x = -footprint; x <= footprint; x += Math.max(12, footprint / 2)) {
        streetLamp(x, roadZ - 5.5);
    }
    car(footprint * 0.35, roadZ + 1.6, [0xb22222, 0x1f4e79, 0xdedede, 0x2f2f2f][Math.floor(random() * 4)]);
    const trees = clamp(Math.round(footprint / 3.5), 5, 16);
    for (let i = 0; i < trees; i++) {
        const angle = (i / trees) * Math.PI * 2 + random() * 0.4;
        const distance = footprint * 0.72 + 4 + random() * 5;
        const x = Math.cos(angle) * distance;
        const z = Math.sin(angle) * distance;
        if (z > roadZ - 7 && z < roadZ + 5) {
            continue; // keep the road and pavement clear
        }
        tree(x, z, 0.8 + random() * 0.6);
    }
    return group;
}
