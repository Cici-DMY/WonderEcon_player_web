/*
 * routes.js — Walking route loading and movement along routes
 * Extracted movePlayerAlongRoute / directionFromDelta /
 * normalizeRoutePoints / PLAYER_SPEED from player_world_city_ui.html, refactored into standalone module.
 *
 * Calls host each walking frame: onStep({x,y,direction,moving}) — host uses this to move avatar + switch animation,
 * meanwhile this module feeds coordinates to transparency.update for building fade during walk.
 */
(function (global) {
  "use strict";

  const PLAYER_SPEED = 90; // px/s, from player_world_city_ui.html

  // -- Isometric 4-direction detection, extracted as-is --
  function directionFromDelta(dx, dy) {
    const u = dx - dy;
    const v = dx + dy;
    if (Math.abs(u) >= Math.abs(v)) return u >= 0 ? "front" : "back";
    return v >= 0 ? "right" : "left";
  }

  // -- Normalize route points, extracted from host normalizeRoutePoints --
  function normalizeRoutePoints(route) {
    if (!Array.isArray(route)) return [];
    return route
      .map(point => {
        if (Array.isArray(point)) return { x: Number(point[0]), y: Number(point[1]) };
        return { x: Number(point?.x), y: Number(point?.y) };
      })
      .filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
  }

  /** Load a routes/*.json, returns { points, loop, sceneSize }. */
  async function loadRouteFile(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Route load failed: HTTP ${res.status} (${url})`);
    const data = await res.json();
    return {
      points: normalizeRoutePoints(data.points),
      loop: Boolean(data.loop),
      sceneSize: data.sceneSize || { width: 6400, height: 3600 },
      raw: data
    };
  }

  /**
   * Move along route. Extracted from host movePlayerAlongRoute rAF progression logic.
   * @param route   Point array or {points,loop}
   * @param opts.start   Start point {x,y}, defaults to first route point
   * @param opts.loop    Whether to loop
   * @param opts.speed   Speed (px/s), defaults to PLAYER_SPEED
   * @param opts.onStep  function({x,y,direction,moving}) per-frame callback (move avatar/switch animation/fade)
   * @param opts.onArrive function() arrival callback (non-loop)
   * @returns { stop() } handle
   */
  function walkRoute(route, opts = {}) {
    const points = normalizeRoutePoints(route.points || route);
    const loop = opts.loop != null ? Boolean(opts.loop) : Boolean(route.loop);
    const speed = opts.speed || PLAYER_SPEED;
    const getSpeed = typeof opts.getSpeed === "function"
      ? () => {
          const dynamicSpeed = Number(opts.getSpeed());
          return Number.isFinite(dynamicSpeed) && dynamicSpeed > 0 ? dynamicSpeed : speed;
        }
      : () => speed;
    const onStep = typeof opts.onStep === "function" ? opts.onStep : () => {};
    const onArrive = typeof opts.onArrive === "function" ? opts.onArrive : () => {};

    if (points.length < 2) { onArrive(); return { stop() {} }; }

    const state = {
      x: opts.start?.x ?? points[0].x,
      y: opts.start?.y ?? points[0].y,
      direction: "front",
      moving: true
    };
    let segmentIndex = 1;
    let previousTimestamp = 0;
    let raf = 0;
    let stopped = false;

    const step = timestamp => {
      if (stopped) return;
      if (!previousTimestamp) previousTimestamp = timestamp;
      const dt = Math.min((timestamp - previousTimestamp) / 1000, 0.05);
      previousTimestamp = timestamp;

      const target = points[segmentIndex];
      const dx = target.x - state.x;
      const dy = target.y - state.y;
      const remaining = Math.hypot(dx, dy);

      if (remaining <= 2) {
        state.x = target.x;
        state.y = target.y;
        segmentIndex += 1;
        if (segmentIndex >= points.length) {
          if (loop) {
            segmentIndex = points.length > 1 ? 1 : 0;
          } else {
            state.moving = false;
            onStep({ ...state });
            onArrive();
            return;
          }
        }
      } else {
        state.direction = directionFromDelta(dx, dy);
        const travel = Math.min(remaining, getSpeed() * dt);
        state.x += dx / remaining * travel;
        state.y += dy / remaining * travel;
      }
      onStep({ ...state });
      raf = requestAnimationFrame(step);
    };

    onStep({ ...state });
    raf = requestAnimationFrame(step);

    return {
      stop() {
        stopped = true;
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
      }
    };
  }

  global.EWMRoutes = {
    PLAYER_SPEED,
    directionFromDelta,
    normalizeRoutePoints,
    loadRouteFile,
    walkRoute
  };
})(typeof window !== "undefined" ? window : globalThis);
