(function(global) {
  'use strict';

  var TASK_DEFINITIONS = [
    {
      id: "loan_decision",
      title: "Loan Decision",
      icon: "\u{1F3E6}",
      targetEntityId: "bank-0",
      hint: "Commercial Bank: View loan terms and complete Loan Decision",
      unavailableHint: "Current identity and wealth level have no loan task access"
    },
    {
      id: "labor_decision",
      title: "Employment Decision",
      icon: "\u{1F465}",
      targetEntityId: "labor-market",
      hint: "talent_market: Set desired wage and decide whether to continue current employment",
      unavailableHint: "Current player has no employment status, not participating in employment task"
    },
    {
      id: "consumption_decision",
      title: "Consumption Decision",
      icon: "\u{1F6D2}",
      targetEntityId: "supermarket",
      hint: "supermarket: Arrange this period's consumption based on available funds",
      unavailableHint: "Current task unavailable"
    },
    {
      id: "stock_decision",
      title: "Stock Decision",
      icon: "\u{1F4C8}",
      targetEntityId: "stock-market",
      hint: "Stock Exchange: Evaluate risk preference and adjust positions",
      unavailableHint: "Current task unavailable"
    },
    {
      id: "deposit_decision",
      title: "Deposit Decision",
      icon: "\u{1F3E6}",
      targetEntityId: "bank-0",
      hint: "Commercial Bank: Arrange deposits based on interest rate environment",
      unavailableHint: "Current task unavailable"
    }
  ];

  var state = {
    current: null,
    currentIndex: 0,
    title: '',
    hint: '',
    targetEntityId: null,
    steps: [],
    allowedTaskIds: [],
    blockedTaskIds: [],
    taskPermission: null
  };

  var config = {
    onWalk: null,
    onLaborEnterpriseWalk: null,
    onSettlement: null,
    getEntity: null,
    onActivity: null,
    onToast: null
  };

  var dom = {};

  function getEntity(id) {
    if (typeof config.getEntity === 'function') {
      return config.getEntity(id);
    }
    return { name: id, id: id };
  }

  function getTaskPermission(player, explicitPermission) {
    if (explicitPermission && Array.isArray(explicitPermission.allowedTaskIds)) {
      var allowedSet = new Set(explicitPermission.allowedTaskIds);
      var firstAllowed = TASK_DEFINITIONS.find(function(task) { return allowedSet.has(task.id); }) || TASK_DEFINITIONS[0];
      return {
        allowedTaskIds: TASK_DEFINITIONS.filter(function(task) { return allowedSet.has(task.id); }).map(function(task) { return task.id; }),
        blockedTaskIds: TASK_DEFINITIONS.filter(function(task) { return !allowedSet.has(task.id); }).map(function(task) { return task.id; }),
        startTaskId: explicitPermission.startTaskId || firstAllowed.id,
        startTaskIndex: Number.isFinite(explicitPermission.startTaskIndex)
          ? explicitPermission.startTaskIndex
          : TASK_DEFINITIONS.findIndex(function(task) { return task.id === firstAllowed.id; })
      };
    }

    var identityText = String(player.identity || player.group || player.role || "").toLowerCase();
    var isNonLabor = identityText.includes("non-labor") || identityText.includes("nonlabor") || identityText.includes("非劳动力") || identityText.includes("退休");
    var isEmployed = player.isEmployed != null ? player.isEmployed : (player.is_employed != null ? player.is_employed : (!isNonLabor && (identityText.includes("labor") || identityText.includes("劳动力"))));
    var wealthLevel = Number.parseInt(player.wealthLevel || player.wealth_level, 10) || 3;

    var allowedNumbers;
    if (!isEmployed) {
      allowedNumbers = [3, 4, 5];
    } else if (wealthLevel <= 2) {
      allowedNumbers = [1, 2, 3, 4, 5];
    } else {
      allowedNumbers = [2, 3, 4, 5];
    }

    var allowedTaskIds = TASK_DEFINITIONS.filter(function(_, index) { return allowedNumbers.includes(index + 1); }).map(function(task) { return task.id; });
    var blockedTaskIds = TASK_DEFINITIONS.filter(function(task) { return !allowedTaskIds.includes(task.id); }).map(function(task) { return task.id; });
    var firstAllowed2 = TASK_DEFINITIONS.find(function(task) { return allowedTaskIds.includes(task.id); }) || TASK_DEFINITIONS[0];

    return {
      isEmployed: Boolean(isEmployed),
      wealthLevel: wealthLevel,
      allowedTaskIds: allowedTaskIds,
      blockedTaskIds: blockedTaskIds,
      startTaskId: firstAllowed2.id,
      startTaskIndex: TASK_DEFINITIONS.findIndex(function(task) { return task.id === firstAllowed2.id; })
    };
  }

  function isTaskAllowed(taskId) {
    var allowed = state.allowedTaskIds;
    return !Array.isArray(allowed) || allowed.includes(taskId);
  }

  function syncTaskFromIndex() {
    if (!Array.isArray(state.steps) || !Number.isFinite(state.currentIndex)) return;
    var allowedSet = new Set(state.allowedTaskIds || state.steps.filter(function(step) { return step.status !== "unavailable"; }).map(function(step) { return step.id; }));

    if (state.current === "complete") {
      state.steps.forEach(function(step) {
        if (!allowedSet.has(step.id)) {
          step.status = "unavailable";
          step.hint = step.hint || step.unavailableHint || "Current player cannot execute this task";
        } else {
          step.status = "done";
          step.result = step.result || "This task is completed";
        }
      });
      state.title = "All available tasks completed";
      state.hint = "All tasks available to the current role have been completed.";
      return;
    }

    state.steps.forEach(function(step, index) {
      if (!allowedSet.has(step.id)) {
        step.status = "unavailable";
        step.hint = step.hint || step.unavailableHint || "Current player cannot execute this task";
      } else if (index < state.currentIndex) {
        step.status = "done";
        step.result = step.result || "This task is completed";
      } else if (index === state.currentIndex) {
        step.status = "active";
        state.current = step.id;
        state.targetEntityId = step.targetEntityId;
        var target = getEntity(step.targetEntityId);
        state.title = "Go to " + (target ? target.name : "target building") + " to complete " + step.title;
        state.hint = step.hint || state.hint;
      } else {
        step.status = "locked";
        step.hint = step.hint || "Unlocks after completing prerequisite task";
      }
    });

    var activeStep = state.steps.find(function(step) { return step.status === "active"; });
    if (activeStep) {
      var target = getEntity(activeStep.targetEntityId);
      state.current = activeStep.id;
      state.currentIndex = state.steps.findIndex(function(step) { return step.id === activeStep.id; });
      state.targetEntityId = activeStep.targetEntityId;
      state.title = "Go to " + (target ? target.name : "target building") + " to complete " + activeStep.title;
      state.hint = activeStep.hint || state.hint;
    }
  }

  function applyPermissions(permissionInput, preferredTaskId) {
    var player = config.player || {};
    var existingSteps = state.steps || [];
    var preserved = new Map(existingSteps.map(function(step) { return [step.id, step]; }));
    var permission = getTaskPermission(player, permissionInput || state.taskPermission);
    var allowedSet = new Set(permission.allowedTaskIds);
    var preferredIndex = preferredTaskId ? TASK_DEFINITIONS.findIndex(function(def) { return def.id === preferredTaskId; }) : -1;

    var currentIndex;
    if (preferredIndex >= 0 && allowedSet.has(TASK_DEFINITIONS[preferredIndex].id)) {
      currentIndex = preferredIndex;
    } else if (Number.isFinite(state.currentIndex) && TASK_DEFINITIONS[state.currentIndex] && allowedSet.has(TASK_DEFINITIONS[state.currentIndex].id)) {
      currentIndex = state.currentIndex;
    } else {
      currentIndex = permission.startTaskIndex;
    }

    state.taskPermission = permission;
    state.allowedTaskIds = permission.allowedTaskIds;
    state.blockedTaskIds = permission.blockedTaskIds;
    state.currentIndex = currentIndex;
    state.steps = TASK_DEFINITIONS.map(function(definition, index) {
      var old = preserved.get(definition.id) || {};
      var allowed = allowedSet.has(definition.id);
      var status = "locked";
      if (!allowed) status = "unavailable";
      else if (index < currentIndex) status = "done";
      else if (index === currentIndex) status = "active";
      return {
        id: definition.id,
        title: definition.title,
        icon: definition.icon,
        targetEntityId: definition.targetEntityId,
        hint: allowed ? (old.hint || definition.hint) : definition.unavailableHint,
        unavailableHint: definition.unavailableHint,
        result: old.result,
        status: status
      };
    });

    syncTaskFromIndex();
    renderPanel();
  }

  function persistProgress() {
    try {
      sessionStorage.setItem('EWMTaskProgress', JSON.stringify({
        currentIndex: state.currentIndex,
        complete: state.current === 'complete'
      }));
    } catch(e) {}
  }

  function loadProgress() {
    try {
      var raw = sessionStorage.getItem('EWMTaskProgress');
      return raw ? JSON.parse(raw) : null;
    } catch(e) { return null; }
  }

  function advanceTask(currentTaskId) {
    var steps = state.steps || [];
    var allowedSet = new Set(state.allowedTaskIds || steps.filter(function(step) { return step.status !== "unavailable"; }).map(function(step) { return step.id; }));
    var currentIndex = steps.findIndex(function(step) { return step.id === currentTaskId; });

    if (currentIndex >= 0 && allowedSet.has(currentTaskId)) {
      steps[currentIndex].status = "done";
      steps[currentIndex].result = steps[currentIndex].result || "This task is completed";
    }

    var nextIndex = steps.findIndex(function(step, index) { return index > currentIndex && allowedSet.has(step.id); });
    if (nextIndex >= 0) {
      state.currentIndex = nextIndex;
      syncTaskFromIndex();
      persistProgress();
      renderPanel();
      return steps[nextIndex];
    }

    steps.forEach(function(step, index) {
      if (allowedSet.has(step.id)) {
        step.status = "done";
        step.result = step.result || "This task is completed";
      }
    });
    state.current = "complete";
    state.title = "All available tasks completed";
    state.hint = "All tasks available to the current role have been completed.";
    persistProgress();
    renderPanel();
    return null;
  }

  function consumeSceneResult() {
    var result = null;
    try {
      result = JSON.parse(sessionStorage.getItem("EWMInteriorResult") || "null");
    } catch (error) {
      console.warn("[EWMTaskFlow] result parse failed", error);
    }
    if (!result || !result.completed || !result.taskId) return null;
    sessionStorage.removeItem("EWMInteriorResult");

    if (result.taskId === "labor_decision" && result.sceneId === "labor_market") {
      var laborIndex = (state.steps || []).findIndex(function(step) { return step.id === "labor_decision"; });
      if (laborIndex >= 0 && isTaskAllowed("labor_decision")) {
        state.currentIndex = laborIndex;
        state.current = "labor_decision";
        syncTaskFromIndex();
        renderPanel();
      }
      if (typeof config.onActivity === 'function') {
        config.onActivity("Employment Decision", "talent_market phase completed, proceeding to enterprise.");
      }
      window.setTimeout(function() {
        if (typeof config.onLaborEnterpriseWalk === 'function') {
          config.onLaborEnterpriseWalk();
        } else {
          console.warn("[EWMTaskFlow] onLaborEnterpriseWalk not configured");
        }
      }, 500);
      return (state.steps || []).find(function(step) { return step.id === "labor_decision"; }) || null;
    }

    var nextStep = advanceTask(result.taskId);
    if (typeof config.onActivity === 'function') {
      config.onActivity("Task Complete", result.label || ((result.taskTitle || result.taskId) + " completed"));
    }
    return nextStep;
  }

  function handleStepClick(step) {
    if (!step || step.status !== "active") return;
    if (typeof config.onWalk === 'function') {
      config.onWalk(step);
    } else {
      console.warn("[EWMTaskFlow] onWalk not configured");
    }
  }

  function handleSettlementClick() {
    if (typeof config.onSettlement === 'function') {
      config.onSettlement(dom.settlementBtn);
    } else {
      console.warn("[EWMTaskFlow] onSettlement not configured");
    }
  }

  function togglePanel() {
    dom.panel.classList.toggle("collapsed");
    dom.toggleBtn.textContent = dom.panel.classList.contains("collapsed") ? "⌄" : "⌃";
  }

  function renderPanel() {
    if (!dom.panel) return;
    var total = state.steps.length || 1;
    var currentIndex = Number.isFinite(state.currentIndex) ? state.currentIndex : Math.max(0, state.steps.findIndex(function(step) { return step.status === "active"; }));
    var activeStep = state.steps[currentIndex];

    dom.taskTitle.textContent = activeStep ? activeStep.title : state.title;
    dom.taskTarget.textContent = (function() {
      if (!activeStep) return "Unspecified";
      var entity = getEntity(activeStep.targetEntityId);
      return entity ? entity.name : "Unspecified";
    })();
    dom.taskProgress.textContent = (currentIndex + 1) + " / " + total;
    dom.taskHint.textContent = state.hint;
    renderSteps();
    renderSettlement();
  }

  function renderSteps() {
    var steps = state.steps || [];
    dom.taskSteps.innerHTML = steps.map(function(step, index) {
      var target = getEntity(step.targetEntityId);
      var stateText = step.status === "done" ? "Completed" : step.status === "active" ? "Current Task" : step.status === "unavailable" ? "Unavailable" : "Locked";
      var subText = step.status === "active" ? step.hint : step.status === "done" ? step.result : step.status === "unavailable" ? (step.hint || "Current player cannot execute this task") : "Unlocks after completing prerequisite task";
      var disabled = step.status === "active" ? "" : "disabled";
      var iconText = step.status === "done" ? "✓" : step.status === "active" ? (step.icon || (index + 1)) : step.status === "unavailable" ? "—" : "\u{1F512}";

      return '<button class="task-step ' + step.status + '" type="button" data-task-id="' + step.id + '" ' + disabled + '>' +
        '<span class="task-step-icon">' + iconText + '</span>' +
        '<span>' +
          '<span class="task-step-title">' + step.title + '</span>' +
          '<span class="task-step-sub">' + (step.status === "active" && target ? (target.name + " · " + subText) : (subText || "")) + '</span>' +
          '<span class="task-step-state">' + stateText + '</span>' +
        '</span>' +
      '</button>';
    }).join("");

    dom.taskSteps.querySelectorAll(".task-step").forEach(function(button) {
      button.addEventListener("click", function(event) {
        event.stopPropagation();
        var step = steps.find(function(item) { return item.id === button.dataset.taskId; });
        handleStepClick(step);
      });
    });
  }

  function renderSettlement() {
    if (!dom.settlementEntry || !dom.settlementBtn) return;
    var isComplete = state.current === "complete";
    dom.settlementEntry.classList.toggle("visible", isComplete);
    dom.settlementBtn.disabled = !isComplete;
    if (isComplete) {
      dom.settlementBtn.textContent = "Enter Final Settlement";
    }
  }

  function buildDOM(containerId) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error("[EWMTaskFlow] container not found:", containerId);
      return;
    }

    container.innerHTML =
      '<section class="task-panel" id="ewm-task-panel" aria-label="Task Guide">' +
        '<div class="task-panel-head">' +
          '<div>' +
            '<div class="panel-kicker">Task Flow</div>' +
            '<div class="task-title" id="ewm-task-title">Loading...</div>' +
          '</div>' +
          '<button class="task-toggle" type="button" id="ewm-task-toggle" aria-label="Collapse task flow">⌃</button>' +
        '</div>' +
        '<div class="task-summary">' +
          '<span class="label">Current Progress</span>' +
          '<span class="value" id="ewm-task-progress">Task 1 / 5</span>' +
          '<span class="label">Recommended Target</span>' +
          '<span class="value" id="ewm-task-target">-</span>' +
        '</div>' +
        '<div class="task-expanded">' +
          '<div class="task-steps" id="ewm-task-steps"></div>' +
          '<div class="task-hint" id="ewm-task-hint"></div>' +
          '<div class="settlement-entry" id="ewm-settlement-entry" aria-live="polite">' +
            '<div class="settlement-title">This month\'s tasks completed</div>' +
            '<div class="settlement-copy">All available tasks for this month are completed. You can view the economic settlement animation.</div>' +
            '<button class="settlement-btn" type="button" id="ewm-settlement-btn">Enter Final Settlement</button>' +
          '</div>' +
        '</div>' +
      '</section>';

    dom.panel = document.getElementById('ewm-task-panel');
    dom.taskTitle = document.getElementById('ewm-task-title');
    dom.toggleBtn = document.getElementById('ewm-task-toggle');
    dom.taskProgress = document.getElementById('ewm-task-progress');
    dom.taskTarget = document.getElementById('ewm-task-target');
    dom.taskSteps = document.getElementById('ewm-task-steps');
    dom.taskHint = document.getElementById('ewm-task-hint');
    dom.settlementEntry = document.getElementById('ewm-settlement-entry');
    dom.settlementBtn = document.getElementById('ewm-settlement-btn');

    dom.toggleBtn.addEventListener('click', togglePanel);
    dom.settlementBtn.addEventListener('click', handleSettlementClick);
  }

  function init(options) {
    options = options || {};
    config.player = options.player || {};
    config.onWalk = options.onWalk || null;
    config.onLaborEnterpriseWalk = options.onLaborEnterpriseWalk || null;
    config.onSettlement = options.onSettlement || null;
    config.getEntity = options.getEntity || null;
    config.onActivity = options.onActivity || null;
    config.onToast = options.onToast || null;

    buildDOM(options.container || 'taskFlowContainer');

    var saved = loadProgress();
    if (saved && saved.complete) {
      applyPermissions(options.permission || null, options.preferredTaskId || null);
      state.steps.forEach(function(step) {
        var allowedSet = new Set(state.allowedTaskIds);
        if (allowedSet.has(step.id)) {
          step.status = "done";
          step.result = step.result || "This task is completed";
        }
      });
      state.current = "complete";
      state.title = "All available tasks completed";
      state.hint = "All tasks available to the current role have been completed.";
      renderPanel();
    } else if (saved && Number.isFinite(saved.currentIndex)) {
      applyPermissions(options.permission || null, TASK_DEFINITIONS[saved.currentIndex] ? TASK_DEFINITIONS[saved.currentIndex].id : null);
    } else {
      applyPermissions(options.permission || null, options.preferredTaskId || null);
    }
  }

  global.EWMTaskFlow = {
    init: init,
    applyPermissions: applyPermissions,
    advanceTask: advanceTask,
    consumeSceneResult: consumeSceneResult,
    renderPanel: renderPanel,
    getState: function() { return state; },
    getDefinitions: function() { return TASK_DEFINITIONS; }
  };

})(window);
