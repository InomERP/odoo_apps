/**
 * Materials with procedural textures (drawn on canvases, no image files), shared by the
 * exterior and interior builders. THREE is passed in because three.js is loaded on demand.
 */

function canvas(size, draw) {
    const el = document.createElement("canvas");
    el.width = el.height = size;
    const ctx = el.getContext("2d");
    draw(ctx, size);
    return el;
}

// Deterministic noise so textures look the same on every load.
function noise(seed) {
    let state = seed;
    return () => {
        state = (state * 16807) % 2147483647;
        return (state - 1) / 2147483646;
    };
}

function speckle(ctx, size, base, variation, count, seed, maxDot = 2) {
    const random = noise(seed);
    ctx.fillStyle = base;
    ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < count; i++) {
        const shade = Math.round((random() - 0.5) * variation);
        ctx.fillStyle = `rgba(${shade > 0 ? "255,255,255" : "0,0,0"},${Math.abs(shade) / 255})`;
        ctx.fillRect(random() * size, random() * size, 1 + random() * maxDot, 1 + random() * maxDot);
    }
}

const DRAWINGS = {
    plaster: (ctx, s) => speckle(ctx, s, "#ffffff", 40, 9000, 11),
    concrete: (ctx, s) => speckle(ctx, s, "#ffffff", 60, 12000, 23, 3),
    brick(ctx, s) {
        const random = noise(37);
        ctx.fillStyle = "#d9d2c5";
        ctx.fillRect(0, 0, s, s);
        const rows = 16;
        const h = s / rows;
        const w = s / 4;
        for (let r = 0; r < rows; r++) {
            const offset = r % 2 ? w / 2 : 0;
            for (let c = -1; c < 5; c++) {
                const tone = 150 + Math.round(random() * 40);
                ctx.fillStyle = `rgb(${tone + 40},${tone - 30},${tone - 60})`;
                ctx.fillRect(c * w + offset + 2, r * h + 2, w - 4, h - 4);
            }
        }
    },
    roofTiles(ctx, s) {
        const random = noise(41);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, s, s);
        const rows = 12;
        const h = s / rows;
        for (let r = 0; r < rows; r++) {
            const g = ctx.createLinearGradient(0, r * h, 0, (r + 1) * h);
            g.addColorStop(0, "rgba(0,0,0,0)");
            g.addColorStop(1, "rgba(0,0,0,0.35)");
            ctx.fillStyle = g;
            ctx.fillRect(0, r * h, s, h);
            for (let c = 0; c < 8; c++) {
                ctx.fillStyle = `rgba(0,0,0,${0.05 + random() * 0.1})`;
                ctx.fillRect(c * (s / 8) + (r % 2 ? s / 16 : 0), r * h, 2, h);
            }
        }
    },
    wood(ctx, s) {
        const random = noise(53);
        const planks = 6;
        const pw = s / planks;
        for (let p = 0; p < planks; p++) {
            const tone = 0.85 + random() * 0.3;
            ctx.fillStyle = `rgb(${Math.round(200 * tone)},${Math.round(160 * tone)},${Math.round(115 * tone)})`;
            ctx.fillRect(p * pw, 0, pw, s);
            for (let g = 0; g < 18; g++) {
                ctx.strokeStyle = `rgba(90,60,30,${0.05 + random() * 0.1})`;
                ctx.beginPath();
                const x = p * pw + random() * pw;
                ctx.moveTo(x, 0);
                ctx.bezierCurveTo(x + 6, s / 3, x - 6, (2 * s) / 3, x + 3, s);
                ctx.stroke();
            }
            ctx.fillStyle = "rgba(60,40,20,0.5)";
            ctx.fillRect(p * pw, 0, 1.5, s);
            ctx.fillRect(p * pw, ((p * 37) % 7) * (s / 7), pw, 1.5);
        }
    },
    tiles(ctx, s) {
        speckle(ctx, s, "#f2efe9", 25, 4000, 61);
        ctx.strokeStyle = "rgba(120,110,100,0.45)";
        ctx.lineWidth = 2;
        for (let i = 0; i <= 4; i++) {
            ctx.beginPath();
            ctx.moveTo((i * s) / 4, 0);
            ctx.lineTo((i * s) / 4, s);
            ctx.moveTo(0, (i * s) / 4);
            ctx.lineTo(s, (i * s) / 4);
            ctx.stroke();
        }
    },
    smallTiles(ctx, s) {
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, s, s);
        ctx.strokeStyle = "rgba(90,110,120,0.35)";
        ctx.lineWidth = 1.5;
        for (let i = 0; i <= 8; i++) {
            ctx.beginPath();
            ctx.moveTo((i * s) / 8, 0);
            ctx.lineTo((i * s) / 8, s);
            ctx.moveTo(0, (i * s) / 8);
            ctx.lineTo(s, (i * s) / 8);
            ctx.stroke();
        }
    },
    carpet: (ctx, s) => speckle(ctx, s, "#ffffff", 70, 20000, 71, 1.5),
    grass(ctx, s) {
        const random = noise(83);
        ctx.fillStyle = "#7fae62";
        ctx.fillRect(0, 0, s, s);
        for (let i = 0; i < 14000; i++) {
            const g = 120 + Math.round(random() * 70);
            ctx.fillStyle = `rgba(${g - 70},${g},${g - 90},0.55)`;
            ctx.fillRect(random() * s, random() * s, 1, 2 + random() * 3);
        }
    },
    asphalt(ctx, s) {
        speckle(ctx, s, "#5f646b", 70, 16000, 97, 1.5);
        ctx.fillStyle = "rgba(245,245,235,0.9)";
        for (let x = 0; x < s; x += s / 4) {
            ctx.fillRect(x + s / 16, s / 2 - 3, s / 8, 6);
        }
    },
    paving(ctx, s) {
        speckle(ctx, s, "#d8d2c6", 35, 5000, 101);
        ctx.strokeStyle = "rgba(110,100,90,0.45)";
        ctx.lineWidth = 2;
        for (let r = 0; r < 8; r++) {
            ctx.beginPath();
            ctx.moveTo(0, (r * s) / 8);
            ctx.lineTo(s, (r * s) / 8);
            ctx.stroke();
            for (let c = 0; c < 4; c++) {
                const x = c * (s / 4) + (r % 2 ? s / 8 : 0);
                ctx.beginPath();
                ctx.moveTo(x, (r * s) / 8);
                ctx.lineTo(x, ((r + 1) * s) / 8);
                ctx.stroke();
            }
        }
    },
    fabric: (ctx, s) => speckle(ctx, s, "#ffffff", 45, 15000, 113, 1),
};

