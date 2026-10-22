import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

import { buildPropertyModel } from "./property_3d_builder";
import { buildInterior, generatePlan } from "./property_3d_interior";
import { createMaterials } from "./property_3d_materials";
import { WalkControls } from "./property_3d_walk";

const LIB = "/inom_rental_management_website/static/lib/three/";
let threeLoaded = null;

// three.js is loaded only when a 3D view comes into sight.
function loadThree() {
    if (!threeLoaded) {
        threeLoaded = loadJS(`${LIB}three.min.js`).then(() =>
            Promise.all([
                loadJS(`${LIB}OrbitControls.js`),
                loadJS(`${LIB}GLTFLoader.js`),
                loadJS(`${LIB}RoomEnvironment.js`),
            ])
        );
    }
    return threeLoaded;
}

function hasWebGL() {
    try {
        const canvas = document.createElement("canvas");
        return !!(window.WebGLRenderingContext && (canvas.getContext("webgl2") || canvas.getContext("webgl")));
    } catch {
        return false;
    }
}

const HINTS = {
    exterior: () => _t("Drag to rotate, scroll or pinch to zoom, right-drag to move."),
    interior: () => _t("Drag to rotate the cut-away floor plan, scroll or pinch to zoom. Pick a room to walk into it."),
    walk: () => _t("Drag to look around. Walk with W A S D or the arrow keys, or tap the floor to go there."),
};

export class Property3DView extends Interaction {
    static selector = ".o_property_3d";
    dynamicContent = {
        ".o_property_3d_rotate": {
            "t-on-click": this.toggleRotate,
            "t-att-aria-pressed": () => String(this.autoRotate),
            "t-att-class": () => ({ active: this.autoRotate, "d-none": this.mode === "walk" }),
        },
        ".o_property_3d_reset": { "t-on-click": this.resetView },
        ".o_property_3d_fullscreen": { "t-on-click": this.toggleFullscreen },
        ".o_property_3d_mode": {
            "t-on-click": this.onModeClick,
            "t-att-class": (el) => ({ active: el.dataset.mode === this.mode, "d-none": !this.modes.includes(el.dataset.mode) }),
            "t-att-aria-pressed": (el) => String(el.dataset.mode === this.mode),
        },
        ".o_property_3d_rooms": { "t-on-click": this.onRoomClick },
        ".o_property_3d_hint": { "t-out": () => (this.mode ? HINTS[this.mode]() : "") },
    };

    setup() {
        this.viewport = this.el.querySelector(".o_property_3d_viewport");
        this.statusEl = this.el.querySelector(".o_property_3d_status");
        this.roomsEl = this.el.querySelector(".o_property_3d_rooms");
        this.autoRotate = true;
        this.started = false;
        this.visible = false;
        this.frame = null;
        this.mode = "exterior";
        this.modes = ["exterior"];
        this.levelIndex = 0;
        try {
            this.spec = JSON.parse(this.el.dataset.spec || "{}");
        } catch {
            this.spec = {};
        }
    }

    start() {
        if (!hasWebGL()) {
            this.setStatus("unsupported", _t("Your browser cannot show 3D views."));
            return;
        }
        if (!("IntersectionObserver" in window)) {
            this.visible = true;
            this.init();
            return;
        }
        const observer = new IntersectionObserver(
            (entries) => {
                this.visible = entries.some((entry) => entry.isIntersecting);
                if (this.visible && !this.started) {
                    this.init();
                }
            },
            { rootMargin: "200px" }
        );
        observer.observe(this.viewport);
        this.registerCleanup(() => observer.disconnect());
        this.addListener(document, "fullscreenchange", this.onFullscreenChange);
    }

    setStatus(state, message = "") {
        this.el.dataset.state = state;
        if (this.statusEl) {
            this.statusEl.classList.toggle("d-none", state === "ready");
            this.statusEl.querySelector(".o_property_3d_message").textContent = message;
        }
    }

