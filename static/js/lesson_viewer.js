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
  let ANNOTATIONS = [];

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

    scene.add(annotationGroup);
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

  function loadModel(url) {
    const loader = new THREE.GLTFLoader();
    loader.load(
      url,
      function (gltf) {
        if (currentModel) scene.remove(currentModel);
        currentModel = gltf.scene;
        scene.add(currentModel);
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
    const distance = fitDist * 1.6;

    initialTarget.copy(center);
    initialCameraPosition.set(
      center.x + distance * 0.55,
      center.y + distance * 0.35,
      center.z + distance
    );

    camera.near = Math.max(distance / 100, 0.01);
    camera.far = Math.max(distance * 100, 100);
    camera.updateProjectionMatrix();
    camera.position.copy(initialCameraPosition);
    controls.target.copy(initialTarget);
    controls.update();
  }

  function createAnnotationMarkers() {
    while (annotationGroup.children.length) {
      annotationGroup.remove(annotationGroup.children[0]);
    }
    labelEls.forEach(function (el) {
      el.remove();
    });
    labelEls.length = 0;
    Object.keys(markerById).forEach(function (key) {
      delete markerById[key];
    });

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
      label.setAttribute("aria-label", annotation.title || "Hotspot");
      label.addEventListener("click", function (event) {
        event.stopPropagation();
        focusAnnotation(annotation.id);
      });
      viewerEl.appendChild(label);
      labelEls.push(label);
    });
  }

  function estimateMarkerScale() {
    if (!currentModel) return 0.08;
    const size = new THREE.Box3()
      .setFromObject(currentModel)
      .getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    return Math.max(maxDim * 0.025, 0.04);
  }

  function updateLabels() {
    if (!labelEls.length) return;
    const width = viewerEl.clientWidth;
    const height = viewerEl.clientHeight;

    labelEls.forEach(function (label) {
      const id = Number(label.dataset.annotationId);
      const marker = markerById[id];
      if (!marker) return;

      const pos = marker.position.clone().project(camera);
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
      label.style.display = "flex";
      label.style.transform =
        "translate(-50%, -50%) translate(" + x + "px," + y + "px)";
      label.classList.toggle("is-active", id === selectedAnnotationId);
    });
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

    const endTarget = marker.position.clone();
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
