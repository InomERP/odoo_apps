/**
 * Interior of a property: a floor plan generated from its public details (style, bedrooms,
 * bathrooms, area, furnishing), built as rooms with walls, doors, windows and furniture.
 * Sizes are in metres; the street side is +z. THREE is passed in (loaded on demand).
 */
import { makeLabel } from "./property_3d_materials";

const EXTERIOR_WALL = 0.25;
const INTERIOR_WALL = 0.12;
const DOOR_HEIGHT = 2.1;
const CORRIDOR = 1.3;

function clamp(value, low, high) {
    return Math.min(high, Math.max(low, value));
}

// ---------------------------------------------------------------- floor plans

const ROOM_INFO = {
    living: { label: "Living & Dining", floor: "floorWood" },
    kitchen: { label: "Kitchen", floor: "floorTiles" },
    bedroom: { label: "Bedroom", floor: "floorWood" },
    master: { label: "Master Bedroom", floor: "floorWood" },
    bathroom: { label: "Bathroom", floor: "floorBath", wall: "wallBath" },
    hall: { label: "Hallway", floor: "floorTiles" },
    stairs: { label: "Staircase", floor: "floorWood" },
    storage: { label: "Storage", floor: "floorTiles" },
    balcony: { label: "Balcony", floor: "floorTiles" },
    workspace: { label: "Open Workspace", floor: "floorCarpet" },
    meeting: { label: "Meeting Room", floor: "floorCarpet" },
    cabin: { label: "Manager Cabin", floor: "floorCarpet" },
    pantry: { label: "Pantry", floor: "floorTiles" },
    restroom: { label: "Restroom", floor: "floorBath", wall: "wallBath" },
    sales: { label: "Sales Floor", floor: "floorTiles" },
    hallStore: { label: "Warehouse Hall", floor: "floorConcrete" },
    office: { label: "Site Office", floor: "floorTiles" },
};

/**
 * One storey laid out in three bands, front to back: `front` rooms along the street side,
 * a corridor, and `back` rooms opening onto it. Widths are shared by weight.
 */
function bandFloor(width, depth, front, back, { frontShare = 0.46, corridor = true } = {}) {
    const rooms = [];
    const walls = [];
    const corridorDepth = corridor && back.length ? CORRIDOR : 0;
    const frontDepth = back.length ? depth * frontShare : depth;
    const backDepth = depth - frontDepth - corridorDepth;
    const zFront = depth / 2;
    const zFrontInner = zFront - frontDepth;
    const zBack = -depth / 2;
    const zBackInner = zBack + backDepth;

    function columns(list) {
        const total = list.reduce((sum, room) => sum + (room.weight || 1), 0);
        let x = -width / 2;
        return list.map((room) => {
            const w = (width * (room.weight || 1)) / total;
            const column = { ...room, x0: x, x1: x + w };
            x += w;
            return column;
        });
    }

    const frontRooms = columns(front).map((room) => ({ ...room, z0: zFrontInner, z1: zFront, side: "front" }));
    const backRooms = columns(back).map((room) => ({ ...room, z0: zBack, z1: zBackInner, side: "back" }));
    rooms.push(...frontRooms, ...backRooms);
    if (corridorDepth) {
        rooms.push({ type: "hall", x0: -width / 2, x1: width / 2, z0: zBackInner, z1: zFrontInner, side: "hall" });
    }

    // Exterior walls: windows in each room on the street and back facades, entrance on the side.
    const frontWall = { a: [-width / 2, zFront], b: [width / 2, zFront], exterior: true, openings: [] };
    for (const room of frontRooms) {
        const w = room.x1 - room.x0;
        if (room.balconyDoor) {
            frontWall.openings.push({ at: room.x0 + w * 0.3 + width / 2, width: 1.8, kind: "glassDoor" });
            frontWall.openings.push({ at: room.x0 + w * 0.72 + width / 2, width: Math.min(2.2, w * 0.3), kind: "window" });
        } else if (room.shopFront) {
            frontWall.openings.push({ at: room.x0 + w * 0.5 + width / 2, width: Math.min(2, w * 0.2), kind: "glassDoor" });
            frontWall.openings.push({ at: room.x0 + w * 0.2 + width / 2, width: w * 0.28, kind: "window", sill: 0.3, height: 2.2 });
            frontWall.openings.push({ at: room.x0 + w * 0.8 + width / 2, width: w * 0.28, kind: "window", sill: 0.3, height: 2.2 });
        } else {
            const count = Math.max(1, Math.floor(w / 3.2));
            for (let i = 0; i < count; i++) {
                frontWall.openings.push({ at: room.x0 + (w / count) * (i + 0.5) + width / 2, width: Math.min(1.6, w / count - 0.6), kind: "window" });
            }
        }
    }
    const backWall = { a: [-width / 2, zBack], b: [width / 2, zBack], exterior: true, openings: [] };
    for (const room of backRooms) {
        const w = room.x1 - room.x0;
        if (room.type === "stairs") {
            continue;
        }
        const wet = room.type === "bathroom" || room.type === "restroom";
        backWall.openings.push({
            at: room.x0 + w / 2 + width / 2, width: wet ? Math.min(0.8, w - 0.4) : Math.min(1.6, w - 0.8), kind: "window",
            sill: wet ? 1.5 : 0.9, height: wet ? 0.6 : 1.4,
        });
    }
    const entranceZ = corridorDepth ? (zBackInner + zFrontInner) / 2 : zFront - Math.min(2, frontDepth / 2);
    const sideRight = { a: [width / 2, zBack], b: [width / 2, zFront], exterior: true, openings: [] };
    sideRight.openings.push({ at: entranceZ - zBack, width: 1.0, kind: "door", entrance: true });
    const sideLeft = { a: [-width / 2, zBack], b: [-width / 2, zFront], exterior: true, openings: [] };
    walls.push(frontWall, backWall, sideRight, sideLeft);

    // Interior walls
    if (back.length) {
        if (corridorDepth) {
            const corridorBack = { a: [-width / 2, zBackInner], b: [width / 2, zBackInner], openings: [] };
            for (const room of backRooms) {
                corridorBack.openings.push({
                    at: (room.x0 + room.x1) / 2 + width / 2, width: room.type === "stairs" ? room.x1 - room.x0 - 0.3 : 0.9,
                    kind: room.type === "stairs" ? "opening" : "door",
                });
            }
            walls.push(corridorBack);
            const corridorFront = { a: [-width / 2, zFrontInner], b: [width / 2, zFrontInner], openings: [] };
            for (const room of frontRooms) {
                const w = room.x1 - room.x0;
                corridorFront.openings.push({
                    at: (room.x0 + room.x1) / 2 + width / 2,
                    width: room.openPlan ? Math.min(w - 0.6, 3.2) : 0.9,
                    kind: room.openPlan ? "opening" : "door",
                });
            }
            walls.push(corridorFront);
        } else {
            const divider = { a: [-width / 2, zFrontInner], b: [width / 2, zFrontInner], openings: [] };
            for (const room of backRooms) {
                divider.openings.push({ at: (room.x0 + room.x1) / 2 + width / 2, width: 0.9, kind: "door" });
            }
            walls.push(divider);
        }
        backRooms.slice(1).forEach((room) => walls.push({ a: [room.x0, zBack], b: [room.x0, zBackInner], openings: [] }));
    }
    frontRooms.slice(1).forEach((room) => {
        const prev = frontRooms[frontRooms.indexOf(room) - 1];
        const length = zFront - zFrontInner;
        walls.push({
            a: [room.x0, zFrontInner], b: [room.x0, zFront],
            openings: prev.openPlan && room.type === "kitchen" ? [{ at: length * 0.45, width: Math.min(1.8, length - 1), kind: "opening" }] : [],
        });
    });
    return { width, depth, rooms, walls };
}

