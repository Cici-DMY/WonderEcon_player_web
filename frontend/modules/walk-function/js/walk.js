/*
 * walk.js — 总入口
 * 给【人物ID】+【任务路线】即可触发行走 + 建筑虚化。
 *
 *   await EWMWalk.trigger("walk_1", { from: 1, to: 2 });
 *
 * 依赖（同目录，按顺序在 walk.js 之前引入）：
 *   matcher.js  routes.js  transparency.js  sizing.js
 *
 * 流程：
 *   1) matcher: personId + taskRoute -> routeFile
 *   2) routes:  载入 routeFile，沿点行走（每帧回调）
 *   3) transparency: 行走中把人物坐标喂给虚化判定，经过的建筑半透明
 *   4) sizing:  人物/光圈/标签尺寸对齐 player_world_city_ui.html
 */
(function (global) {
  "use strict";

  // 行走过程中默认叠加的虚化图层（transparency/*.json）。
  // 后续可按路线分组细化；这里先统一加载已有的。
  const _tBase = ((global.EWMWalkConfig && global.EWMWalkConfig.transparencyBasePath) || "transparency").replace(/\/+$/, "");
  const DEFAULT_TRANSPARENCY_FILES = [
    `${_tBase}/commercial_bank_0.json`,
    `${_tBase}/stadium1.json`,
    `${_tBase}/stadium2.json`,
    `${_tBase}/supermarket.json`,
    `${_tBase}/supermarket_green.json`,
    `${_tBase}/supermarket_red.json`,
    `${_tBase}/supermarket_white.json`,
    `${_tBase}/supermarket_yellow.json`,
    `${_tBase}/talent_market.json`,
    `${_tBase}/tree1.json`,
    `${_tBase}/tree2.json`,
    `${_tBase}/tree3.json`,
    `${_tBase}/tree4.json`,
    `${_tBase}/tree5.json`,
    `${_tBase}/tree6.json`,
    `${_tBase}/tree7.json`,
    `${_tBase}/wealth1_labor_house_01.json`,
    `${_tBase}/wealth1_labor_house_06.json`,
    `${_tBase}/wealth2_labor_house_04.json`,
    `${_tBase}/wealth3_labor_house_01.json`,
    `${_tBase}/wealth3_nonlabor_house_01.json`,
    `${_tBase}/wealth4_labor_house_10.json`
  ];

  function resolveAssetUrl(path) {
    if (/^(https?:)?\/\//.test(String(path)) || String(path).startsWith("data:")) return path;
    return new URL(path, document.baseURI).href;
  }

  function ensureAvatar(opts) {
    // 优先复用宿主已有头像；否则新建一个最简头像。
    let avatar = opts.avatarEl
      || document.querySelector(".player-avatar-on-map")
      || document.querySelector(".ewm-walk-avatar");
    if (!avatar) {
      avatar = document.createElement("div");
      avatar.className = "ewm-walk-avatar";
      const img = document.createElement("img");
      img.alt = "walker";
      if (opts.spriteSrc) img.src = opts.spriteSrc;
      avatar.appendChild(img);
      (opts.layer || document.body).appendChild(avatar);
    }
    return avatar;
  }

  function positionAvatar(avatar, x, y) {
    avatar.style.left = `${x}px`;
    avatar.style.top = `${y}px`;
  }

  let activeWalk = null; // { handle, transparency }

  /**
   * 触发行走。
   * @param personId  人物ID（matcher 用）
   * @param taskRoute { from, to } 或 { segment } 或 { taskId }
   * @param opts {
   *    layer: 建筑/场景层 DOM（行走与虚化都在它内部，默认自动找）
   *    avatarEl: 复用的头像 DOM
   *    transparencyFiles: 自定义本次虚化图层数组
   *    loop, speed, labelText, spriteSrc,
   *    onStep, onArrive
   * }
   * @returns 匹配结果（含 routeFile）；未匹配到则 applied=false。
   */
  async function trigger(personId, taskRoute, opts = {}) {
    if (!global.EWMMatcher || !global.EWMRoutes || !global.EWMTransparency) {
      throw new Error("[EWMWalk] 依赖未就绪：需先引入 matcher.js / routes.js / transparency.js");
    }

    // 0) 结束上一段行走
    stop();

    // 1) 匹配路线
    const match = global.EWMMatcher.matchRoute(personId, taskRoute);
    if (!match.applied) {
      console.warn("[EWMWalk] 未匹配到路线:", match.reason, match);
      return match;
    }

    const layer = opts.layer
      || document.querySelector("#scene-building-layer, .scene-building-layer")
      || document.body;

    // 2) 载入路线文件
    const routeUrl = resolveAssetUrl(match.routeFile);
    const route = await global.EWMRoutes.loadRouteFile(routeUrl);
    if (route.points.length < 2) {
      console.warn("[EWMWalk] 路线点不足:", match.routeFile);
      return { ...match, applied: false, reason: "路线点不足" };
    }

    // 3) 准备虚化图层
    const transparency = global.EWMTransparency.create({ sceneBuildingLayer: layer });
    const tFiles = (opts.transparencyFiles || DEFAULT_TRANSPARENCY_FILES)
      .map(f => resolveAssetUrl(f));
    await transparency.loadPolygonFiles(tFiles);

    // 4) 头像 + 尺寸
    const avatar = ensureAvatar({ ...opts, layer });
    if (global.EWMSizing) global.EWMSizing.applySizing(avatar, opts.labelText);

    // 5) 行走：每帧移动头像 + 喂虚化
    const rawMultiplier = Number(opts.speedMultiplier);
    const speedMultiplier = Number.isFinite(rawMultiplier) && rawMultiplier > 0 ? rawMultiplier : 1;
    const rawSpeed = Number(opts.speed);
    const baseSpeed = Number.isFinite(rawSpeed) && rawSpeed > 0 ? rawSpeed : global.EWMRoutes.PLAYER_SPEED;
    const readSpeedMultiplier = () => {
      const dynamicMultiplier = typeof opts.getSpeedMultiplier === "function"
        ? Number(opts.getSpeedMultiplier())
        : speedMultiplier;
      return Number.isFinite(dynamicMultiplier) && dynamicMultiplier > 0 ? dynamicMultiplier : 1;
    };
    const handle = global.EWMRoutes.walkRoute(route, {
      start: opts.start || route.points[0],
      loop: opts.loop != null ? opts.loop : route.loop,
      speed: baseSpeed * speedMultiplier,
      getSpeed: () => baseSpeed * readSpeedMultiplier(),
      onStep: ({ x, y, direction, moving }) => {
        positionAvatar(avatar, x, y);
        if (avatar.dataset) avatar.dataset.direction = direction;
        transparency.update(x, y);          // ← 行走中建筑虚化
        opts.onStep?.({ x, y, direction, moving });
      },
      onArrive: () => {
        transparency.clearAll();
        opts.onArrive?.(match);
      }
    });

    activeWalk = { handle, transparency };
    return { ...match, routeUrl };
  }

  /** 停止当前行走并清掉虚化。 */
  function stop() {
    if (activeWalk) {
      activeWalk.handle?.stop?.();
      activeWalk.transparency?.clearAll?.();
      activeWalk = null;
    }
  }

  global.EWMWalk = {
    trigger,
    stop,
    DEFAULT_TRANSPARENCY_FILES
  };
})(typeof window !== "undefined" ? window : globalThis);
