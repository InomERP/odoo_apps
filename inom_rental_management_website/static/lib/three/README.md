# three.js r147

Unmodified files from the npm package `three@0.147.0` (MIT licence, see LICENSE):

- `three.min.js` (build/three.min.js)
- `OrbitControls.js` (examples/js/controls/OrbitControls.js)
- `GLTFLoader.js` (examples/js/loaders/GLTFLoader.js)
- `RoomEnvironment.js` (examples/js/environments/RoomEnvironment.js)

Package checksum (sha1, as published on registry.npmjs.org): `1974af9e8e0c1efb3a8561334d57c0b6c29a7951`.

r147 is the last release shipping these non-module builds, which load as plain scripts and define the
global `THREE`. They are loaded on demand by `static/src/property_3d/property_3d.js` only when a
property's 3D view scrolls into sight, and are not part of any asset bundle.