export function createMaterials(THREE, renderer) {
    const textures = {};
    const anisotropy = renderer ? renderer.capabilities.getMaxAnisotropy() : 1;

    function texture(name) {
        if (!textures[name]) {
            const t = new THREE.CanvasTexture(canvas(256, DRAWINGS[name]));
            t.wrapS = t.wrapT = THREE.RepeatWrapping;
            t.anisotropy = Math.min(8, anisotropy);
            t.encoding = THREE.sRGBEncoding;
            textures[name] = t;
        }
        return textures[name];
    }

    const cache = {};
    // A material with a tiled texture; `repeat` is the size in metres of one texture tile.
    function make(key, color, { map, repeat = 2, roughness = 0.85, metalness = 0, ...rest } = {}) {
        if (!cache[key]) {
            const options = { color, roughness, metalness, ...rest };
            if (map) {
                options.map = texture(map);
            }
            const mat = new THREE.MeshStandardMaterial(options);
            mat.userData.tileSize = repeat;
            cache[key] = mat;
        }
        return cache[key];
    }

    const M = {
        plaster: make("plaster", 0xf1ebe0, { map: "plaster", repeat: 3 }),
        plasterWarm: make("plasterWarm", 0xe7d6bc, { map: "plaster", repeat: 3 }),
        plasterGrey: make("plasterGrey", 0xd5d8dc, { map: "plaster", repeat: 3 }),
        brick: make("brick", 0xffffff, { map: "brick", repeat: 2.4 }),
        concrete: make("concrete", 0xc9ccd0, { map: "concrete", repeat: 3 }),
        trim: make("trim", 0xb7ab98, { roughness: 0.7 }),
        frame: make("frame", 0x3e4652, { roughness: 0.45, metalness: 0.4 }),
        frameWhite: make("frameWhite", 0xf4f4f2, { roughness: 0.5 }),
        glass: new THREE.MeshPhysicalMaterial({
            color: 0x9fb8cf, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.35,
            envMapIntensity: 1.4, clearcoat: 1, depthWrite: false,
        }),
        glassFacade: make("glassFacade", 0x8fb0d6, { roughness: 0.06, metalness: 0.75, envMapIntensity: 1.6 }),
        glassLit: make("glassLit", 0xf3d49a, { roughness: 0.3, emissive: 0x7a5a25, emissiveIntensity: 0.45 }),
        roofTiles: make("roofTiles", 0x7b3b2c, { map: "roofTiles", repeat: 3 }),
        roofSlate: make("roofSlate", 0x4a5568, { map: "roofTiles", repeat: 3 }),
        metal: make("metal", 0xa7afb8, { roughness: 0.35, metalness: 0.7 }),
        metalDark: make("metalDark", 0x4b5563, { roughness: 0.4, metalness: 0.6 }),
        door: make("door", 0x7a5235, { map: "wood", repeat: 1.2, roughness: 0.6 }),
        grass: make("grass", 0xc9d6b8, { map: "grass", repeat: 4, roughness: 1 }),
        soil: make("soil", 0xb39567, { map: "concrete", repeat: 3, roughness: 1 }),
        asphalt: make("asphalt", 0xffffff, { map: "asphalt", repeat: 7, roughness: 0.95 }),
        paving: make("paving", 0xffffff, { map: "paving", repeat: 2.5 }),
        trunk: make("trunk", 0x6b4a33),
        leaf: make("leaf", 0x3f8f4a, { roughness: 0.9 }),
        leafLight: make("leafLight", 0x5aa857, { roughness: 0.9 }),
        hedge: make("hedge", 0x4e9a4a, { map: "grass", repeat: 1, roughness: 1 }),
        fence: make("fence", 0x8a6a4a, { map: "wood", repeat: 1 }),
        awningA: make("awningA", 0xd9534f, { map: "fabric", repeat: 1 }),
        awningB: make("awningB", 0xf7f4ee, { map: "fabric", repeat: 1 }),
        sign: make("sign", 0x24324a, { roughness: 0.4 }),
        // Interior
        wallInside: make("wallInside", 0xe9e1d4, { map: "plaster", repeat: 3, roughness: 0.95 }),
        wallBath: make("wallBath", 0xe9f1f3, { map: "smallTiles", repeat: 1.2, roughness: 0.4 }),
        floorWood: make("floorWood", 0xffffff, { map: "wood", repeat: 2, roughness: 0.55 }),
        floorTiles: make("floorTiles", 0xffffff, { map: "tiles", repeat: 2.4, roughness: 0.45 }),
        floorBath: make("floorBath", 0xd7e3e8, { map: "smallTiles", repeat: 1.2, roughness: 0.5 }),
        floorCarpet: make("floorCarpet", 0x8d96a3, { map: "carpet", repeat: 1.5, roughness: 1 }),
        floorConcrete: make("floorConcrete", 0xb9bcc0, { map: "concrete", repeat: 4, roughness: 0.8 }),
        ceiling: make("ceiling", 0xf1eee8, { roughness: 1 }),
        fabricGrey: make("fabricGrey", 0x8a929c, { map: "fabric", repeat: 0.8, roughness: 1 }),
        fabricBlue: make("fabricBlue", 0x4d6a8f, { map: "fabric", repeat: 0.8, roughness: 1 }),
        fabricBeige: make("fabricBeige", 0xd9c9ad, { map: "fabric", repeat: 0.8, roughness: 1 }),
        linen: make("linen", 0xf7f5f0, { map: "fabric", repeat: 0.8, roughness: 1 }),
        woodLight: make("woodLight", 0xffffff, { map: "wood", repeat: 1.2, roughness: 0.6 }),
        woodDark: make("woodDark", 0x8a6040, { map: "wood", repeat: 1.2, roughness: 0.6 }),
        counter: make("counter", 0x3c3f44, { roughness: 0.25, metalness: 0.1 }),
        cabinet: make("cabinet", 0xf1efea, { roughness: 0.5 }),
        ceramic: make("ceramic", 0xffffff, { roughness: 0.15 }),
        chrome: make("chrome", 0xdfe3e8, { roughness: 0.1, metalness: 1 }),
        appliance: make("appliance", 0xd9dde1, { roughness: 0.35, metalness: 0.25 }),
        screen: make("screen", 0x12161c, { roughness: 0.2, metalness: 0.3 }),
        plant: make("plant", 0x3f8f4a, { roughness: 0.9 }),
        pot: make("pot", 0xc06a4a, { roughness: 0.8 }),
        rug: make("rug", 0xb7a58c, { map: "carpet", repeat: 1, roughness: 1 }),
        lamp: make("lamp", 0xfff4d6, { emissive: 0xffe2a8, emissiveIntensity: 0.9 }),
        shelf: make("shelf", 0xd0d4d9, { roughness: 0.5, metalness: 0.3 }),
        rack: make("rack", 0x2f5aa8, { roughness: 0.5, metalness: 0.4 }),
        pallet: make("pallet", 0xc8a46e, { map: "wood", repeat: 1 }),
        box: make("box", 0xb48a5a, { roughness: 0.9 }),
        productA: make("productA", 0xe06666, { roughness: 0.6 }),
        productB: make("productB", 0x6fa8dc, { roughness: 0.6 }),
        productC: make("productC", 0xf6b26b, { roughness: 0.6 }),
        stairs: make("stairs", 0xffffff, { map: "wood", repeat: 1.2, roughness: 0.6 }),
        railing: make("railing", 0x5b6470, { roughness: 0.4, metalness: 0.6 }),
    };

    /**
     * Repeat a material's texture to fit a surface of w x h metres. Returns a clone so each
     * surface keeps its own scale (clones share the texture image).
     */
    M.fit = (mat, w, h) => {
        if (!mat.map) {
            return mat;
        }
        const key = `${mat.uuid}:${w.toFixed(1)}x${h.toFixed(1)}`;
        if (!cache[key]) {
            const clone = mat.clone();
            clone.map = mat.map.clone();
            clone.map.needsUpdate = true;
            const tile = mat.userData.tileSize || 2;
            clone.map.repeat.set(Math.max(w / tile, 0.2), Math.max(h / tile, 0.2));
            cache[key] = clone;
        }
        return cache[key];
    };
    return M;
}