    async init() {
        this.started = true;
        this.setStatus("loading", _t("Loading the 3D view..."));
        try {
            await this.waitFor(loadThree());
        } catch {
            this.setStatus("error", _t("The 3D view could not be loaded."));
            return;
        }
        const THREE = window.THREE;
        this.THREE = THREE;
        THREE.ColorManagement.legacyMode = false;
        this.createScene(THREE);
        this.materials = createMaterials(THREE, this.renderer);

        const modelUrl = this.el.dataset.modelUrl;
        let exterior = null;
        if (modelUrl) {
            try {
                exterior = await this.waitFor(this.loadModel(THREE, modelUrl));
                this.uploaded = true;
            } catch {
                exterior = null;
            }
        }
        if (!exterior) {
            exterior = buildPropertyModel(THREE, this.spec, this.materials);
        }
        this.exterior = exterior;
        this.scene.add(exterior);
        this.modes = ["exterior"];
        if (!this.uploaded && this.spec.interior) {
            const plan = generatePlan(this.spec);
            if (plan.floors.length) {
                // An apartment is shown on a typical upper floor, so its windows look down on the grounds.
                const baseY = this.spec.kind === "apartment" ? Math.min(Math.max((this.spec.floors || 1) - 1, 0), 4) * 3.1 : 0;
                this.interior = buildInterior(THREE, this.materials, plan, { baseY });
                this.interior.group.visible = false;
                this.scene.add(this.interior.group);
                this.interiorSurroundings = this.buildInteriorSurroundings(THREE, plan);
                this.interiorSurroundings.visible = false;
                this.scene.add(this.interiorSurroundings);
                this.interior.group.updateMatrixWorld(true);
                this.modes.push("interior", "walk");
            }
        } else if (this.uploaded) {
            this.modes.push("walk");
        }
        this.renderRooms();
        this.el.dataset.modes = this.modes.join(",");
        this.setMode("exterior");
        this.setStatus("ready");
        this.clock = new THREE.Clock();
        this.loop();
    }