function residentialRooms(bedrooms, bathrooms, { stairs = false, groundFloor = false } = {}) {
    const back = [];
    let baths = bathrooms;
    for (let i = 0; i < bedrooms; i++) {
        back.push({ type: i === 0 && !groundFloor ? "master" : "bedroom", weight: i === 0 ? 1.25 : 1 });
        if (baths > 0) {
            back.push({ type: "bathroom", weight: 0.55 });
            baths--;
        }
    }
    while (baths-- > 0) {
        back.push({ type: "bathroom", weight: 0.55 });
    }
    if (stairs) {
        back.splice(Math.min(1, back.length), 0, { type: "stairs", weight: 0.6 });
    }
    return back;
}

export function generatePlan(spec) {
    const kind = spec.kind || "apartment";
    const bedrooms = clamp(spec.bedrooms || 0, 0, 8);
    const bathrooms = clamp(spec.bathrooms || Math.max(1, Math.ceil(bedrooms / 1.5)), 1, 8);
    const floors = [];

    if (kind === "apartment" || kind === "house") {
        const storeys = kind === "house" ? clamp(spec.floors || 2, 1, 3) : 1;
        let area = spec.area || 40 + 28 * Math.max(bedrooms, 1) + 6 * bathrooms;
        area = clamp(area, 30, 900);
        const floorArea = area / storeys;
        if (storeys === 1) {
            const back = residentialRooms(bedrooms, bathrooms);
            if (!back.length) {
                back.push({ type: "bathroom", weight: 0.6 }, { type: "storage", weight: 0.5 });
            }
            let width = Math.sqrt(floorArea * 1.5);
            const minWidth = back.reduce((sum, room) => sum + (room.type === "bathroom" ? 1.8 : 3.0) * (room.weight || 1), 0);
            width = Math.max(width, minWidth, 7);
            const depth = Math.max(floorArea / width, 8);
            const front = [
                { type: "living", weight: 1.7, openPlan: true, balconyDoor: kind === "apartment" },
                { type: "kitchen", weight: 1 },
            ];
            floors.push({ name: "Floor plan", ...bandFloor(width, depth, front, back), balcony: kind === "apartment" });
        } else {
            // Ground floor: living spaces, a guest bathroom, the stairs; bedrooms upstairs.
            const upstairsBedrooms = Math.max(bedrooms - (bedrooms >= 4 ? 1 : 0), 1);
            const perFloor = Math.ceil(upstairsBedrooms / (storeys - 1));
            let width = Math.sqrt(floorArea * 1.4);
            width = Math.max(width, perFloor * 3.4 + 2.2, 9);
            const depth = Math.max(floorArea / width, 9);
            const groundBack = residentialRooms(bedrooms >= 4 ? 1 : 0, 1, { stairs: true, groundFloor: true });
            floors.push({
                name: "Ground floor",
                ...bandFloor(width, depth, [
                    { type: "living", weight: 1.7, openPlan: true },
                    { type: "kitchen", weight: 1 },
                ], groundBack),
            });
            let remaining = upstairsBedrooms;
            let remainingBaths = Math.max(bathrooms - 1, 1);
            for (let level = 1; level < storeys; level++) {
                const here = level === storeys - 1 ? remaining : Math.min(perFloor, remaining);
                const baths = level === storeys - 1 ? remainingBaths : Math.min(here, remainingBaths);
                remaining -= here;
                remainingBaths -= baths;
                const upper = residentialRooms(here, Math.max(baths, 1), { stairs: true });
                const frontCount = Math.max(1, Math.ceil(upper.length / 2));
                floors.push({
                    name: level === 1 ? "First floor" : "Second floor",
                    ...bandFloor(width, depth, upper.slice(0, frontCount), upper.slice(frontCount), { frontShare: 0.5 }),
                });
            }
        }
    } else if (kind === "office") {
        const area = clamp(spec.area || 450, 120, 1800);
        const width = Math.sqrt(area * 1.5);
        const depth = area / width;
        floors.push({
            name: "Office floor",
            ...bandFloor(width, depth, [{ type: "workspace", openPlan: true }],
                [{ type: "meeting", weight: 1.4 }, { type: "cabin", weight: 1 }, { type: "pantry", weight: 0.9 }, { type: "restroom", weight: 0.7 }],
                { frontShare: 0.6 }),
        });
    } else if (kind === "shop") {
        const area = clamp((spec.area || 120) / clamp(spec.floors || 1, 1, 4), 40, 900);
        const width = Math.max(Math.sqrt(area * 1.3), 7);
        const depth = area / width;
        floors.push({
            name: "Shop floor",
            ...bandFloor(width, depth, [{ type: "sales", shopFront: true, openPlan: true }],
                [{ type: "storage", weight: 1.6 }, { type: "restroom", weight: 0.6 }], { frontShare: 0.66, corridor: false }),
        });
    } else if (kind === "warehouse") {
        const area = clamp(spec.area || 1500, 300, 8000);
        const width = Math.sqrt(area * 1.6);
        const depth = area / width;
        floors.push({
            name: "Warehouse",
            ...bandFloor(width, depth, [{ type: "office", weight: 1 }, { type: "restroom", weight: 0.45 }],
                [{ type: "hallStore" }], { frontShare: 0.18, corridor: false }),
            wallHeight: 8,
        });
    }
    return { floors, furnishing: spec.furnishing || "unfurnished", kind };
}

