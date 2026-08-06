(function () {
  "use strict";

  const viewerEl = document.getElementById("placer-viewer");
  const loadingEl = document.getElementById("placer-loading");
  const statusEl = document.getElementById("placer-status");
  const configEl = document.getElementById("placer-config");
  const formEl = document.getElementById("hotspot-form");

  if (!viewerEl || !configEl || typeof THREE === "undefined") {
    return;
  }

  const config = JSON.parse(configEl.textContent);
  const inputX = document.getElementById("id_position_x");
  const inputY = document.getElementById("id_position_y");
  const inputZ = document.getElementById("id_position_z");

  let scene;
  let camera;
  let renderer;
  let controls;
  let currentModel = null;
  let annotationGroup = new THREE.Group();
  let previewMarker = null;
  let raycaster = new THREE.Raycaster();
  let pointer = new THREE.Vector2();
  let pointerDown = null;
  let placed = false;

  function setStatus(message, ok) {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.toggle("is-ok", Boolean(ok));
  }

  function setLoading(message, showSpinner) {
    if (!loadingEl) return;
    loadingEl.style.display = "flex";
    if (showSpinner) {
      loadingEl.innerHTML =
        '<div class="loader"></div><p>' + message + "</p>";
    } else {
      loadingEl.innerHTML = "<p>" + message + "</p>";
    }
  }

  function hideLoading() {
    if (loadingEl) loadingEl.style.display = "none";
  }

  function roundCoord(value) {
    return Math.round(Number(value) * 1000) / 1000;
  }

  function writeCoords(x, y, z) {
    if (inputX) inputX.value = String(roundCoord(x));
    if (inputY) inputY.value = String(roundCoord(y));
    if (inputZ) inputZ.value = String(roundCoord(z));
    placed = true;
    setStatus(
      "Position set — add a title and description, then save.",
      true
    );
  }

  function viewerSize() {
    const width = Math.max(viewerEl.clientWidth, 1);
    const height = Math.max(viewerEl.clientHeight, 1);
    return { width: width, height: height };
  }

  function estimateMarkerScale() {
    if (!currentModel) return 0.08;
    const size = new THREE.Box3()
      .setFromObject(currentModel)
      .getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    return Math.max(maxDim * 0.03, 0.05);
  }

  function ensurePreviewMarker() {
    if (previewMarker) return previewMarker;
    const scale = estimateMarkerScale();
    previewMarker = new THREE.Mesh(
      new THREE.SphereGeometry(scale * 1.15, 18, 18),
      new THREE.MeshStandardMaterial({
        color: 0xa78bfa,
        emissive: 0x5b21b6,
        metalness: 0.15,
        roughness: 0.3,
      })
    );
    previewMarker.visible = false;
    annotationGroup.add(previewMarker);
    return previewMarker;
  }

  function movePreview(x, y, z) {
    const marker = ensurePreviewMarker();
    marker.position.set(x, y, z);
    marker.visible = true;
  }

  function createExistingMarkers() {
    while (annotationGroup.children.length) {
      const child = annotationGroup.children[0];
      annotationGroup.remove(child);
    }
    previewMarker = null;

    const scale = estimateMarkerScale();
    const editingId = config.editingId;
    (config.annotations || []).forEach(function (annotation) {
      if (editingId && annotation.id === editingId) {
        return;
      }
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(scale, 16, 16),
        new THREE.MeshStandardMaterial({
          color: 0x22d3ee,
          emissive: 0x0e7490,
          metalness: 0.1,
          roughness: 0.35,
        })
      );
      marker.position.set(
        Number(annotation.x) || 0,
        Number(annotation.y) || 0,
        Number(annotation.z) || 0
      );
      annotationGroup.add(marker);
    });
  }

  function initScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const size = viewerSize();
    camera = new THREE.PerspectiveCamera(
      45,
      size.width / size.height,
      0.1,
      2000
    );
    camera.position.set(3, 2, 5);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(size.width, size.height, false);
    renderer.outputEncoding = THREE.sRGBEncoding;
    viewerEl.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 0.9));
    const key = new THREE.DirectionalLight(0xffffff, 1);
    key.position.set(5, 8, 4);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xa5b4fc, 0.4);
    fill.position.set(-4, 2, -3);
    scene.add(fill);

    scene.add(annotationGroup);

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointerup", onPointerUp);
    window.addEventListener("resize", onResize);

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(function () {
        onResize();
      });
      observer.observe(viewerEl);
    }

    animate();
  }

  function fitCameraToObject(object3d) {
    if (!object3d || !camera || !controls) return;

    const box = new THREE.Box3().setFromObject(object3d);
    if (box.isEmpty()) return;

    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;

    // Frame tightly so small / large models both fill the view
    const fitHeightDistance =
      maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));
    const fitWidthDistance = fitHeightDistance / camera.aspect;
    const distance = Math.max(fitHeightDistance, fitWidthDistance) * 1.15;

    camera.near = Math.max(distance / 100, 0.01);
    camera.far = Math.max(distance * 100, 100);
    camera.updateProjectionMatrix();
    camera.position.set(
      center.x + distance * 0.45,
      center.y + distance * 0.28,
      center.z + distance
    );
    controls.target.copy(center);
    controls.minDistance = maxDim * 0.2;
    controls.maxDistance = distance * 8;
    controls.update();
  }

  function addPlaceholderModel() {
    const group = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(1.4, 0.5, 0.9),
      new THREE.MeshStandardMaterial({
        color: 0x6366f1,
        metalness: 0.2,
        roughness: 0.45,
      })
    );
    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(0.35, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshStandardMaterial({
        color: 0x22d3ee,
        metalness: 0.1,
        roughness: 0.35,
      })
    );
    dome.position.y = 0.25;
    group.add(body);
    group.add(dome);
    scene.add(group);
    currentModel = group;
  }

  function afterModelReady() {
    onResize();
    fitCameraToObject(currentModel);
    createExistingMarkers();
    applyInitialPosition();
    // Layout may settle a frame later after flex sizing
    window.requestAnimationFrame(function () {
      onResize();
      fitCameraToObject(currentModel);
    });
  }

  function loadModel(url) {
    const loader = new THREE.GLTFLoader();
    loader.load(
      url,
      function (gltf) {
        if (currentModel) scene.remove(currentModel);
        currentModel = gltf.scene;
        scene.add(currentModel);
        hideLoading();
        afterModelReady();
      },
      undefined,
      function (error) {
        console.error("Failed to load model:", error);
        setLoading(
          "Could not load this 3D model. Showing a placeholder you can still click.",
          false
        );
        addPlaceholderModel();
        afterModelReady();
      }
    );
  }

  function applyInitialPosition() {
    const initial = config.initialPosition;
    if (!initial) return;
    const x = Number(initial.x) || 0;
    const y = Number(initial.y) || 0;
    const z = Number(initial.z) || 0;
    writeCoords(x, y, z);
    movePreview(x, y, z);
    setStatus("Existing position loaded — click the model to move it.", true);
  }

  function onPointerDown(event) {
    if (event.button !== 0) return;
    pointerDown = { x: event.clientX, y: event.clientY };
  }

  function onPointerUp(event) {
    if (event.button !== 0 || !pointerDown || !currentModel) {
      pointerDown = null;
      return;
    }

    const dx = event.clientX - pointerDown.x;
    const dy = event.clientY - pointerDown.y;
    pointerDown = null;
    if (dx * dx + dy * dy > 36) {
      return;
    }

    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);

    const hits = raycaster.intersectObject(currentModel, true);
    if (!hits.length) {
      setStatus("No surface hit — try clicking directly on the model.", false);
      return;
    }

    const point = hits[0].point;
    writeCoords(point.x, point.y, point.z);
    movePreview(point.x, point.y, point.z);
  }

  function onResize() {
    if (!camera || !renderer) return;
    const size = viewerSize();
    camera.aspect = size.width / size.height;
    camera.updateProjectionMatrix();
    renderer.setSize(size.width, size.height, false);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  if (formEl) {
    formEl.addEventListener("submit", function (event) {
      if (!placed && !config.initialPosition) {
        event.preventDefault();
        setStatus("Click the model first to set the hotspot position.", false);
        return;
      }
      if (!inputX.value || !inputY.value || !inputZ.value) {
        event.preventDefault();
        setStatus("Click the model first to set the hotspot position.", false);
      }
    });
  }

  initScene();

  if (config.modelUrl) {
    setLoading("Loading 3D model…", true);
    loadModel(config.modelUrl);
  } else {
    setLoading(
      "No model on this lesson yet — using a placeholder. Upload a .glb on the lesson edit page for real placement.",
      false
    );
    addPlaceholderModel();
    afterModelReady();
  }
})();
