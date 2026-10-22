/**
 * First-person walk-through: drag to look around, WASD or arrow keys to move, tap the floor to
 * walk there. Walls stop the visitor (doorways let them through) and they can only stand on a floor.
 */

const EYE_HEIGHT = 1.6;
const RADIUS = 0.28;
const SPEED = 1.8; // metres per second

function distanceToSegment(px, pz, [ax, az], [bx, bz]) {
    const dx = bx - ax;
    const dz = bz - az;
    const lengthSq = dx * dx + dz * dz || 1e-9;
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / lengthSq));
    return Math.hypot(px - (ax + t * dx), pz - (az + t * dz));
}

export class WalkControls {
    /**
     * @param {object} THREE
     * @param {THREE.PerspectiveCamera} camera
     * @param {HTMLElement} element  the canvas receiving pointer events
     */
    constructor(THREE, camera, element) {
        this.THREE = THREE;
        this.camera = camera;
        this.element = element;
        this.enabled = false;
        this.yaw = 0;
        this.pitch = 0;
        this.keys = new Set();
        this.target = null;
        this.level = null; // { group, floors, collisions, y }
        this.free = false; // free flight for uploaded models (no floor plan to collide with)
        this.raycaster = new THREE.Raycaster();
        this.down = new THREE.Vector3(0, -1, 0);
        this.listeners = [];
        const on = (target, event, handler, options) => {
            target.addEventListener(event, handler, options);
            this.listeners.push(() => target.removeEventListener(event, handler, options));
        };
        let dragging = null;
        on(element, "pointerdown", (ev) => {
            if (!this.enabled) {
                return;
            }
            dragging = { x: ev.clientX, y: ev.clientY, moved: 0, time: Date.now() };
            element.setPointerCapture?.(ev.pointerId);
        });
        on(element, "pointermove", (ev) => {
            if (!this.enabled || !dragging) {
                return;
            }
            const dx = ev.clientX - dragging.x;
            const dy = ev.clientY - dragging.y;
            dragging.x = ev.clientX;
            dragging.y = ev.clientY;
            dragging.moved += Math.abs(dx) + Math.abs(dy);
            this.yaw -= dx * 0.005;
            this.pitch = Math.max(-1.2, Math.min(1.2, this.pitch - dy * 0.005));
            this.target = null;
        });
        on(element, "pointerup", (ev) => {
            if (!this.enabled || !dragging) {
                return;
            }
            // A tap (not a drag) walks to the point of the floor under the finger.
            if (dragging.moved < 6 && Date.now() - dragging.time < 400) {
                this.walkToScreenPoint(ev);
            }
            dragging = null;
        });
        on(element, "dblclick", (ev) => this.enabled && this.walkToScreenPoint(ev));
        on(element, "wheel", (ev) => {
            if (!this.enabled) {
                return;
            }
            ev.preventDefault();
            this.camera.fov = Math.max(35, Math.min(85, this.camera.fov + ev.deltaY * 0.03));
            this.camera.updateProjectionMatrix();
        }, { passive: false });
        on(window, "keydown", (ev) => {
            if (!this.enabled || ev.target.closest?.("input, textarea, select")) {
                return;
            }
            const key = ev.key.toLowerCase();
            if (["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright", "shift"].includes(key)) {
                this.keys.add(key);
                this.target = null;
                if (key.startsWith("arrow")) {
                    ev.preventDefault();
                }
            }
        });
        on(window, "keyup", (ev) => this.keys.delete(ev.key.toLowerCase()));
        on(window, "blur", () => this.keys.clear());
    }

    dispose() {
        this.listeners.forEach((off) => off());
    }

    /** Place the visitor at (x, z) of a level, looking along `yaw`. */
    placeAt(level, x, z, yaw = this.yaw) {
        this.level = level;
        this.yaw = yaw;
        this.pitch = -0.05;
        this.target = null;
        this.camera.position.set(x, (level ? level.y : 0) + EYE_HEIGHT, z);
        this.applyRotation();
    }

    applyRotation() {
        const euler = new this.THREE.Euler(this.pitch, this.yaw, 0, "YXZ");
        this.camera.quaternion.setFromEuler(euler);
    }