// ---------------------------------------------------------------- building the interior

export function buildInterior(THREE, M, plan, { baseY = 0 } = {}) {
    const root = new THREE.Group();
    const levels = [];
    const storeyHeight = 3.0;
    plan.floors.forEach((floor, index) => {
        const level = buildFloor(THREE, M, floor, plan, floor.wallHeight || 2.9);
        level.group.position.y = baseY + index * storeyHeight;
        level.y = baseY + index * storeyHeight;
        level.name = floor.name;
        level.index = index;
        root.add(level.group);
        levels.push(level);
    });
    return { group: root, levels };
}

function buildFloor(THREE, M, floor, plan, wallHeight) {
    const group = new THREE.Group();
    const floorsMeshes = [];
    const collisions = [];
    const rooms = [];
    const lights = [];
    const furnished = plan.furnishing;

    function add(geometry, mat, x, y, z, parent = group) {
        const mesh = new THREE.Mesh(geometry, mat);
        mesh.position.set(x, y, z);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        parent.add(mesh);
        return mesh;
    }
    function box(w, h, d, mat, x, y, z, parent = group) {
        return add(new THREE.BoxGeometry(w, h, d), mat, x, y, z, parent);
    }
    function cylinder(rt, rb, h, mat, x, y, z, parent = group, segments = 16) {
        return add(new THREE.CylinderGeometry(rt, rb, h, segments), mat, x, y, z, parent);
    }

    // Floors and ceilings per room
    for (const room of floor.rooms) {
        const info = ROOM_INFO[room.type] || ROOM_INFO.hall;
        const w = room.x1 - room.x0;
        const d = room.z1 - room.z0;
        const cx = (room.x0 + room.x1) / 2;
        const cz = (room.z0 + room.z1) / 2;
        const floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(w, d), M.fit(M[info.floor], w, d));
        floorMesh.rotation.x = -Math.PI / 2;
        floorMesh.position.set(cx, 0.01, cz);
        floorMesh.receiveShadow = true;
        floorMesh.userData.walkable = true;
        group.add(floorMesh);
        floorsMeshes.push(floorMesh);
        const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(w, d), M.ceiling);
        ceiling.rotation.x = Math.PI / 2;
        ceiling.position.set(cx, wallHeight, cz);
        ceiling.userData.ceiling = true;
        group.add(ceiling);
        if (room.type !== "stairs") {
            // Ceiling light fitting and its warm light
            const lamp = cylinder(0.25, 0.25, 0.04, M.lamp, cx, wallHeight - 0.03, cz, group, 20);
            lamp.castShadow = false;
            lamp.userData.ceiling = true;
            const light = new THREE.PointLight(0xffe7c4, room.type === "hall" ? 0.25 : 0.55, Math.max(w, d) * 1.6 + 2, 2);
            light.position.set(cx, wallHeight - 0.35, cz);
            group.add(light);
            lights.push(light);
        }
        const label = info.label;
        const sameType = floor.rooms.filter((r) => r.type === room.type);
        const name = sameType.length > 1 && room.type !== "hall" ? `${label} ${sameType.indexOf(room) + 1}` : label;
        room.name = name;
        if (room.type !== "hall") {
            const sprite = makeLabel(THREE, [name, `${w.toFixed(1)} × ${d.toFixed(1)} m`], { scale: clamp(Math.min(w, d) / 3.5, 0.6, 1.2) });
            sprite.position.set(cx, Math.min(wallHeight + 0.6, 3.6), cz);
            sprite.userData.label = true;
            group.add(sprite);
        }
        rooms.push({ name, type: room.type, center: [cx, cz], bounds: [room.x0, room.z0, room.x1, room.z1], side: room.side });
        furnish(room, w, d, cx, cz);
    }

    // Walls with openings
    for (const wall of floor.walls) {
        buildWall(wall);
    }

    // Balcony with glass railing in front of the living room
    if (floor.balcony) {
        const living = floor.rooms.find((r) => r.type === "living");
        if (living) {
            const w = living.x1 - living.x0;
            const z = floor.depth / 2 + EXTERIOR_WALL / 2;
            const slab = box(w, 0.15, 1.6, M.fit(M.floorTiles, w, 1.6), (living.x0 + living.x1) / 2, -0.06, z + 0.8);
            slab.userData.walkable = true;
            floorsMeshes.push(slab);
            const glass = box(w, 1.05, 0.03, M.glass, (living.x0 + living.x1) / 2, 0.55, z + 1.58);
            glass.castShadow = false;
            box(w, 0.05, 0.06, M.railing, (living.x0 + living.x1) / 2, 1.1, z + 1.58);
            collisions.push({ a: [living.x0, z + 1.6], b: [living.x1, z + 1.6], half: 0.05 });
            collisions.push({ a: [living.x0, z], b: [living.x0, z + 1.6], half: 0.05 });
            collisions.push({ a: [living.x1, z], b: [living.x1, z + 1.6], half: 0.05 });
            rooms.push({ name: "Balcony", type: "balcony", center: [(living.x0 + living.x1) / 2, z + 0.8], bounds: [living.x0, z, living.x1, z + 1.6], side: "front" });
            for (let i = 0; i < 2; i++) {
                plant(living.x0 + 0.5 + i * (w - 1), z + 1.2, 0.8);
            }
        }
    }

    function buildWall(wall) {
        const thickness = wall.exterior ? EXTERIOR_WALL : INTERIOR_WALL;
        const [ax, az] = wall.a;
        const [bx, bz] = wall.b;
        const length = Math.hypot(bx - ax, bz - az);
        const angle = Math.atan2(bz - az, bx - ax);
        const dir = [(bx - ax) / length, (bz - az) / length];
        const at = (t) => [ax + dir[0] * t, az + dir[1] * t];
        const segment = new THREE.Group();
        segment.position.set(ax, 0, az);
        segment.rotation.y = -angle;
        group.add(segment);
        const outside = wall.exterior ? M.plaster : M.wallInside;
        const piece = (t0, t1, y0, y1) => {
            if (t1 - t0 < 0.01 || y1 - y0 < 0.01) {
                return;
            }
            const mesh = box(t1 - t0, y1 - y0, thickness, M.fit(outside, t1 - t0, y1 - y0), (t0 + t1) / 2, (y0 + y1) / 2, 0, segment);
            mesh.userData.wall = true;
        };
        const openings = [...wall.openings].sort((p, q) => p.at - q.at);
        let cursor = 0;
        for (const opening of openings) {
            const t0 = clamp(opening.at - opening.width / 2, 0, length);
            const t1 = clamp(opening.at + opening.width / 2, 0, length);
            piece(cursor, t0, 0, wallHeight);
            if (cursor < t0) {
                collisions.push({ a: at(cursor), b: at(t0), half: thickness / 2 });
            }
            if (opening.kind === "window") {
                const sill = opening.sill ?? 0.9;
                const height = opening.height ?? 1.4;
                piece(t0, t1, 0, sill);
                piece(t0, t1, Math.min(sill + height, wallHeight), wallHeight);
                const pane = box(t1 - t0, height, 0.02, M.glass, (t0 + t1) / 2, sill + height / 2, 0, segment);
                pane.castShadow = false;
                frame(segment, t0, t1, sill, sill + height, thickness);
                box(t1 - t0 + 0.1, 0.04, thickness + 0.08, M.frameWhite, (t0 + t1) / 2, sill, 0, segment);
                collisions.push({ a: at(t0), b: at(t1), half: thickness / 2 });
            } else {
                const top = opening.kind === "opening" ? Math.min(2.4, wallHeight) : opening.kind === "glassDoor" ? 2.3 : DOOR_HEIGHT;
                piece(t0, t1, top, wallHeight);
                if (opening.kind === "glassDoor") {
                    frame(segment, t0, t1, 0, top, thickness);
                    // Sliding glass door, half open
                    const leaf = box((t1 - t0) / 2, top - 0.05, 0.03, M.glass, t0 + (t1 - t0) * 0.25, top / 2, thickness / 4, segment);
                    leaf.castShadow = false;
                } else if (opening.kind === "door") {
                    // Door leaf opened at 80 degrees, frame around the opening
                    frame(segment, t0, t1, 0, top, thickness, M.frameWhite);
                    const hinge = new THREE.Group();
                    hinge.position.set(t0 + 0.03, 0, wall.exterior ? -thickness / 2 : thickness / 2);
                    hinge.rotation.y = wall.exterior ? 1.4 : -1.4;
                    segment.add(hinge);
                    box(t1 - t0 - 0.06, top - 0.02, 0.04, M.door, (t1 - t0 - 0.06) / 2, top / 2, 0, hinge);
                    cylinder(0.025, 0.025, 0.12, M.chrome, t1 - t0 - 0.16, 1.0, 0.05, hinge).rotation.x = Math.PI / 2;
                }
            }
            cursor = Math.max(cursor, t1);
        }
        piece(cursor, length, 0, wallHeight);
        if (cursor < length) {
            collisions.push({ a: at(cursor), b: at(length), half: thickness / 2 });
        }
    }

    function frame(parent, t0, t1, y0, y1, thickness, mat = M.frame) {
        const w = 0.06;
        box(t1 - t0, w, thickness + 0.02, mat, (t0 + t1) / 2, y1 - w / 2, 0, parent);
        box(w, y1 - y0, thickness + 0.02, mat, t0 + w / 2, (y0 + y1) / 2, 0, parent);
        box(w, y1 - y0, thickness + 0.02, mat, t1 - w / 2, (y0 + y1) / 2, 0, parent);
        if (y0 > 0) {
            box(t1 - t0, w, thickness + 0.02, mat, (t0 + t1) / 2, y0 + w / 2, 0, parent);
        }
    }

    // ------------------------------------------------------------ furniture
    function plant(x, z, scale = 1) {
        cylinder(0.18 * scale, 0.14 * scale, 0.35 * scale, M.pot, x, 0.175 * scale, z);
        add(new THREE.SphereGeometry(0.32 * scale, 12, 10), M.plant, x, 0.6 * scale, z);
        add(new THREE.SphereGeometry(0.22 * scale, 12, 10), M.plant, x + 0.12 * scale, 0.85 * scale, z - 0.05);
    }
    function chair(x, z, rotation, mat = M.woodDark, seat = M.fabricGrey) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(0.45, 0.06, 0.45, seat, 0, 0.46, 0, g);
        box(0.45, 0.5, 0.05, mat, 0, 0.74, -0.2, g);
        for (const [dx, dz] of [[-0.19, -0.19], [0.19, -0.19], [-0.19, 0.19], [0.19, 0.19]]) {
            box(0.04, 0.45, 0.04, mat, dx, 0.22, dz, g);
        }
    }
    function officeChair(x, z, rotation) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        cylinder(0.28, 0.28, 0.05, M.metalDark, 0, 0.05, 0, g);
        cylinder(0.03, 0.03, 0.4, M.chrome, 0, 0.28, 0, g);
        box(0.5, 0.08, 0.48, M.fabricBlue, 0, 0.5, 0, g);
        box(0.48, 0.55, 0.07, M.fabricBlue, 0, 0.82, -0.22, g);
    }
    function table(x, z, w, d, h = 0.75, top = M.woodLight, legs = M.metalDark) {
        box(w, 0.05, d, top, x, h, z);
        for (const [dx, dz] of [[-w / 2 + 0.06, -d / 2 + 0.06], [w / 2 - 0.06, -d / 2 + 0.06], [-w / 2 + 0.06, d / 2 - 0.06], [w / 2 - 0.06, d / 2 - 0.06]]) {
            box(0.05, h, 0.05, legs, x + dx, h / 2, z + dz);
        }
    }
    function bed(x, z, rotation, width) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(width + 0.1, 0.3, 2.1, M.woodDark, 0, 0.15, 0, g);
        box(width, 0.22, 2.0, M.linen, 0, 0.41, 0.02, g);
        box(width + 0.02, 0.05, 1.2, M.fabricBlue, 0, 0.54, 0.38, g);
        box(width + 0.1, 0.9, 0.08, M.fabricBeige, 0, 0.75, -1.04, g);
        const pillows = width > 1.2 ? [-width / 4, width / 4] : [0];
        for (const px of pillows) {
            box(Math.min(0.6, width / 2 - 0.05), 0.12, 0.38, M.linen, px, 0.58, -0.75, g);
        }
        for (const side of width > 1.2 ? [-1, 1] : [1]) {
            box(0.45, 0.5, 0.4, M.woodLight, side * (width / 2 + 0.35), 0.25, -0.8, g);
            cylinder(0.08, 0.12, 0.3, M.lamp, side * (width / 2 + 0.35), 0.68, -0.8, g, 12);
        }
    }
    function wardrobe(x, z, rotation, width) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(width, 2.2, 0.6, M.cabinet, 0, 1.1, 0, g);
        const doors = Math.max(2, Math.round(width / 0.55));
        for (let i = 1; i < doors; i++) {
            box(0.01, 2.1, 0.02, M.trim, -width / 2 + (width / doors) * i, 1.1, 0.31, g);
        }
    }
    function sofa(x, z, rotation, width) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(width, 0.42, 0.9, M.fabricGrey, 0, 0.21, 0, g);
        box(width, 0.45, 0.2, M.fabricGrey, 0, 0.62, -0.35, g);
        box(0.2, 0.25, 0.9, M.fabricGrey, -width / 2 + 0.1, 0.55, 0, g);
        box(0.2, 0.25, 0.9, M.fabricGrey, width / 2 - 0.1, 0.55, 0, g);
        const cushions = Math.max(2, Math.round(width / 0.8));
        for (let i = 0; i < cushions; i++) {
            box((width - 0.45) / cushions - 0.04, 0.1, 0.65, M.fabricBeige, -width / 2 + 0.22 + ((width - 0.45) / cushions) * (i + 0.5), 0.47, 0.05, g);
        }
    }
    function counterRun(x0, x1, zWall, facing, withUpper = true) {
        // Kitchen counter along a wall; facing = +1 when the wall is at the back (z smaller).
        const length = x1 - x0;
        const z = zWall + facing * 0.33;
        box(length, 0.86, 0.6, M.cabinet, (x0 + x1) / 2, 0.43, z);
        box(length + 0.02, 0.04, 0.64, M.counter, (x0 + x1) / 2, 0.88, z);
        const doors = Math.max(2, Math.round(length / 0.6));
        for (let i = 1; i < doors; i++) {
            box(0.01, 0.75, 0.01, M.trim, x0 + (length / doors) * i, 0.43, z + facing * 0.305);
        }
        if (withUpper) {
            box(length, 0.7, 0.35, M.cabinet, (x0 + x1) / 2, 1.85, zWall + facing * 0.2);
        }
        // Sink and hob
        box(0.5, 0.02, 0.4, M.chrome, x0 + length * 0.3, 0.905, z);
        box(0.6, 0.02, 0.5, M.screen, x0 + length * 0.7, 0.905, z);
    }
    function wc(x, z, rotation) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        cylinder(0.18, 0.15, 0.4, M.ceramic, 0, 0.2, 0.1, g);
        box(0.38, 0.4, 0.18, M.ceramic, 0, 0.6, -0.14, g);
    }
    function basin(x, z, rotation) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(0.6, 0.6, 0.45, M.cabinet, 0, 0.5, 0, g);
        box(0.62, 0.06, 0.47, M.ceramic, 0, 0.83, 0, g);
        box(0.55, 0.7, 0.02, M.chrome, 0, 1.45, -0.22, g);
    }
    function shower(x0, z0) {
        box(0.9, 0.06, 0.9, M.ceramic, x0 + 0.45, 0.03, z0 + 0.45);
        const glassPanel = box(0.9, 1.9, 0.02, M.glass, x0 + 0.45, 1.0, z0 + 0.9);
        glassPanel.castShadow = false;
        cylinder(0.08, 0.08, 0.02, M.chrome, x0 + 0.45, 2.05, z0 + 0.2);
    }
    function shelfUnit(x, z, rotation, length, height = 1.8, products = true) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(length, height, 0.04, M.shelf, 0, height / 2, -0.2, g);
        const levels = Math.round(height / 0.45);
        const productMats = [M.productA, M.productB, M.productC];
        for (let i = 0; i < levels; i++) {
            const y = 0.1 + i * 0.45;
            box(length, 0.03, 0.42, M.shelf, 0, y, 0, g);
            if (products) {
                const count = Math.floor(length / 0.18);
                for (let p = 0; p < count; p++) {
                    if ((p * 7 + i * 3) % 5 === 0) {
                        continue;
                    }
                    box(0.13, 0.18 + ((p + i) % 3) * 0.05, 0.25, productMats[(p + i) % 3], -length / 2 + 0.1 + p * 0.18, y + 0.12, 0.02, g);
                }
            }
        }
    }
    function rack(x, z, length) {
        const height = 6;
        for (const dx of [-length / 2, length / 2]) {
            box(0.1, height, 1.1, M.rack, x + dx, height / 2, z);
        }
        for (let level = 0; level < 4; level++) {
            const y = 0.2 + level * 1.5;
            box(length, 0.08, 1.1, M.metal, x, y, z);
            const pallets = Math.floor(length / 1.3);
            for (let p = 0; p < pallets; p++) {
                if ((p + level) % 4 === 3) {
                    continue;
                }
                const px = x - length / 2 + 0.7 + p * 1.3;
                box(1.1, 0.14, 1.0, M.pallet, px, y + 0.11, z);
                box(1.0, 0.9, 0.9, M.box, px, y + 0.63, z);
            }
        }
    }
    function rug(x, z, w, d) {
        const r = box(w, 0.01, d, M.rug, x, 0.02, z);
        r.castShadow = false;
    }
    function tv(x, z, rotation) {
        const g = new THREE.Group();
        g.position.set(x, 0, z);
        g.rotation.y = rotation;
        group.add(g);
        box(1.8, 0.45, 0.42, M.woodDark, 0, 0.22, 0, g);
        box(1.3, 0.75, 0.05, M.screen, 0, 1.25, -0.1, g);
    }
    function stairs(room, w, d) {
        // A straight flight rising towards the back wall, with a railing.
        const steps = 16;
        const run = Math.min(d - 0.4, 4.2);
        const stepDepth = run / steps;
        const flightWidth = Math.min(w - 0.3, 1.1);
        const x = (room.x0 + room.x1) / 2;
        for (let i = 0; i < steps; i++) {
            const z = room.z1 - 0.3 - stepDepth * (i + 0.5);
            box(flightWidth, 0.04, stepDepth + 0.02, M.stairs, x, (i + 1) * (3.0 / steps), z);
            box(flightWidth, (i + 1) * (3.0 / steps), 0.02, M.cabinet, x, ((i + 1) * (3.0 / steps)) / 2, z + stepDepth / 2);
        }
        const rail = box(0.04, 0.04, Math.hypot(run, 3.0), M.railing, x + flightWidth / 2, 1.9, room.z1 - 0.3 - run / 2);
        rail.rotation.x = Math.atan2(3.0, run);
        // The staircase is not walkable in walk-through mode: floors are reached with the floor buttons.
        collisions.push({ box: [room.x0, room.z0, room.x1, room.z1] });
    }

    function furnish(room, w, d, cx, cz) {
        const full = furnished === "furnished";
        const some = furnished !== "unfurnished";
        const back = room.side === "back";
        // Far wall from the door: z0 for back rooms, z1 for front rooms.
        const farZ = back ? room.z0 : room.z1;
        const inward = back ? 1 : -1;
        switch (room.type) {
            case "living": {
                if (full) {
                    const sofaWidth = clamp(w * 0.38, 1.8, 3);
                    sofa(room.x0 + 0.55, cz + d * 0.1, Math.PI / 2, sofaWidth);
                    table(room.x0 + 1.75, cz + d * 0.1, 0.6, 1.1, 0.4, M.woodLight, M.woodLight);
                    rug(room.x0 + 1.7, cz + d * 0.1, 2.2, 2.6);
                    tv(room.x0 + 3.4, cz + d * 0.1, -Math.PI / 2);
                    const diningX = room.x1 - Math.min(2.2, w * 0.3);
                    table(diningX, cz - d * 0.15, 1.6, 0.9);
                    for (const [dx, dz, rot] of [[-0.45, -0.65, 0], [0.45, -0.65, 0], [-0.45, 0.65, Math.PI], [0.45, 0.65, Math.PI]]) {
                        chair(diningX + dx, cz - d * 0.15 + dz, rot);
                    }
                    plant(room.x0 + 0.4, farZ + inward * 0.4);
                }
                break;
            }
            case "kitchen": {
                // No wall cabinets over the windows of a street-side kitchen.
                counterRun(room.x0 + 0.1, room.x1 - 0.7, farZ, inward, back);
                if (some) {
                    box(0.7, 1.9, 0.65, M.appliance, room.x1 - 0.45, 0.95, farZ + inward * 0.4);
                    box(0.02, 0.5, 0.02, M.chrome, room.x1 - 0.75, 1.35, farZ + inward * 0.74);
                }
                if (full && d > 3) {
                    table(cx, cz - inward * 0.3, 1.0, 0.7);
                    chair(cx - 0.3, cz - inward * 0.85, back ? Math.PI : 0);
                    chair(cx + 0.3, cz - inward * 0.85, back ? Math.PI : 0);
                }
                break;
            }
            case "master":
            case "bedroom": {
                const bedWidth = room.type === "master" ? 1.8 : w > 3 ? 1.5 : 1.0;
                if (full) {
                    bed(cx, farZ + inward * 1.12, back ? 0 : Math.PI, bedWidth);
                    rug(cx, farZ + inward * 2.2, Math.min(w - 0.6, 2.4), 1.4);
                }
                if (some && w > 2.6) {
                    wardrobe(room.x0 + 0.33, cz + inward * 0.2, Math.PI / 2, Math.min(d - 1.6, 2.2));
                }
                if (full && w > 3.2) {
                    table(room.x1 - 0.5, cz + inward * 0.4, 0.6, 1.1);
                    officeChair(room.x1 - 0.95, cz + inward * 0.4, -Math.PI / 2);
                }
                break;
            }
            case "bathroom":
            case "restroom": {
                wc(room.x0 + 0.35, farZ + inward * 0.35, back ? 0 : Math.PI);
                basin(cx + 0.2, farZ + inward * 0.25, back ? 0 : Math.PI);
                if (room.type === "bathroom" && w > 1.8) {
                    shower(room.x1 - 0.95, back ? room.z0 + 0.05 : room.z1 - 0.95);
                }
                break;
            }
            case "stairs":
                stairs(room, w, d);
                break;
            case "storage":
                if (plan.kind === "shop") {
                    for (let x = room.x0 + 0.4; x < room.x1 - 1; x += 1.6) {
                        shelfUnit(x + 0.6, room.z0 + 0.3, 0, 1.2, 2.2, true);
                    }
                    box(0.6, 0.6, 0.6, M.box, cx, 0.3, cz);
                    box(0.5, 0.5, 0.5, M.box, cx + 0.5, 0.25, cz + 0.4);
                } else {
                    shelfUnit(cx, room.z0 + 0.3, 0, Math.min(w - 0.4, 1.6), 2.0, false);
                }
                break;
            case "workspace": {
                if (!some) {
                    break;
                }
                const rows = Math.max(1, Math.floor((d - 2) / 3));
                const cols = Math.max(1, Math.floor((w - 2) / 3.2));
                for (let r = 0; r < rows; r++) {
                    for (let c = 0; c < cols; c++) {
                        const x = room.x0 + 1.6 + c * ((w - 3.2) / Math.max(cols - 1, 1));
                        const z = room.z0 + 1.8 + r * 3;
                        for (const side of [-1, 1]) {
                            table(x, z + side * 0.42, 1.4, 0.75, 0.74, M.cabinet);
                            box(0.6, 0.38, 0.04, M.screen, x, 1.0, z + side * 0.2);
                            officeChair(x, z + side * 1.15, side > 0 ? Math.PI : 0);
                        }
                    }
                }
                plant(room.x0 + 0.5, room.z1 - 0.6);
                plant(room.x1 - 0.5, room.z1 - 0.6);
                break;
            }
            case "meeting": {
                if (!some) {
                    break;
                }
                const length = Math.min(w - 1.6, 4);
                table(cx, cz, length, 1.2);
                const seats = Math.max(2, Math.floor(length / 0.8));
                for (let i = 0; i < seats; i++) {
                    const x = cx - length / 2 + 0.4 + (length - 0.8) * (i / Math.max(seats - 1, 1));
                    officeChair(x, cz - 0.95, 0);
                    officeChair(x, cz + 0.95, Math.PI);
                }
                box(1.6, 0.9, 0.05, M.screen, cx, 1.5, room.z0 + 0.15);
                break;
            }
            case "cabin": {
                if (!some) {
                    break;
                }
                table(cx, farZ + inward * 1.2, 1.6, 0.8, 0.75, M.woodDark);
                officeChair(cx, farZ + inward * 0.55, back ? Math.PI : 0);
                chair(cx - 0.4, farZ + inward * 2, back ? 0 : Math.PI, M.woodDark, M.fabricBlue);
                chair(cx + 0.4, farZ + inward * 2, back ? 0 : Math.PI, M.woodDark, M.fabricBlue);
                shelfUnit(room.x1 - 0.35, cz, -Math.PI / 2, Math.min(d - 1, 1.6), 2.0, false);
                break;
            }
            case "pantry":
                counterRun(room.x0 + 0.1, room.x1 - 0.1, farZ, inward, true);
                if (some) {
                    table(cx, cz + inward * 0.4, 0.9, 0.9);
                }
                break;
            case "sales": {
                // Checkout counter by the entrance, shelf rows behind.
                box(1.8, 1.0, 0.6, M.woodDark, room.x1 - 1.4, 0.5, room.z1 - 1.6);
                box(1.85, 0.04, 0.65, M.counter, room.x1 - 1.4, 1.02, room.z1 - 1.6);
                box(0.35, 0.25, 0.05, M.screen, room.x1 - 1.4, 1.2, room.z1 - 1.75);
                if (some) {
                    // Back-to-back shelf pairs; the side nearest the entrance faces the customers,
                    // and the first 3 m inside the door stay clear for the checkout.
                    const rows = Math.max(1, Math.floor((d - 4.5) / 1.9));
                    for (let r = 0; r < rows; r++) {
                        shelfUnit(cx - 0.8, room.z0 + 1.2 + r * 1.9, Math.PI, Math.min(w - 4, 6), 1.6);
                        shelfUnit(cx - 0.8, room.z0 + 1.6 + r * 1.9, 0, Math.min(w - 4, 6), 1.6);
                    }
                }
                break;
            }
            case "hallStore": {
                const rows = Math.max(1, Math.floor((d - 4) / 4));
                const length = Math.max(4, w - 8);
                for (let r = 0; r < rows; r++) {
                    rack(cx, room.z0 + 2 + r * 4, length);
                }
                break;
            }
            case "office":
                table(cx, cz, 1.4, 0.7, 0.75, M.woodDark);
                officeChair(cx, cz - 0.6, 0);
                shelfUnit(room.x0 + 0.35, cz, Math.PI / 2, Math.min(d - 1, 1.4), 2.0, false);
                break;
            default:
                break;
        }
    }

    return { group, floors: floorsMeshes, collisions, rooms, lights, width: floor.width, depth: floor.depth, wallHeight };
}
