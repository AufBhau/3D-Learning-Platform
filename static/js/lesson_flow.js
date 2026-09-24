(function () {
  "use strict";

  const track = document.getElementById("flow-track");
  const tips = document.getElementById("flow-tips");
  const tipsCard = document.getElementById("flow-tips-card");
  const titleEl = document.getElementById("flow-tips-title");
  const hotspotRow = document.getElementById("flow-tips-hotspots-row");
  const clickRow = document.getElementById("flow-tips-click-row");
  const hotspotLabel = document.getElementById("flow-tips-hotspot-label");
  const hotspotText = document.getElementById("flow-tips-hotspot-text");

  if (!track || !tipsCard || !titleEl) {
    return;
  }

  function alignTipsToItem(item) {
    if (!tips || !item || window.matchMedia("(max-width: 1020px)").matches) {
      tipsCard.style.transform = "";
      return;
    }

    const tipsRect = tips.getBoundingClientRect();
    const itemRect = item.getBoundingClientRect();
    const offset = itemRect.top - tipsRect.top;
    const clamped = Math.max(0, offset);
    tipsCard.style.transform = "translateY(" + clamped + "px)";
  }

  function selectLesson(item) {
    track.querySelectorAll(".flow-item").forEach(function (el) {
      const active = el === item;
      el.classList.toggle("is-active", active);
      const card = el.querySelector(".flow-card");
      if (card) {
        card.setAttribute("aria-pressed", active ? "true" : "false");
      }
    });

    titleEl.textContent = item.dataset.title || "Lesson";

    const count = Number(item.dataset.hotspotCount || 0);
    const hotspots = item.dataset.hotspots || "";

    if (clickRow) {
      clickRow.hidden = count === 0;
    }

    if (hotspotRow && hotspotLabel && hotspotText) {
      if (count > 0) {
        hotspotRow.hidden = false;
        hotspotLabel.textContent =
          count + " hotspot" + (count === 1 ? "" : "s");
        hotspotText.textContent = hotspots;
      } else {
        hotspotRow.hidden = true;
        hotspotLabel.textContent = "";
        hotspotText.textContent = "";
      }
    }

    alignTipsToItem(item);
  }

  track.addEventListener("click", function (event) {
    if (event.target.closest("[data-open-viewer]")) {
      return;
    }

    const card = event.target.closest("[data-select-lesson]");
    if (!card) return;

    event.preventDefault();
    const item = card.closest(".flow-item");
    if (!item) return;
    selectLesson(item);
  });

  track.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    if (event.target.closest("[data-open-viewer]")) return;
    const card = event.target.closest("[data-select-lesson]");
    if (!card) return;
    event.preventDefault();
    const item = card.closest(".flow-item");
    if (item) selectLesson(item);
  });

  const initial =
    track.querySelector(".flow-item.is-active") ||
    track.querySelector(".flow-item");
  if (initial) {
    selectLesson(initial);
  }

  window.addEventListener("resize", function () {
    const active = track.querySelector(".flow-item.is-active");
    if (active) alignTipsToItem(active);
  });
})();
