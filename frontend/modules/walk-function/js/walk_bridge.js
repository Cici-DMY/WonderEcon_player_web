(function(global) {
  'use strict';

  var WALK_ANIM_FRAME_MS = 90;

  var TASK_ROUTE_SEGMENTS_LABOR_LOW = [
    { taskId: "loan_decision", segment: "1-2", type: "task" },
    { taskId: "labor_decision", segment: "2-3", type: "task" },
    { taskId: "labor_decision", segment: "3-4", type: "labor_enterprise" },
    { taskId: "consumption_decision", segment: "4-5", type: "task" },
    { taskId: "stock_decision", segment: "5-6", type: "task" },
    { taskId: "deposit_decision", segment: "6-7", type: "task" }
  ];

  var TASK_ROUTE_SEGMENTS_LABOR_HIGH = [
    { taskId: "labor_decision", segment: "1-2", type: "task" },
    { taskId: "labor_decision", segment: "2-3", type: "labor_enterprise" },
    { taskId: "consumption_decision", segment: "3-4", type: "task" },
    { taskId: "stock_decision", segment: "4-5", type: "task" },
    { taskId: "deposit_decision", segment: "5-6", type: "task" }
  ];

  var TASK_ROUTE_SEGMENTS_NONLABOR = [
    { taskId: "consumption_decision", segment: "1-2", type: "task" },
    { taskId: "stock_decision", segment: "2-3", type: "task" },
    { taskId: "deposit_decision", segment: "3-4", type: "task" }
  ];

  var config = {
    personId: "walk_1",
    wealthTier: 3,
    labor: true,
    speedMultiplier: 3,
    sceneEl: null,
    viewportEl: null,
    onArrive: null,
    onLaborEnterpriseArrive: null
  };

  var walkAvatar = null;
  var spriteImg = null;
  var spriteFrames = {};
  var currentDirection = 'front';
  var currentFrameIndex = 0;
  var lastFrameTime = 0;
  var isWalking = false;
  var panning = false;

  function getSpritePath(personId) {
    var basePath = (global.EWMWalkConfig && global.EWMWalkConfig.spriteBasePath) || 'modules/person';
    return basePath + '/' + personId;
  }

  function preloadFrames(personId) {
    var base = getSpritePath(personId);
    var directions = ['front', 'back', 'left', 'right'];
    spriteFrames = {};
    directions.forEach(function(dir) {
      spriteFrames[dir] = [];
      for (var i = 1; i <= 12; i++) {
        var img = new Image();
        img.src = base + '/walk_' + dir + '_' + String(i).padStart(2, '0') + '.png';
        spriteFrames[dir].push(img);
      }
    });
  }

  function animateSprite(direction, moving, timestamp) {
    if (!spriteImg || !moving) return;
    if (direction !== currentDirection) {
      currentDirection = direction;
      currentFrameIndex = 0;
      lastFrameTime = timestamp;
    }
    if (timestamp - lastFrameTime >= WALK_ANIM_FRAME_MS) {
      currentFrameIndex = (currentFrameIndex + 1) % 12;
      lastFrameTime = timestamp;
    }
    var frames = spriteFrames[currentDirection];
    if (frames && frames[currentFrameIndex]) {
      spriteImg.src = frames[currentFrameIndex].src;
    }
  }

  var WALK_CAMERA_SCALE = 0.85;
  var WALK_CAMERA_SMOOTH_FACTOR = 0.25;
  var cameraInitialized = false;

  function focusCamera(x, y) {
    var viewport = config.viewportEl;
    var scene = config.sceneEl;
    if (!viewport || !scene) return;
    if (panning) return;

    var rect = viewport.getBoundingClientRect();
    var vw = rect.width;
    var vh = rect.height;

    var minScale = Math.max(vw / 6400, vh / 3600) * 1.01;
    var targetScale = Math.max(minScale, Math.min(2.4, WALK_CAMERA_SCALE));

    var currentTransform = scene.style.transform || '';
    var scaleMatch = currentTransform.match(/scale\(([^)]+)\)/);
    var currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : targetScale;

    var translateMatch = currentTransform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)/);
    var currentPanX = translateMatch ? parseFloat(translateMatch[1]) : 0;
    var currentPanY = translateMatch ? parseFloat(translateMatch[2]) : 0;

    var useScale = cameraInitialized ? currentScale + (targetScale - currentScale) * WALK_CAMERA_SMOOTH_FACTOR : targetScale;

    var targetPanX = (vw / 2) - (x * useScale);
    var targetPanY = (vh / 2) - (y * useScale);

    var sw = 6400 * useScale;
    var sh = 3600 * useScale;
    if (sw > vw) { targetPanX = Math.min(0, Math.max(vw - sw, targetPanX)); }
    else { targetPanX = (vw - sw) / 2; }
    if (sh > vh) { targetPanY = Math.min(0, Math.max(vh - sh, targetPanY)); }
    else { targetPanY = (vh - sh) / 2; }

    var finalPanX, finalPanY;
    if (cameraInitialized) {
      finalPanX = currentPanX + (targetPanX - currentPanX) * WALK_CAMERA_SMOOTH_FACTOR;
      finalPanY = currentPanY + (targetPanY - currentPanY) * WALK_CAMERA_SMOOTH_FACTOR;
    } else {
      finalPanX = targetPanX;
      finalPanY = targetPanY;
      cameraInitialized = true;
    }

    scene.style.transform = 'translate(' + finalPanX + 'px, ' + finalPanY + 'px) scale(' + useScale + ')';
  }

  function ensureAvatar() {
    if (walkAvatar) return walkAvatar;
    var scene = config.sceneEl;
    if (!scene) return null;

    walkAvatar = document.createElement('div');
    walkAvatar.className = 'ewm-walk-avatar';
    spriteImg = document.createElement('img');
    spriteImg.alt = 'player';
    var base = getSpritePath(config.personId);
    spriteImg.src = base + '/walk_front_01.png';
    walkAvatar.appendChild(spriteImg);
    scene.appendChild(walkAvatar);

    if (global.EWMSizing) {
      global.EWMSizing.applySizing(walkAvatar, 'player');
    }
    return walkAvatar;
  }

  function removeAvatar() {
    if (walkAvatar && walkAvatar.parentNode) {
      walkAvatar.parentNode.removeChild(walkAvatar);
    }
    walkAvatar = null;
    spriteImg = null;
  }

  function buildWalkSequence() {
    if (!config.labor) return TASK_ROUTE_SEGMENTS_NONLABOR;
    if (config.wealthTier <= 2) return TASK_ROUTE_SEGMENTS_LABOR_LOW;
    return TASK_ROUTE_SEGMENTS_LABOR_HIGH;
  }

  function resolveRouteEntry(taskId) {
    var sequence = buildWalkSequence();
    var entry = sequence.find(function(e) { return e.taskId === taskId && e.type === 'task'; });
    return entry || null;
  }

  function resolveLaborEnterpriseEntry() {
    var sequence = buildWalkSequence();
    return sequence.find(function(e) { return e.type === 'labor_enterprise'; }) || null;
  }

  function triggerWalk(step, callback) {
    if (!step || !step.id) return;
    if (!global.EWMWalk) {
      console.error('[EWMWalkBridge] EWMWalk not loaded');
      return;
    }

    var entry = resolveRouteEntry(step.id);
    if (!entry) {
      console.warn('[EWMWalkBridge] no route entry for task:', step.id);
      return;
    }

    isWalking = true;
    ensureAvatar();

    var startTime = performance.now();
    global.EWMWalk.trigger(config.personId, { segment: entry.segment }, {
      layer: config.sceneEl,
      avatarEl: walkAvatar,
      speedMultiplier: config.speedMultiplier,
      getSpeedMultiplier: function() { return config.speedMultiplier; },
      onStep: function(info) {
        animateSprite(info.direction, info.moving, performance.now() - startTime);
        focusCamera(info.x, info.y);
      },
      onArrive: function(match) {
        isWalking = false;
        cameraInitialized = false;
        if (typeof callback === 'function') {
          callback(step, match);
        }
        if (typeof config.onArrive === 'function') {
          config.onArrive(step, match);
        }
      }
    });
  }

  function triggerLaborEnterpriseWalk(callback) {
    if (!global.EWMWalk) {
      console.error('[EWMWalkBridge] EWMWalk not loaded');
      return;
    }

    var entry = resolveLaborEnterpriseEntry();
    if (!entry) {
      console.warn('[EWMWalkBridge] no labor enterprise route entry');
      return;
    }

    isWalking = true;
    ensureAvatar();

    var startTime = performance.now();
    global.EWMWalk.trigger(config.personId, { segment: entry.segment }, {
      layer: config.sceneEl,
      avatarEl: walkAvatar,
      speedMultiplier: config.speedMultiplier,
      getSpeedMultiplier: function() { return config.speedMultiplier; },
      onStep: function(info) {
        animateSprite(info.direction, info.moving, performance.now() - startTime);
        focusCamera(info.x, info.y);
      },
      onArrive: function(match) {
        isWalking = false;
        cameraInitialized = false;
        if (typeof callback === 'function') {
          callback(match);
        }
        if (typeof config.onLaborEnterpriseArrive === 'function') {
          config.onLaborEnterpriseArrive(match);
        }
      }
    });
  }

  function init(options) {
    options = options || {};
    config.personId = options.personId || 'walk_1';
    config.wealthTier = options.wealthTier || 3;
    config.labor = options.labor != null ? options.labor : true;
    config.speedMultiplier = options.speedMultiplier || 3;
    config.sceneEl = options.sceneEl || document.getElementById('scene');
    config.viewportEl = options.viewportEl || document.getElementById('viewport');
    config.onArrive = options.onArrive || null;
    config.onLaborEnterpriseArrive = options.onLaborEnterpriseArrive || null;

    EWMMatcher.PERSON_ATTRIBUTE_MAP[config.personId] = {
      wealthTier: config.wealthTier,
      labor: config.labor
    };

    preloadFrames(config.personId);

    var vp = config.viewportEl;
    if (vp) {
      vp.addEventListener('mousedown', function() { panning = true; });
      document.addEventListener('mouseup', function() { panning = false; });
    }
  }

  function setSpeed(multiplier) {
    config.speedMultiplier = multiplier;
  }

  function stop() {
    if (global.EWMWalk) global.EWMWalk.stop();
    isWalking = false;
  }

  global.EWMWalkBridge = {
    init: init,
    triggerWalk: triggerWalk,
    triggerLaborEnterpriseWalk: triggerLaborEnterpriseWalk,
    setSpeed: setSpeed,
    stop: stop,
    removeAvatar: removeAvatar,
    isWalking: function() { return isWalking; },
    getConfig: function() { return config; }
  };

})(window);
