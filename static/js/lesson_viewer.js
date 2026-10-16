(function () {
  "use strict";

  const viewerEl = document.getElementById("viewer");
  const loadingEl = document.getElementById("loading");
  const hotspotDetailEl = document.getElementById("hotspot-detail");
  const hotspotListEl = document.getElementById("hotspot-list");
  const completionBadgeEl = document.getElementById("completion-badge");
  const progressActionsEl = document.getElementById("progress-actions");
  const configEl = document.getElementById("viewer-config");

  if (!viewerEl || typeof THREE === "undefined" || !configEl) {
    return;
  }

  const config = JSON.parse(configEl.textContent);
  let MODEL_URL = "";
  let MODEL_ORIENTATION = { x: 0, y: 0, z: 0 };
  let CAMERA_ZOOM = { distance: 1, min: 0.25, max: 6 };
  let ANNOTATIONS = [];
  let baseFitDistance = 1;

  let scene;
  let camera;
  let renderer;
  let controls;
  let currentModel = null;
  let wireframeOn = false;
  let autoRotate = false;
  let initialCameraPosition = new THREE.Vector3(3, 2, 5);
  let initialTarget = new THREE.Vector3(0, 0, 0);
  let annotationGroup = new THREE.Group();
  let raycaster = new THREE.Raycaster();
  let pointer = new THREE.Vector2();
  let selectedAnnotationId = null;
  const markerById = {};
  const labelEls = [];
  let nameTagEl = null;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function setLoadingMessage(message, showSpinner) {
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

  function showToast(message, kind) {
    let box = document.getElementById("viewer-toast");
    if (!box) {
      box = document.createElement("div");
      box.id = "viewer-toast";
      box.className = "viewer-messages";
      const sidebar = document.getElementById("sidebar");
      if (sidebar) {
        sidebar.insertBefore(box, sidebar.children[2] || null);
      }
    }
    box.innerHTML =
      '<div class="viewer-alert viewer-alert-' +
      (kind || "info") +
      '">' +
      escapeHtml(message) +
      "</div>";
  }

  function updateCompletionUI(completed) {
    if (completionBadgeEl) {
      completionBadgeEl.hidden = !completed;
    }
    if (!progressActionsEl || !config.isAuthenticated) return;

    if (completed) {
      progressActionsEl.innerHTML =
        '<button type="button" class="control-btn btn-secondary" data-progress-action="uncomplete">Mark Incomplete</button>';
    } else {
      progressActionsEl.innerHTML =
        '<button type="button" class="control-btn btn-success" data-progress-action="complete">Mark Complete</button>';
    }
  }

  function renderHotspotList(annotations) {
    if (!hotspotListEl) return;
    if (!annotations.length) {
      hotspotListEl.innerHTML = "<p class=\"info-box\" style=\"margin:0\">No hotspots for this lesson.</p>";
      return;
    }
    hotspotListEl.innerHTML = annotations
      .map(function (annotation, index) {
        return (
          '<li><button type="button" class="hotspot-list-item" data-annotation-id="' +
          annotation.id +
          '">' +
          (index + 1) +
          ". " +
          escapeHtml(annotation.title || "Hotspot") +
          (annotation.description
            ? "<span>" + escapeHtml(annotation.description) + "</span>"
            : "") +
          "</button></li>"
        );
      })
      .join("");
    bindHotspotList();
  }

  async function fetchLesson() {
    setLoadingMessage("Loading lesson from API...", true);
    const response = await fetch(config.lessonApiUrl, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!response.ok) {
      throw new Error("API request failed (" + response.status + ")");
    }
    return response.json();
  }

  async function markProgress(action) {
    const response = await fetch(config.completeApiUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ action: action }),
    });
    if (response.status === 403) {
      throw new Error("Please log in to track progress.");
    }
    if (!response.ok) {
      throw new Error("Could not update progress.");
    }
    return response.json();
  }

  function initScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const width = viewerEl.clientWidth;
    const height = viewerEl.clientHeight;

    camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 2000);
    camera.position.copy(initialCameraPosition);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.outputEncoding = THREE.sRGBEncoding;
    viewerEl.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.copy(initialTarget);
    controls.autoRotate = false;
    controls.autoRotateSpeed = 1.2;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 0.85));

    const key = new THREE.DirectionalLight(0xffffff, 0.9);
    key.position.set(5, 8, 4);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xa5b4fc, 0.35);
    fill.position.set(-4, 2, -3);
    scene.add(fill);

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("resize", onResize);
    animate();
  }

  function startViewer() {
    if (MODEL_URL) {
      setLoadingMessage("Loading 3D Model...", true);
      loadModel(MODEL_URL);
    } else {
      setLoadingMessage(
        "No 3D model uploaded yet. Showing a placeholder so you can test controls and hotspots.",
        false
      );
      addPlaceholderModel();
      fitCameraToObject(currentModel);
      createAnnotationMarkers();
      window.setTimeout(hideLoading, 700);
    }
  }

  function applyModelOrientation(root) {
    const deg = THREE.MathUtils.degToRad;
    root.rotation.set(
      deg(Number(MODEL_ORIENTATION.x) || 0),
      deg(Number(MODEL_ORIENTATION.y) || 0),
      deg(Number(MODEL_ORIENTATION.z) || 0)
    );
  }

  function mountModel(object3d) {
    if (currentModel) {
      scene.remove(currentModel);
    }
    // Keep hotspots parented to the oriented root so they follow rotation edits.
    if (annotationGroup.parent) {
      annotationGroup.parent.remove(annotationGroup);
    }
    const root = new THREE.Group();
    root.add(object3d);
    root.add(annotationGroup);
    applyModelOrientation(root);
    scene.add(root);
    currentModel = root;
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
    mountModel(group);
  }

  function loadModel(url) {
    const loader = new THREE.GLTFLoader();
    loader.load(
      url,
      function (gltf) {
        mountModel(gltf.scene);
        fitCameraToObject(currentModel);
        createAnnotationMarkers();
        hideLoading();
      },
      undefined,
      function (error) {
        console.error("Failed to load model:", error);
        setLoadingMessage(
          "Could not load this 3D model. Check that the file is a valid .glb / .gltf.",
          false
        );
        addPlaceholderModel();
        fitCameraToObject(currentModel);
        createAnnotationMarkers();
      }
    );
  }

  function fitCameraToObject(object3d) {
    if (!object3d) return;

    const box = new THREE.Box3().setFromObject(object3d);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const fitDist = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360));
    baseFitDistance = fitDist * 1.6;

    const distanceFactor = Math.max(Number(CAMERA_ZOOM.distance) || 1, 0.05);
    let minFactor = Math.max(Number(CAMERA_ZOOM.min) || 0.25, 0.05);
    let maxFactor = Math.max(Number(CAMERA_ZOOM.max) || 6, 0.1);
    if (minFactor > maxFactor) {
      const swap = minFactor;
      minFactor = maxFactor;
      maxFactor = swap;
    }
    const clampedDistance = Math.min(
      Math.max(distanceFactor, minFactor),
      maxFactor
    );
    const distance = baseFitDistance * clampedDistance;

    initialTarget.copy(center);
    const dir = new THREE.Vector3(0.55, 0.35, 1).normalize();
    initialCameraPosition
      .copy(center)
      .add(dir.multiplyScalar(distance));

    camera.near = Math.max(distance / 100, 0.01);
    camera.far = Math.max(distance * 100, 100);
    camera.updateProjectionMatrix();
    camera.position.copy(initialCameraPosition);
    controls.target.copy(initialTarget);
    controls.minDistance = baseFitDistance * minFactor;
    controls.maxDistance = baseFitDistance * maxFactor;
    controls.update();
  }

  function ensureNameTag() {
    if (nameTagEl) return nameTagEl;
    nameTagEl = document.createElement("div");
    nameTagEl.className = "hotspot-name-tag";
    viewerEl.appendChild(nameTagEl);
    return nameTagEl;
  }

  function createAnnotationMarkers() {
    while (annotationGroup.children.length) {
      annotationGroup.remove(annotationGroup.children[0]);
    }
    labelEls.forEach(function (el) {
      el.remove();
    });
    labelEls.length = 0;
    if (nameTagEl) {
      nameTagEl.classList.remove("is-visible");
    }
    Object.keys(markerById).forEach(function (key) {
      delete markerById[key];
    });

    // Hotspots live in the oriented model root so they rotate with it.
    if (currentModel && annotationGroup.parent !== currentModel) {
      currentModel.add(annotationGroup);
    }

    if (!ANNOTATIONS.length) return;

    const scale = estimateMarkerScale();
    ANNOTATIONS.forEach(function (annotation, index) {
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
      marker.userData.annotationId = annotation.id;
      annotationGroup.add(marker);
      markerById[annotation.id] = marker;

      const label = document.createElement("button");
      label.type = "button";
      label.className = "hotspot-label";
      label.textContent = String(index + 1);
      label.dataset.annotationId = String(annotation.id);
      label.dataset.index = String(index + 1);
      label.dataset.title = annotation.title || "Hotspot";
      label.setAttribute("aria-label", annotation.title || "Hotspot");
      label.addEventListener("click", function (event) {
        event.stopPropagation();
        focusAnnotation(annotation.id);
      });
      viewerEl.appendChild(label);
      labelEls.push(label);
    });
    ensureNameTag();
    if (currentModel) {
      currentModel.updateMatrixWorld(true);
    }
  }

  function estimateMarkerScale() {
    // Size markers from the model only. An absolute minimum (e.g. 0.04) makes
    // hotspots enormous on small/normalized GLBs.
    if (!currentModel) return 0.03;
    const size = new THREE.Box3()
      .setFromObject(currentModel)
      .getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    return maxDim * 0.008;
  }

  function updateLabels() {
    if (!labelEls.length) return;
    const width = viewerEl.clientWidth;
    const height = viewerEl.clientHeight;
    const nameTag = ensureNameTag();
    let activeScreen = null;
    let activeTitle = "";

    const worldPos = new THREE.Vector3();
    labelEls.forEach(function (label) {
      const id = Number(label.dataset.annotationId);
      const marker = markerById[id];
      if (!marker) return;

      // Markers are children of the rotated model — project world position.
      marker.getWorldPosition(worldPos);
      const pos = worldPos.clone().project(camera);
      const visible =
        pos.z > -1 &&
        pos.z < 1 &&
        pos.x >= -1.2 &&
        pos.x <= 1.2 &&
        pos.y >= -1.2 &&
        pos.y <= 1.2;

      if (!visible) {
        label.style.display = "none";
        return;
      }

      const x = (pos.x * 0.5 + 0.5) * width;
      const y = (-pos.y * 0.5 + 0.5) * height;
      const isActive = id === selectedAnnotationId;
      label.style.display = "flex";
      label.style.transform =
        "translate(-50%, -50%) translate(" + x + "px," + y + "px)";
      label.classList.toggle("is-active", isActive);
      label.textContent = label.dataset.index;
      if (isActive) {
        activeScreen = { x: x, y: y };
        activeTitle = label.dataset.title || "Hotspot";
      }
    });

    if (!activeScreen) {
      nameTag.classList.remove("is-visible");
      return;
    }

    // Place the name beside the marker so it does not cover the component.
    nameTag.textContent = activeTitle;
    nameTag.classList.add("is-visible");
    const gap = 20;
    let tagX = activeScreen.x + gap;
    const tagY = activeScreen.y;
    nameTag.style.transform =
      "translate(0, -50%) translate(" + tagX + "px," + tagY + "px)";
    const tagWidth = nameTag.offsetWidth || 140;
    if (tagX + tagWidth > width - 10) {
      tagX = activeScreen.x - gap;
      nameTag.style.transform =
        "translate(-100%, -50%) translate(" + tagX + "px," + tagY + "px)";
    }
  }

  function showHotspotDetail(annotation) {
    if (!hotspotDetailEl) return;
    if (!annotation) {
      hotspotDetailEl.hidden = true;
      hotspotDetailEl.innerHTML = "";
      return;
    }
    hotspotDetailEl.hidden = false;
    hotspotDetailEl.innerHTML =
      "<strong>" +
      escapeHtml(annotation.title || "Hotspot") +
      "</strong><p>" +
      escapeHtml(annotation.description || "") +
      "</p>";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function scrollHotspotTextIntoView(id) {
    const sidebar = document.getElementById("sidebar");
    const activeItem = document.querySelector(
      '.hotspot-list-item[data-annotation-id="' + id + '"]'
    );
    // Scroll to the matching list row (title + description). Fall back to detail.
    const target = activeItem || hotspotDetailEl;
    if (!sidebar || !target || target.hidden) return;

    // Scroll the sidebar overflow container directly.
    requestAnimationFrame(function () {
      const sidebarTop = sidebar.getBoundingClientRect().top;
      const targetTop = target.getBoundingClientRect().top;
      const nextTop = sidebar.scrollTop + (targetTop - sidebarTop) - 12;
      sidebar.scrollTo({
        top: Math.max(0, nextTop),
        behavior: "smooth",
      });
    });
  }

  function focusAnnotation(id) {
    const annotation = ANNOTATIONS.find(function (item) {
      return item.id === id;
    });
    const marker = markerById[id];
    if (!annotation || !marker) return;

    selectedAnnotationId = id;
    showHotspotDetail(annotation);

    document.querySelectorAll(".hotspot-list-item").forEach(function (item) {
      item.classList.toggle(
        "is-active",
        Number(item.dataset.annotationId) === id
      );
    });

    scrollHotspotTextIntoView(id);

    const endTarget = new THREE.Vector3();
    marker.getWorldPosition(endTarget);
    const offset = camera.position.clone().sub(controls.target).normalize();
    const distance = camera.position.distanceTo(controls.target) || 3;
    const endPos = endTarget.clone().add(offset.multiplyScalar(distance));
    animateCameraTo(endPos, endTarget, 450);
  }

  function animateCameraTo(endPos, endTarget, duration) {
    const startPos = camera.position.clone();
    const startTarget = controls.target.clone();
    const start = performance.now();

    function step(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = t * (2 - t);
      camera.position.lerpVectors(startPos, endPos, eased);
      controls.target.lerpVectors(startTarget, endTarget, eased);
      controls.update();
      if (t < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  function bindHotspotList() {
    document.querySelectorAll(".hotspot-list-item").forEach(function (item) {
      item.onclick = function () {
        focusAnnotation(Number(item.dataset.annotationId));
      };
    });
  }

  function onPointerDown(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(annotationGroup.children, false);
    if (hits.length) {
      focusAnnotation(hits[0].object.userData.annotationId);
    }
  }

  function setWireframe(root, enabled) {
    if (!root) return;
    root.traverse(function (child) {
      if (child.isMesh && child.material) {
        const materials = Array.isArray(child.material)
          ? child.material
          : [child.material];
        materials.forEach(function (material) {
          if (material && "wireframe" in material) {
            material.wireframe = enabled;
            material.needsUpdate = true;
          }
        });
      }
    });
  }

  function onResize() {
    if (!camera || !renderer) return;
    const width = viewerEl.clientWidth;
    const height = viewerEl.clientHeight;
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function animate() {
    requestAnimationFrame(animate);
    if (controls) {
      controls.autoRotate = autoRotate;
      controls.update();
    }
    updateLabels();
    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  window.resetCamera = function () {
    if (!camera || !controls) return;
    animateCameraTo(initialCameraPosition.clone(), initialTarget.clone(), 400);
  };

  window.toggleRotation = function () {
    autoRotate = !autoRotate;
    const btn = document.getElementById("btn-auto-rotate");
    if (btn) btn.classList.toggle("is-active", autoRotate);
  };

  window.toggleWireframe = function () {
    wireframeOn = !wireframeOn;
    setWireframe(currentModel, wireframeOn);
    const btn = document.getElementById("btn-wireframe");
    if (btn) btn.classList.toggle("is-active", wireframeOn);
  };

  window.focusAnnotation = focusAnnotation;

  if (progressActionsEl) {
    progressActionsEl.addEventListener("click", async function (event) {
      const button = event.target.closest("[data-progress-action]");
      if (!button) return;
      button.disabled = true;
      try {
        const data = await markProgress(button.dataset.progressAction);
        updateCompletionUI(Boolean(data.completed));
        showToast(data.message || "Progress updated.", "success");
      } catch (error) {
        showToast(error.message || "Could not update progress.", "info");
      } finally {
        button.disabled = false;
      }
    });
  }

  initScene();

  fetchLesson()
    .then(function (lesson) {
      MODEL_URL = lesson.model_url || "";
      MODEL_ORIENTATION = lesson.model_orientation || { x: 0, y: 0, z: 0 };
      CAMERA_ZOOM = lesson.camera_zoom || { distance: 1, min: 0.25, max: 6 };
      ANNOTATIONS = lesson.annotations || [];
      renderHotspotList(ANNOTATIONS);
      updateCompletionUI(Boolean(lesson.completed));
      startViewer();
    })
    .catch(function (error) {
      console.error(error);
      setLoadingMessage(
        "Could not load lesson API. Check /api/lessons/<id>/.",
        false
      );
    });
})();
