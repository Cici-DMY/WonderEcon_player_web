/*
 * transparency.js — 建筑遮挡虚化逻辑
 * 直接从 player_world_city_ui.html 抽取（点在多边形/身体盒判定/.faded-behind 应用），
 * 改造成可加载 walk-function/transparency/*.json(ewm-occlusion-polygons 格式) 的独立模块。
 *
 * 用法：
 *   const t = EWMTransparency.create({ sceneBuildingLayer, worldWidth, worldHeight });
 *   await t.loadPolygonFiles(["transparency/stadium2.json"]);   // 载入虚化图层
 *   t.update(playerX, playerY);                                // 行走每帧调用，命中即虚化
 *
 * 若宿主页 player_world_city_ui.html 已有同名逻辑，本模块可与之并存：
 * 它只读 occlusionPolygons 并切换建筑 .faded-behind 类。
 */
(function (global) {
  "use strict";

  // —— 人物身体盒常量（取自 player_world_city_ui.html）——
  const PLAYER_BODY_HALF_W = 14;   // 人物身体半宽 (px in scene)
  const PLAYER_BODY_TOP_DY = 38;   // 头顶到脚底
  const PLAYER_BODY_BOTTOM_DY = 2; // 脚底容差
  const PLAYER_AVATAR_Z = 50000;
  const OCCLUDER_Z = 50001;

  // —— 点在多边形内 (射线法)，原样抽取 ——
  function pointInPolygon(x, y, pts) {
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const xi = pts[i].x, yi = pts[i].y;
      const xj = pts[j].x, yj = pts[j].y;
      const intersect = ((yi > y) !== (yj > y)) &&
        (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  // —— 人物身体盒命中多边形：四角 + 中心点任一落入即重叠，原样抽取 ——
  function playerBoxHitsPolygon(pLeft, pRight, pTop, pBottom, pts) {
    return (
      pointInPolygon(pLeft,  pTop,    pts) ||
      pointInPolygon(pRight, pTop,    pts) ||
      pointInPolygon(pLeft,  pBottom, pts) ||
      pointInPolygon(pRight, pBottom, pts) ||
      pointInPolygon((pLeft + pRight) / 2, (pTop + pBottom) / 2, pts)
    );
  }

  // —— 切换某建筑 DOM 的虚化态：z-index 抬到人物之上 + .faded-behind，原样抽取 ——
  function applyFadeState(el, shouldFade) {
    if (!el) return;
    const wasBehind = el.classList.contains("faded-behind");
    if (shouldFade && !wasBehind) {
      if (el.dataset.origZ === undefined) {
        el.dataset.origZ = el.style.zIndex || "";
      }
      el.style.zIndex = String(OCCLUDER_Z);
      el.classList.add("faded-behind");
    } else if (!shouldFade && wasBehind) {
      el.style.zIndex = el.dataset.origZ || "";
      delete el.dataset.origZ;
      el.classList.remove("faded-behind");
    }
  }

  /**
   * 按 polygon 的 key 找回对应建筑 DOM。抽取自宿主 findBuildingElByPolygonKey：
   * 搜全部 .scene-item（不限 .building），命中后补上 building 类。
   */
  function findBuildingElByPolygonKey(sceneBuildingLayer, key) {
    if (!key || !sceneBuildingLayer) return null;
    const all = sceneBuildingLayer.querySelectorAll(".scene-item, .item");
    for (let i = 0; i < all.length; i++) {
      const el = all[i];
      if (
        el.dataset.resolvedEntityId === key ||
        el.dataset.entityId === key ||
        el.dataset.buildingId === key ||
        el.dataset.layoutKey === key ||
        el.id === key ||
        el.dataset.name === key
      ) {
        if (!el.classList.contains("building") && !el.classList.contains("foundation")) {
          el.classList.add("building");
        }
        return el;
      }
    }
    return null;
  }

  // 注入 .faded-behind 样式（若宿主页没定义，保证虚化可见）。
  function ensureFadeStyle() {
    if (document.getElementById("ewm-transparency-style")) return;
    const style = document.createElement("style");
    style.id = "ewm-transparency-style";
    style.textContent =
      ".scene-item.faded-behind,.item.faded-behind{opacity:.6 !important;transition:opacity .25s ease;}";
    document.head.appendChild(style);
  }

  /** 兼容两类透明区 JSON：
   *  1) { polygons: { buildingKey: [{x,y}, ...] } }
   *  2) { buildingId: "buildingKey", polygon: [{x,y}, ...] }
   */
  function normalizeTransparencyPolygons(data) {
    if (!data || typeof data !== "object") return null;
    if (data.polygons && typeof data.polygons === "object") return data.polygons;
    if (data.buildingId && Array.isArray(data.polygon)) {
      return { [data.buildingId]: data.polygon };
    }
    return null;
  }

  /**
   * 创建一个虚化控制器。
   * opts.sceneBuildingLayer: 建筑层 DOM（必填，行走/虚化都在它内部）
   */
  function create(opts = {}) {
    const sceneBuildingLayer = opts.sceneBuildingLayer
      || document.querySelector("#scene-building-layer, .scene-building-layer")
      || document.body;

    ensureFadeStyle();

    // 当前生效的遮挡多边形集合 { key: [{x,y}, ...] }
    let occlusionPolygons = {};
    const fadedKeys = new Set();

    /** 直接设置多边形集合（ewm-occlusion-polygons.polygons 结构）。 */
    function setPolygons(polygons) {
      occlusionPolygons = polygons && typeof polygons === "object" ? polygons : {};
      return occlusionPolygons;
    }

    /** 合并更多多边形（多个 transparency 文件叠加时用）。 */
    function mergePolygons(polygons) {
      if (polygons && typeof polygons === "object") {
        Object.assign(occlusionPolygons, polygons);
      }
      return occlusionPolygons;
    }

    /** 载入一个或多个 transparency/*.json 文件并合并其 polygons。 */
    async function loadPolygonFiles(urls) {
      const list = Array.isArray(urls) ? urls : [urls];
      for (const url of list) {
        try {
          const res = await fetch(url);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const polygons = normalizeTransparencyPolygons(data);
          if (polygons) mergePolygons(polygons);
          else console.warn("[transparency] 文件无可用遮挡多边形:", url);
        } catch (err) {
          console.warn("[transparency] 载入失败:", url, err);
        }
      }
      return occlusionPolygons;
    }

    /**
     * 每帧/每次移动调用：传入人物场景坐标，命中方框的建筑虚化、未命中恢复。
     * 抽取自宿主 updateBuildingsBehindPlayer，仅保留方框判定那一趟。
     */
    function update(px, py) {
      if (!sceneBuildingLayer) return;

      const pLeft   = px - PLAYER_BODY_HALF_W;
      const pRight  = px + PLAYER_BODY_HALF_W;
      const pTop    = py - PLAYER_BODY_TOP_DY;
      const pBottom = py + PLAYER_BODY_BOTTOM_DY;

      const polyKeys = Object.keys(occlusionPolygons);
      for (let i = 0; i < polyKeys.length; i++) {
        const key = polyKeys[i];
        const pts = occlusionPolygons[key];
        if (!Array.isArray(pts) || pts.length < 3) continue;
        const el = findBuildingElByPolygonKey(sceneBuildingLayer, key);
        if (!el) continue;
        const shouldFade = playerBoxHitsPolygon(pLeft, pRight, pTop, pBottom, pts);
        applyFadeState(el, shouldFade);
        if (shouldFade) fadedKeys.add(key); else fadedKeys.delete(key);
      }
    }

    /** 清掉所有虚化态（行走结束/切换路线时调用）。 */
    function clearAll() {
      fadedKeys.forEach(key => {
        const el = findBuildingElByPolygonKey(sceneBuildingLayer, key);
        applyFadeState(el, false);
      });
      fadedKeys.clear();
    }

    return {
      setPolygons,
      mergePolygons,
      loadPolygonFiles,
      update,
      clearAll,
      getPolygons: () => occlusionPolygons
    };
  }

  global.EWMTransparency = {
    create,
    // 同时导出底层纯函数，便于复用/测试
    pointInPolygon,
    playerBoxHitsPolygon,
    applyFadeState,
    findBuildingElByPolygonKey,
    normalizeTransparencyPolygons,
    constants: { PLAYER_BODY_HALF_W, PLAYER_BODY_TOP_DY, PLAYER_BODY_BOTTOM_DY, PLAYER_AVATAR_Z, OCCLUDER_Z }
  };
})(typeof window !== "undefined" ? window : globalThis);