    /** Lawn and trees seen through the windows of the interior. */
    buildInteriorSurroundings(THREE, plan) {
        const group = new THREE.Group();
        const size = Math.max(...plan.floors.map((floor) => Math.max(floor.width, floor.depth)));
        const ground = new THREE.Mesh(new THREE.CircleGeometry(size * 4 + 60, 48), this.materials.fit(this.materials.grass, size * 8, size * 8));
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.05;
        ground.receiveShadow = true;
        group.add(ground);
        const trees = 14;
        for (let i = 0; i < trees; i++) {
            const angle = (i / trees) * Math.PI * 2;
            const distance = size * 0.75 + 6 + (i % 3) * 3;
            const x = Math.cos(angle) * distance;
            const z = Math.sin(angle) * distance;
            const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.26, 2.4, 8), this.materials.trunk);
            trunk.position.set(x, 1.2, z);
            const crown = new THREE.Mesh(new THREE.IcosahedronGeometry(1.8 + (i % 2) * 0.6, 1), i % 2 ? this.materials.leaf : this.materials.leafLight);
            crown.position.set(x, 3.6, z);
            crown.castShadow = trunk.castShadow = true;
            group.add(trunk, crown);
        }
        return group;
    }

    createScene(THREE) {
        const width = this.viewport.clientWidth || 600;
        const height = this.viewport.clientHeight || 400;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.05, 5000);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setSize(width, height);
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.05;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.domElement.classList.add("o_property_3d_canvas");
        this.viewport.appendChild(this.renderer.domElement);

        // Reflections from a neutral studio environment
        const pmrem = new THREE.PMREMGenerator(this.renderer);
        this.environment = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
        this.scene.environment = this.environment;
        pmrem.dispose();

        // Sky dome with a gradient from blue to a warm horizon
        const sky = new THREE.Mesh(
            new THREE.SphereGeometry(2000, 32, 16),
            new THREE.ShaderMaterial({
                side: THREE.BackSide,
                depthWrite: false,
                uniforms: {
                    top: { value: new THREE.Color(0x5b8fc9) },
                    horizon: { value: new THREE.Color(0xe7eef6) },
                    bottom: { value: new THREE.Color(0xdfe6dc) },
                },
                vertexShader: "varying vec3 vPos; void main() { vPos = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
                fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec3 bottom; varying vec3 vPos;
                    void main() { float h = vPos.y; vec3 c = h > 0.0 ? mix(horizon, top, pow(h, 0.6)) : mix(horizon, bottom, min(-h * 4.0, 1.0));
                    gl_FragColor = vec4(c, 1.0); }`,
            })
        );
        this.sky = sky;
        this.scene.add(sky);

        this.hemisphere = new THREE.HemisphereLight(0xdfeaff, 0x6d8f5c, 0.55);
        this.scene.add(this.hemisphere);
        this.sun = new THREE.DirectionalLight(0xfff3df, 1.6);
        this.sun.castShadow = true;
        this.sun.shadow.mapSize.set(2048, 2048);
        this.sun.shadow.bias = -0.0004;
        this.sun.shadow.normalBias = 0.02;
        this.scene.add(this.sun);
        this.scene.add(this.sun.target);
        // A soft light carried by the visitor indoors
        this.walkLight = new THREE.PointLight(0xfff1dc, 0, 9, 1.6);
        this.scene.add(this.walkLight);

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.autoRotate = this.autoRotate;
        this.controls.autoRotateSpeed = 0.7;
        this.controls.maxPolarAngle = Math.PI * 0.49;
        // A visitor taking control stops the automatic rotation.
        this.controls.addEventListener("start", () => {
            if (this.autoRotate) {
                this.autoRotate = false;
                this.controls.autoRotate = false;
                this.updateContent();
            }
        });
        this.walk = new WalkControls(THREE, this.camera, this.renderer.domElement);

        const resizeObserver = new ResizeObserver(() => this.resize());
        resizeObserver.observe(this.viewport);
        this.registerCleanup(() => {
            resizeObserver.disconnect();
            cancelAnimationFrame(this.frame);
            this.controls.dispose();
            this.walk.dispose();
            this.scene.traverse((object) => {
                object.geometry?.dispose();
                for (const mat of [].concat(object.material || [])) {
                    mat.map?.dispose();
                    mat.dispose();
                }
            });
            this.environment?.dispose();
            this.renderer.dispose();
            this.renderer.domElement.remove();
        });
    }

    loadModel(THREE, url) {
        return new Promise((resolve, reject) => {
            new THREE.GLTFLoader().load(
                url,
                (gltf) => {
                    const model = gltf.scene;
                    model.traverse((object) => {
                        if (object.isMesh) {
                            object.castShadow = true;
                            object.receiveShadow = true;
                        }
                    });
                    // Stand the model on the ground, centred.
                    const box = new THREE.Box3().setFromObject(model);
                    const center = box.getCenter(new THREE.Vector3());
                    model.position.sub(new THREE.Vector3(center.x, box.min.y, center.z));
                    const size = box.getSize(new THREE.Vector3());
                    const group = new THREE.Group();
                    group.add(model);
                    const ground = new THREE.Mesh(
                        new THREE.CircleGeometry(Math.max(size.x, size.z) * 1.5 + 2, 64),
                        new THREE.MeshStandardMaterial({ color: 0x86b56e, roughness: 0.95 })
                    );
                    ground.rotation.x = -Math.PI / 2;
                    ground.position.y = -0.01;
                    ground.receiveShadow = true;
                    ground.userData.surroundings = true;
                    group.add(ground);
                    this.modelSize = size;
                    resolve(group);
                },
                undefined,
                reject
            );
        });
    }

    // ------------------------------------------------------------ modes
    onModeClick(ev) {
        this.setMode(ev.currentTarget.dataset.mode);
    }

    setMode(mode) {
        if (!this.modes.includes(mode) || !this.scene) {
            return;
        }
        this.mode = mode;
        this.el.dataset.mode = mode;
        const inside = mode !== "exterior";
        const generatedInterior = inside && this.interior;
        this.exterior.visible = !generatedInterior;
        if (this.interior) {
            this.interior.group.visible = !!generatedInterior;
            this.interiorSurroundings.visible = !!generatedInterior;
            this.interior.levels.forEach((level, index) => {
                // In the dollhouse, show the chosen storey only; light the storey being visited.
                level.group.visible = mode === "walk" || index === this.levelIndex;
                level.lights.forEach((light) => (light.visible = index === this.levelIndex));
                level.group.traverse((object) => {
                    if (object.userData.label) {
                        object.visible = mode === "interior";
                    }
                });
            });
        }
        this.controls.enabled = mode !== "walk";
        this.walk.enabled = mode === "walk";
        this.walkLight.intensity = mode === "walk" && this.interior ? 0.35 : 0;
        this.hemisphere.intensity = generatedInterior ? 0.6 : 0.55;
        this.renderer.toneMappingExposure = generatedInterior ? 0.95 : 1.05;
        this.controls.autoRotate = this.autoRotate && mode === "exterior";
        this.renderer.domElement.style.cursor = mode === "walk" ? "crosshair" : "";
        if (mode === "exterior") {
            this.fitView(this.exterior);
        } else if (mode === "interior") {
            this.fitView(this.interior.levels[this.levelIndex].group, { interior: true });
        } else {
            this.startWalk();
        }
        this.renderRooms();
        this.updateContent();
    }

    startWalk(room = null) {
        const THREE = this.THREE;
        this.camera.fov = 70;
        this.camera.near = 0.05;
        this.camera.updateProjectionMatrix();
        this.scene.fog = null;
        if (this.interior) {
            const level = this.interior.levels[this.levelIndex];
            this.walk.free = false;
            const target = room || level.rooms.find((r) => r.type === "living" || r.type === "workspace" || r.type === "sales" || r.type === "hallStore") || level.rooms[0];
            // Stand just inside the doorway, looking across the room towards its windows.
            const [x0, z0, x1, z1] = target.bounds;
            // Rooms are entered from the corridor, a shop from the street.
            const back = target.side === "back" || target.type === "sales";
            const yaw = back ? 0 : Math.PI;
            const cx = (x0 + x1) / 2;
            let spot = [cx, (z0 + z1) / 2];
            for (let i = 0; i < 40; i++) {
                const depth = Math.min(0.8 + i * 0.15, (z1 - z0) - 0.4);
                const dx = ((i % 5) - 2) * 0.5;
                const candidate = [cx + dx, back ? z1 - depth : z0 + depth];
                if (!this.walk.blockedAt(level, candidate[0], candidate[1])) {
                    spot = candidate;
                    break;
                }
            }
            this.walk.placeAt(level, spot[0], spot[1], yaw);
            this.walk.pitch = -0.12;
            this.walk.applyRotation();
            this.currentRoom = target.name;
        } else {
            // Uploaded model: stand in front of it at eye height and fly freely.
            const size = this.modelSize || new THREE.Vector3(10, 5, 10);
            this.walk.free = true;
            this.walk.placeAt({ y: 0, group: this.exterior, floors: [], collisions: [] }, 0, size.z / 2 + 3, 0);
        }
    }

    onRoomClick(ev) {
        const button = ev.target.closest("[data-room], [data-level]");
        if (!button || !this.interior) {
            return;
        }
        if (button.dataset.level !== undefined) {
            this.levelIndex = Number(button.dataset.level);
            this.setMode(this.mode === "exterior" ? "interior" : this.mode);
            return;
        }
        const level = this.interior.levels[this.levelIndex];
        const room = level.rooms[Number(button.dataset.room)];
        if (this.mode !== "walk") {
            this.setMode("walk");
        }
        this.startWalk(room);
        this.renderRooms();
    }

    renderRooms() {
        if (!this.roomsEl) {
            return;
        }
        this.roomsEl.replaceChildren();
        if (!this.interior || this.mode === "exterior") {
            this.roomsEl.classList.add("d-none");
            return;
        }
        this.roomsEl.classList.remove("d-none");
        const button = (text, data, active) => {
            const el = document.createElement("button");
            el.type = "button";
            el.className = `btn btn-sm ${active ? "btn-primary" : "btn-light border"} o_property_3d_room`;
            el.textContent = text;
            Object.assign(el.dataset, data);
            return el;
        };
        if (this.interior.levels.length > 1) {
            this.interior.levels.forEach((level, index) => {
                this.roomsEl.appendChild(button(level.name, { level: index }, index === this.levelIndex));
            });
            const sep = document.createElement("span");
            sep.className = "vr mx-1";
            this.roomsEl.appendChild(sep);
        }
        this.interior.levels[this.levelIndex].rooms.forEach((room, index) => {
            if (room.type !== "hall" && room.type !== "stairs") {
                this.roomsEl.appendChild(button(room.name, { room: index }, this.mode === "walk" && this.currentRoom === room.name));
            }
        });
    }

    // ------------------------------------------------------------ camera
    fitView(subject, { interior = false } = {}) {
        const THREE = this.THREE;
        const box = new THREE.Box3();
        subject.updateMatrixWorld(true);
        for (const child of subject.children) {
            if (!child.userData.surroundings && !child.userData.label) {
                box.expandByObject(child);
            }
        }
        if (box.isEmpty()) {
            box.setFromObject(subject);
        }
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const extent = Math.max(size.x, size.y, size.z, 1);
        let position;
        if (interior) {
            // High three-quarter view into the cut-away floor plan
            center.y = box.min.y + 0.5;
            const distance = Math.max(size.x, size.z) * 1.05;
            position = new THREE.Vector3(center.x + distance * 0.35, center.y + distance * 0.95, center.z + distance * 0.7);
            this.controls.maxPolarAngle = Math.PI * 0.42;
        } else {
            center.y = Math.min(center.y, size.y * 0.45);
            const distance = extent * 1.25;
            position = new THREE.Vector3(center.x + distance * 0.75, center.y + distance * 0.5, center.z + distance * 0.95);
            this.controls.maxPolarAngle = Math.PI * 0.49;
        }
        this.home = { position, target: center.clone() };
        this.camera.fov = 45;
        this.camera.near = extent / 500;
        this.camera.far = 6000;
        this.camera.updateProjectionMatrix();
        this.controls.minDistance = extent * (interior ? 0.3 : 0.15);
        this.controls.maxDistance = extent * 5;
        this.scene.fog = interior ? null : new THREE.Fog(0xe7eef6, extent * 4, extent * 14);
        this.sun.position.set(center.x + extent * 0.9, extent * 1.6, center.z + extent * 0.7);
        this.sun.target.position.copy(center);
        const shadow = this.sun.shadow.camera;
        shadow.left = shadow.bottom = -extent * 1.6;
        shadow.right = shadow.top = extent * 1.6;
        shadow.near = 0.5;
        shadow.far = extent * 6;
        shadow.updateProjectionMatrix();
        this.resetView();
    }

    loop() {
        this.frame = requestAnimationFrame(() => this.loop());
        const delta = Math.min(this.clock.getDelta(), 0.1);
        if (!this.visible && !document.fullscreenElement) {
            return;
        }
        if (this.mode === "walk") {
            this.walk.update(delta);
            this.walkLight.position.copy(this.camera.position);
            this.updateCurrentRoom();
        } else {
            this.controls.update();
        }
        this.sky.position.copy(this.camera.position);
        this.renderer.render(this.scene, this.camera);
    }

    updateCurrentRoom() {
        if (!this.interior) {
            return;
        }
        const { x, z } = this.camera.position;
        const room = this.interior.levels[this.levelIndex].rooms.find(
            ({ bounds: [x0, z0, x1, z1] }) => x >= x0 && x <= x1 && z >= z0 && z <= z1
        );
        if (room && room.name !== this.currentRoom) {
            this.currentRoom = room.name;
            this.el.dataset.room = room.name;
            this.renderRooms();
        }
    }

    resize() {
        if (!this.renderer) {
            return;
        }
        const width = this.viewport.clientWidth;
        const height = this.viewport.clientHeight;
        if (width && height) {
            this.renderer.setSize(width, height);
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
        }
    }

    toggleRotate() {
        this.autoRotate = !this.autoRotate;
        if (this.controls) {
            this.controls.autoRotate = this.autoRotate && this.mode === "exterior";
        }
    }

    resetView() {
        if (this.mode === "walk") {
            this.startWalk();
            return;
        }
        if (!this.home) {
            return;
        }
        this.camera.position.copy(this.home.position);
        this.controls.target.copy(this.home.target);
        this.controls.update();
    }

    toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else if (this.el.requestFullscreen) {
            this.el.requestFullscreen();
        }
    }

    onFullscreenChange() {
        this.el.classList.toggle("o_property_3d_is_fullscreen", document.fullscreenElement === this.el);
        this.resize();
    }
}

registry.category("public.interactions").add("inom_rental_management_website.property_3d", Property3DView);
