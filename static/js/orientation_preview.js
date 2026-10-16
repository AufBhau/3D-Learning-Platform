(function () {
  "use strict";

  const previewEl = document.getElementById("orientation-preview");
  const loadingEl = document.getElementById("orientation-loading");
  const statusEl = document.getElementById("orientation-status");
  const configEl = document.getElementById("orientation-config");
  const fileInput = document.getElementById("id_model_file");
  const inputX = document.getElementById("id_model_rotation_x");
  const inputY = document.getElementById("id_model_rotation_y");
  const inputZ = document.getElementById("id_model_rotation_z");
  const inputZoom = document.getElementById("id_camera_distance_factor");
  const inputZoomMin = document.getElementById("id_camera_min_distance_factor");
  const inputZoomMax = document.getElementById("id_camera_max_distance_factor");
  const modeModelBtn = document.getElementById("orientation-mode-model");
  const modeOrbitBtn = document.getElementById("orientation-mode-orbit");

  if (!previewEl || !configEl || typeof THREE === "undefined") {
    return;
  }

  const config = JSON.parse(configEl.textContent);
  let scene;
  let camera;
  let renderer;
  let controls;
  let currentRoot = null;
  let objectUrl = null;
  let interactMode = "model";
  let isDraggingModel = false;
  let lastPointer = null;
  let baseFitDistance = 1;
  const _euler = new THREE.Euler(0, 0, 0, "XYZ");
  const _deltaEuler = new THREE.Euler(0, 0, 0, "XYZ");
  const _quaternion = new THREE.Quaternion();
  const _deltaQuat = new THREE.Quaternion();

  function setStatus(message) {
    if (statusEl) statusEl.textContent = message || "";
  }

  function setLoading(message, show) {
    if (!loadingEl) return;
    loadingEl.style.display = show ? "flex" : "none";
    if (show && message) {
      loadingEl.innerHTML =
        '<div class="loader"></div><p>' + message + "</p>";
    }
  }

  function roundVal(value) {
    return Math.round(value * 100) / 100;
  }

  function roundDeg(value) {
    return Math.round(value * 10) / 10;
  }

  function readDegrees() {
    return {
      x: Number(inputX && inputX.value) || 0,
      y: Number(inputY && inputY.value) || 0,
      z: Number(inputZ && inputZ.value) || 0,
    };
  }

  function writeDegrees(x, y, z) {
    if (inputX) inputX.value = String(roundDeg(x));
    if (inputY) inputY.value = String(roundDeg(y));
    if (inputZ) inputZ.value = String(roundDeg(z));
  }

  function readZoom() {
    return {
      distance: Math.max(0.05, Number(inputZoom && inputZoom.value) || 1),
      min: Math.max(0.05, Number(inputZoomMin && inputZoomMin.value) || 0.25),
      max: Math.max(0.1, Number(inputZoomMax && inputZoomMax.value) || 6),
    };
  }

  function writeZoomField(input, value) {
    if (input) input.value = String(roundVal(value));
  }

  function applyOrientationFromInputs() {
    if (!currentRoot) return;
    const deg = THREE.MathUtils.degToRad;
    const values = readDegrees();
    currentRoot.rotation.order = "XYZ";
    currentRoot.rotation.set(deg(values.x), deg(values.y), deg(values.z));
  }

  function syncInputsFromModel() {
    if (!currentRoot) return;
    const rad = THREE.MathUtils.radToDeg;
    _euler.setFromQuaternion(currentRoot.quaternion, "XYZ");
    writeDegrees(rad(_euler.x), rad(_euler.y), rad(_euler.z));
  }

  function currentDistanceFactor() {
    if (!camera || !controls || !baseFitDistance) return 1;
    return camera.position.distanceTo(controls.target) / baseFitDistance;
  }

  function applyZoomLimits() {
    if (!controls || !baseFitDistance) return;
    const zoom = readZoom();
    let minF = Math.min(zoom.min, zoom.max);
    let maxF = Math.max(zoom.min, zoom.max);
    controls.minDistance = baseFitDistance * minF;
    controls.maxDistance = baseFitDistance * maxF;
  }

  function applyCameraDistanceFromInputs() {
    if (!camera || !controls || !baseFitDistance) return;
    applyZoomLimits();
    const zoom = readZoom();
    const factor = Math.min(
      Math.max(zoom.distance, controls.minDistance / baseFitDistance),
      controls.maxDistance / baseFitDistance
    );
    const offset = camera.position.clone().sub(controls.target);
    if (offset.lengthSq() < 1e-8) {
      offset.set(0.55, 0.35, 1).normalize();
    } else {
      offset.normalize();
    }
    camera.position
      .copy(controls.target)
      .add(offset.multiplyScalar(baseFitDistance * factor));
    controls.update();
    writeZoomField(inputZoom, factor);
  }

  function syncZoomInputFromCamera() {
    if (!camera || !controls || !baseFitDistance) return;
    writeZoomField(inputZoom, currentDistanceFactor());
  }

  function setInteractMode(mode) {
    interactMode = mode === "orbit" ? "orbit" : "model";
    if (controls) {
      controls.enableRotate = interactMode === "orbit";
      controls.enableZoom = true;
    }
    if (modeModelBtn) {
      modeModelBtn.classList.toggle("is-active", interactMode === "model");
    }
    if (modeOrbitBtn) {
      modeOrbitBtn.classList.toggle("is-active", interactMode === "orbit");
    }
    previewEl.classList.toggle("is-model-mode", interactMode === "model");
    previewEl.classList.toggle("is-orbit-mode", interactMode === "orbit");
    if (interactMode === "model") {
      setStatus(
        "Drag to rotate · Scroll to zoom · Use Lock zoom / Lock closest / Lock farthest."
      );
    } else {
      setStatus("Orbit camera mode — scroll still zooms within your locked limits.");
    }
  }

  function computeBaseFit(object3d) {
    const box = new THREE.Box3().setFromObject(object3d);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const fitDist = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));
    return fitDist * 1.7;
  }

  function fitCameraToObject(object3d) {
    if (!object3d || !camera || !controls) return;
    const box = new THREE.Box3().setFromObject(object3d);
    const center = box.getCenter(new THREE.Vector3());
    baseFitDistance = computeBaseFit(object3d);
    controls.target.copy(center);
    applyZoomLimits();
    const zoom = readZoom();
    const distance = baseFitDistance * zoom.distance;
    camera.position.set(
      center.x + distance * 0.55,
      center.y + distance * 0.35,
      center.z + distance
    );
    // Keep the actual distance equal to factor * baseFitDistance.
    const offset = camera.position.clone().sub(controls.target).normalize();
    camera.position
      .copy(controls.target)
      .add(offset.multiplyScalar(distance));
    controls.update();
  }

  function mountMesh(object3d) {
    if (currentRoot) {
      scene.remove(currentRoot);
    }
    currentRoot = new THREE.Group();
    currentRoot.rotation.order = "XYZ";
    currentRoot.add(object3d);
    applyOrientationFromInputs();
    scene.add(currentRoot);
    fitCameraToObject(currentRoot);
  }

  function addPlaceholder() {
    const group = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(1.4, 0.5, 0.9),
      new THREE.MeshStandardMaterial({
        color: 0x6366f1,
        metalness: 0.2,
        roughness: 0.45,
      })
    );
    group.add(body);
    mountMesh(group);
    setInteractMode(interactMode);
  }

  function loadUrl(url) {
    if (!url) {
      addPlaceholder();
      setLoading("", false);
      return;
    }
    setLoading("Loading model…", true);
    const loader = new THREE.GLTFLoader();
    loader.load(
      url,
      function (gltf) {
        mountMesh(gltf.scene);
        setLoading("", false);
        setInteractMode(interactMode);
      },
      undefined,
      function () {
        addPlaceholder();
        setLoading("", false);
        setStatus("Could not load this model file.");
      }
    );
  }

  function onPointerDown(event) {
    if (interactMode !== "model" || event.button !== 0 || !currentRoot) {
      return;
    }
    isDraggingModel = true;
    lastPointer = { x: event.clientX, y: event.clientY };
    if (controls) controls.enabled = false;
    previewEl.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (!isDraggingModel || !currentRoot || !lastPointer) return;
    const dx = event.clientX - lastPointer.x;
    const dy = event.clientY - lastPointer.y;
    lastPointer = { x: event.clientX, y: event.clientY };

    const speed = 0.01;
    _deltaEuler.set(dy * speed, dx * speed, 0, "XYZ");
    _deltaQuat.setFromEuler(_deltaEuler);
    _quaternion.copy(currentRoot.quaternion).multiply(_deltaQuat);
    currentRoot.quaternion.copy(_quaternion);
    syncInputsFromModel();
  }

  function onPointerUp(event) {
    if (!isDraggingModel) return;
    isDraggingModel = false;
    lastPointer = null;
    if (controls) controls.enabled = true;
    try {
      previewEl.releasePointerCapture(event.pointerId);
    } catch (err) {
      // ignore
    }
    syncInputsFromModel();
  }

  function initScene() {
    const width = previewEl.clientWidth || 420;
    const height = previewEl.clientHeight || 320;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080e1a);
    camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 2000);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    previewEl.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableRotate = false;
    controls.enableZoom = true;
    controls.addEventListener("change", syncZoomInputFromCamera);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 0.9));
    const key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(4, 6, 3);
    scene.add(key);
    scene.add(new THREE.AxesHelper(0.75));

    previewEl.addEventListener("pointerdown", onPointerDown);
    previewEl.addEventListener("pointermove", onPointerMove);
    previewEl.addEventListener("pointerup", onPointerUp);
    previewEl.addEventListener("pointercancel", onPointerUp);
    window.addEventListener("resize", onResize);
    animate();
  }

  function onResize() {
    if (!camera || !renderer) return;
    const width = previewEl.clientWidth || 420;
    const height = previewEl.clientHeight || 320;
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  function nudge(axis, delta) {
    const values = readDegrees();
    values[axis] = values[axis] + delta;
    writeDegrees(values.x, values.y, values.z);
    applyOrientationFromInputs();
  }

  ["input", "change"].forEach(function (eventName) {
    [inputX, inputY, inputZ].forEach(function (input) {
      if (!input) return;
      input.addEventListener(eventName, function () {
        applyOrientationFromInputs();
      });
    });
    [inputZoom, inputZoomMin, inputZoomMax].forEach(function (input) {
      if (!input) return;
      input.addEventListener(eventName, function () {
        applyCameraDistanceFromInputs();
      });
    });
  });

  document.querySelectorAll("[data-orient-nudge]").forEach(function (button) {
    button.addEventListener("click", function () {
      const axis = button.getAttribute("data-orient-axis");
      const delta = Number(button.getAttribute("data-orient-nudge")) || 0;
      if (!axis) return;
      nudge(axis, delta);
    });
  });

  const resetBtn = document.getElementById("orientation-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      writeDegrees(0, 0, 0);
      applyOrientationFromInputs();
      if (currentRoot) fitCameraToObject(currentRoot);
    });
  }

  const lockZoomBtn = document.getElementById("zoom-lock-default");
  if (lockZoomBtn) {
    lockZoomBtn.addEventListener("click", function () {
      const factor = currentDistanceFactor();
      writeZoomField(inputZoom, factor);
      applyZoomLimits();
      setStatus(
        "Default zoom locked at " + roundVal(factor) + "× fit. Save the lesson to keep it."
      );
    });
  }

  const lockMinBtn = document.getElementById("zoom-lock-min");
  if (lockMinBtn) {
    lockMinBtn.addEventListener("click", function () {
      const factor = currentDistanceFactor();
      writeZoomField(inputZoomMin, factor);
      applyZoomLimits();
      setStatus(
        "Closest zoom locked at " + roundVal(factor) + "× fit. Students cannot zoom closer."
      );
    });
  }

  const lockMaxBtn = document.getElementById("zoom-lock-max");
  if (lockMaxBtn) {
    lockMaxBtn.addEventListener("click", function () {
      const factor = currentDistanceFactor();
      writeZoomField(inputZoomMax, factor);
      applyZoomLimits();
      setStatus(
        "Farthest zoom locked at " + roundVal(factor) + "× fit. Students cannot zoom farther."
      );
    });
  }

  const lockBtn = document.getElementById("orientation-lock");
  const saveBtn = document.getElementById("lock-orientation-save");
  if (lockBtn) {
    lockBtn.addEventListener("click", function () {
      syncInputsFromModel();
      syncZoomInputFromCamera();
      setStatus("Orientation & zoom locked — saving…");
      if (saveBtn) {
        saveBtn.click();
      } else {
        const form = document.getElementById("lesson-form");
        if (form) form.requestSubmit();
      }
    });
  }

  if (modeModelBtn) {
    modeModelBtn.addEventListener("click", function () {
      setInteractMode("model");
    });
  }
  if (modeOrbitBtn) {
    modeOrbitBtn.addEventListener("click", function () {
      setInteractMode("orbit");
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
      objectUrl = URL.createObjectURL(file);
      loadUrl(objectUrl);
    });
  }

  // Seed zoom fields from saved lesson config when empty/default create.
  const savedZoom = config.cameraZoom || {};
  if (inputZoom && savedZoom.distance != null) {
    writeZoomField(inputZoom, savedZoom.distance);
  }
  if (inputZoomMin && savedZoom.min != null) {
    writeZoomField(inputZoomMin, savedZoom.min);
  }
  if (inputZoomMax && savedZoom.max != null) {
    writeZoomField(inputZoomMax, savedZoom.max);
  }

  initScene();
  setInteractMode("model");
  loadUrl(config.modelUrl || "");
})();