/** A text label as a sprite (room names and sizes). */
export function makeLabel(THREE, lines, { scale = 1 } = {}) {
    const el = document.createElement("canvas");
    const ctx = el.getContext("2d");
    const font = 'bold 44px system-ui, -apple-system, "Segoe UI", sans-serif';
    const small = '34px system-ui, -apple-system, "Segoe UI", sans-serif';
    ctx.font = font;
    const width = Math.max(...lines.map((line, i) => {
        ctx.font = i ? small : font;
        return ctx.measureText(line).width;
    })) + 48;
    el.width = Math.ceil(width);
    el.height = 64 + (lines.length - 1) * 46;
    ctx.fillStyle = "rgba(255,255,255,0.88)";
    const r = 18;
    ctx.beginPath();
    ctx.moveTo(r, 0);
    ctx.arcTo(el.width, 0, el.width, el.height, r);
    ctx.arcTo(el.width, el.height, 0, el.height, r);
    ctx.arcTo(0, el.height, 0, 0, r);
    ctx.arcTo(0, 0, el.width, 0, r);
    ctx.fill();
    ctx.textAlign = "center";
    lines.forEach((line, i) => {
        ctx.font = i ? small : font;
        ctx.fillStyle = i ? "#4b5563" : "#13294b";
        ctx.fillText(line, el.width / 2, 46 + i * 46);
    });
    const tex = new THREE.CanvasTexture(el);
    tex.encoding = THREE.sRGBEncoding;
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sprite.scale.set((el.width / 100) * 0.42 * scale, (el.height / 100) * 0.42 * scale, 1);
    sprite.renderOrder = 10;
    return sprite;
}