    walkToScreenPoint(ev) {
        if (!this.level) {
            return;
        }
        const rect = this.element.getBoundingClientRect();
        const pointer = new this.THREE.Vector2(
            ((ev.clientX - rect.left) / rect.width) * 2 - 1,
            -((ev.clientY - rect.top) / rect.height) * 2 + 1
        );
        this.raycaster.setFromCamera(pointer, this.camera);
        const hit = this.raycaster.intersectObjects(this.level.floors, false)[0];
        if (hit) {
            this.target = new this.THREE.Vector2(hit.point.x, hit.point.z);
        }
    }

    /** Whether a visitor could stand at (x, z) of a given level. */
    blockedAt(level, x, z) {
        const previous = this.level;
        this.level = level;
        const result = this.blocked(x, z);
        this.level = previous;
        return result;
    }

    blocked(x, z) {
        if (this.free || !this.level) {
            return false;
        }
        const offsetX = this.level.group.position.x;
        const offsetZ = this.level.group.position.z;
        const lx = x - offsetX;
        const lz = z - offsetZ;
        for (const wall of this.level.collisions) {
            if (wall.box) {
                const [x0, z0, x1, z1] = wall.box;
                if (lx > x0 - RADIUS && lx < x1 + RADIUS && lz > z0 - RADIUS && lz < z1 + RADIUS) {
                    return true;
                }
            } else if (distanceToSegment(lx, lz, wall.a, wall.b) < RADIUS + wall.half) {
                return true;
            }
        }
        // Only stand on a floor of this level.
        this.raycaster.set(new this.THREE.Vector3(x, this.level.y + 1, z), this.down);
        this.raycaster.far = 2;
        const onFloor = this.raycaster.intersectObjects(this.level.floors, false).length > 0;
        this.raycaster.far = Infinity;
        return !onFloor;
    }

    move(dx, dz) {
        const position = this.camera.position;
        const nx = position.x + dx;
        const nz = position.z + dz;
        if (!this.blocked(nx, nz)) {
            position.x = nx;
            position.z = nz;
            return true;
        }
        // Slide along walls
        if (!this.blocked(nx, position.z)) {
            position.x = nx;
            return true;
        }
        if (!this.blocked(position.x, nz)) {
            position.z = nz;
            return true;
        }
        return false;
    }

    update(delta) {
        if (!this.enabled) {
            return;
        }
        const step = SPEED * delta * (this.keys.has("shift") ? 2 : 1);
        const forward = (this.keys.has("w") || this.keys.has("arrowup") ? 1 : 0) - (this.keys.has("s") || this.keys.has("arrowdown") ? 1 : 0);
        const strafe = (this.keys.has("d") ? 1 : 0) - (this.keys.has("a") ? 1 : 0);
        const turn = (this.keys.has("arrowleft") ? 1 : 0) - (this.keys.has("arrowright") ? 1 : 0);
        if (turn) {
            this.yaw += turn * delta * 1.8;
        }
        const sin = Math.sin(this.yaw);
        const cos = Math.cos(this.yaw);
        if (forward || strafe) {
            this.move((-sin * forward + cos * strafe) * step, (-cos * forward - sin * strafe) * step);
        } else if (this.target) {
            const position = this.camera.position;
            const dx = this.target.x - position.x;
            const dz = this.target.y - position.z;
            const distance = Math.hypot(dx, dz);
            if (distance < 0.15) {
                this.target = null;
            } else {
                // Turn smoothly towards the destination while walking.
                const wanted = Math.atan2(-dx, -dz);
                let diff = wanted - this.yaw;
                diff = Math.atan2(Math.sin(diff), Math.cos(diff));
                this.yaw += diff * Math.min(1, delta * 4);
                const amount = Math.min(distance, step * 1.4);
                if (!this.move((dx / distance) * amount, (dz / distance) * amount)) {
                    this.target = null;
                }
            }
        }
        if (this.level && !this.free) {
            this.camera.position.y = this.level.y + EYE_HEIGHT;
        }
        this.applyRotation();
    }
}
