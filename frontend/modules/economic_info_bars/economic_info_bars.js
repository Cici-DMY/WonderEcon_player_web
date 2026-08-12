(function(global) {
  'use strict';

  var DEFAULT_WORLD_STATE = {
    tick: 3,
    monthLabel: "Month 3",
    economyPhase: "Rate Hike Month",
    macroEvent: "Central Bank raises rates by 25 bps, loan costs increase",
    worldStats: {
      averageLoanRate: "5.60%",
      averageDepositRate: "2.22%",
      inflation: "Elevated",
      tickSummary: "Month 3 enters rate hike phase. Corporate hiring slows, household asset allocation shifts to conservative."
    },
    environment: {
      numeric: [
        ["Current Tick", "3"],
        ["Month", "Month 3"],
        ["Economic Phase", "Rate Hike Month"],
        ["Average Wage", "5,200 CNY"],
        ["Average Loan Rate", "5.60%"],
        ["Average Deposit Rate", "2.22%"],
        ["Inflation Pressure", "Elevated"],
        ["Unemployment Rate", "12%"],
        ["Market Sentiment", "Cautious"],
        ["Policy Rate Change", "+25bp"]
      ],
      news: [
        "Month 3 - Rate Hike Month.",
        "1-year deposit rate 2.22%.",
        "1-year loan rate 5.60%.",
        "Mortgage rate 5.60%.",
        "Month 3 enters rate hike phase. Corporate hiring slows, household asset allocation shifts to conservative."
      ]
    }
  };

  var macroNewsByTick = null;

  function loadMacroNews() {
    return fetch("modules/data/macro_news_cn.json", { cache: "no-store" })
      .then(function(response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function(payload) {
        if (!payload || typeof payload !== "object") throw new Error("Invalid macro news payload");
        macroNewsByTick = payload;
        console.log("[MacroNews] loaded modules/data/macro_news_cn.json");
      })
      .catch(function(error) {
        macroNewsByTick = null;
        console.warn("[MacroNews] modules/data/macro_news_cn.json load failed, using fallback background.", error);
      });
  }

  var ECONOMIC_BACKGROUNDS_CN = {
    0: "The economy is showing signs of partial overheating; real estate is booming and investment demand is strong.",
    1: "The economy is running at a high level; inflation is emerging.",
    2: "Demand is stabilizing at a high level.",
    3: "Consumer prices are accelerating.",
    4: "Inflation pressure is intensifying.",
    5: "The economy is in a state of full overheating and high inflation.",
    6: "The inflation situation is deteriorating significantly.",
    7: "The economy is entering early stagflation: prices are soaring but demand is being damaged.",
    8: "High inflation persists.",
    9: "The economy is slowing but inflation remains elevated.",
    10: "Stagflation is deepening; demand contraction is becoming evident.",
    11: "Inflation appears to be peaking; the real economy is weakening.",
    12: "Demand is contracting across the board."
  };

  var ECONOMIC_TICKER_SHORT_CN = {
    0: "Partial overheating, real estate boom, strong investment demand",
    1: "High-level operation, inflation emerging",
    2: "Demand stabilizing at high level",
    3: "Consumer prices accelerating",
    4: "Inflation pressure intensifying",
    5: "Full overheating, high inflation forming",
    6: "Inflation deteriorating significantly",
    7: "Early stagflation, demand being damaged",
    8: "High inflation persists",
    9: "Economy slowing, inflation still high",
    10: "Stagflation deepening, demand contraction evident",
    11: "Inflation peaking, real economy weakening",
    12: "Demand contracting across the board"
  };

  var TICKER_PIXELS_PER_SECOND = 32;
  var TICKER_MIN_DURATION_SECONDS = 80;

  function cloneDefaultWorldState() {
    return JSON.parse(JSON.stringify(DEFAULT_WORLD_STATE));
  }

  function readInitialStateFromSession() {
    try {
      return JSON.parse(sessionStorage.getItem("EWMInitialState") || "null");
    } catch (error) {
      console.warn("[EWMInitialState] sessionStorage parse failed", error);
      return null;
    }
  }

  function formatRateForTicker(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" && Number.isFinite(value)) {
      var percentValue = Math.abs(value) <= 1 ? value * 100 : value;
      return percentValue.toFixed(2) + "%";
    }
    return String(value);
  }

  function getPanelValue(source, paths, fallback, worldState) {
    var roots = [source || {}, (source && source.environment) || {}, (source && source.market) || {}, (source && source.player) || {}, worldState || {}];
    for (var r = 0; r < roots.length; r++) {
      var root = roots[r];
      for (var p = 0; p < paths.length; p++) {
        var parts = String(paths[p]).split(".");
        var value = root;
        for (var i = 0; i < parts.length; i++) {
          if (value && typeof value === 'object') { value = value[parts[i]]; }
          else { value = undefined; break; }
        }
        if (value !== undefined && value !== null && value !== "") return value;
      }
    }
    return fallback;
  }

  function getEnvironmentFallbackByTick(tick) {
    var table = {
      0: { phase: "Partial Overheating", inflation: "Rising", demand: "Strong", policy: "Maintain benchmark rate" },
      1: { phase: "High-Level Operation", inflation: "Continuing to rise", demand: "Overheating", policy: "Monitoring inflation" },
      2: { phase: "High Plateau", inflation: "Elevated", demand: "Slowing from high", policy: "Maintain caution" },
      3: { phase: "Growth Cooling", inflation: "Accelerating", demand: "Marginally weakening", policy: "Policy observation period" },
      4: { phase: "Policy Cooling", inflation: "Food-driven", demand: "Continuing to slow", policy: "Tightening watch" },
      5: { phase: "Full Overheating", inflation: "High", demand: "Resilient", policy: "Rate hike expectations rising" },
      6: { phase: "First Rate Hike", inflation: "Significantly worsening", demand: "Still resilient", policy: "Central Bank raises rates" },
      7: { phase: "Early Stagflation", inflation: "High", demand: "Being damaged", policy: "Digesting first rate hike" },
      8: { phase: "Prolonged High Inflation", inflation: "Persistently high", demand: "Cooling", policy: "Preparing further tightening" },
      9: { phase: "Second Rate Hike", inflation: "Still elevated", demand: "Decelerating", policy: "Continue hiking" },
      10: { phase: "Deepening Stagflation", inflation: "Still high", demand: "Contraction emerging", policy: "Third rate hike" },
      11: { phase: "Inflation Peaking", inflation: "Near peak", demand: "Clearly weakening", policy: "Maintain tightening" },
      12: { phase: "Demand Contraction", inflation: "Declining from high", demand: "Full contraction", policy: "Fourth rate hike" }
    };
    return table[tick] || table[0];
  }

  function getSelectedTickNumber(initialState, worldState) {
    var environment = (initialState && initialState.environment) || {};
    var rawTick = (initialState && initialState.tick != null) ? initialState.tick :
                  (initialState && initialState.selectedTick != null) ? initialState.selectedTick :
                  (environment.tick != null) ? environment.tick :
                  (worldState.tick != null) ? worldState.tick : 1;
    var tick = parseInt(rawTick, 10);
    if (!isFinite(tick)) return 1;
    return Math.max(1, Math.min(13, tick));
  }

  function getCurrentTickFromInitialState(initialState, worldState) {
    return getSelectedTickNumber(initialState, worldState) - 1;
  }

  function buildEnvironmentMetrics(worldState, initialState) {
    if (!initialState) initialState = readInitialStateFromSession();
    var tick = getCurrentTickFromInitialState(initialState, worldState);
    var selectedTick = getSelectedTickNumber(initialState, worldState);
    var fallback = getEnvironmentFallbackByTick(tick);
    var worldStats = worldState.worldStats || {};
    var numericArr = (worldState.environment && worldState.environment.numeric) || [];
    var numericMap = {};
    for (var i = 0; i < numericArr.length; i++) {
      numericMap[numericArr[i][0]] = numericArr[i][1];
    }

    function value(paths, fallbackValue, formatter) {
      var raw = getPanelValue(initialState || {}, paths, fallbackValue, worldState);
      if (raw === "Pending") return raw;
      return formatter ? formatter(raw) : raw;
    }

    return [
      ["Current Tick", value(["tick", "selectedTick", "environment.tick"], selectedTick)],
      ["Economic Phase", value(["economyPhase", "eventType", "environment.economyPhase", "environment.rateEvent"], fallback.phase)],
      ["Benchmark Deposit Rate", value(["depositRate", "current_deposit_1yr", "currentDeposit1yr", "environment.depositRate", "environment.current_deposit_1yr", "worldStats.averageDepositRate"], worldStats.averageDepositRate || numericMap["Average Deposit Rate"] || "Pending", formatRateForTicker)],
      ["Benchmark Loan Rate", value(["loanRate", "current_loan_1yr", "currentLoan1yr", "environment.loanRate", "environment.current_loan_1yr", "worldStats.averageLoanRate"], worldStats.averageLoanRate || numericMap["Average Loan Rate"] || "Pending", formatRateForTicker)],
      ["Long-term Loan Rate", value(["longTermLoanRate", "current_loan_5yr", "currentLoan5yr", "environment.longTermLoanRate", "environment.current_loan_5yr"], "Pending", formatRateForTicker)],
      ["Mortgage Rate", value(["mortgageRate", "current_mortgage_rate", "currentMortgageRate", "environment.mortgageRate", "environment.current_mortgage_rate"], "Pending", formatRateForTicker)],
      ["Inflation Pressure", value(["inflationPressure", "inflation", "environment.inflationPressure", "environment.inflation"], worldStats.inflation || numericMap["Inflation Pressure"] || fallback.inflation)],
      ["Demand Status", value(["demandState", "demandStatus", "environment.demandState", "environment.demandStatus"], fallback.demand)],
      ["Policy Status", value(["policyState", "policyStatus", "eventType", "environment.policyState", "environment.policyStatus", "environment.rateEvent"], fallback.policy)]
    ];
  }

  function buildTickerTextFromInitialState(initialState) {
    if (!initialState || typeof initialState !== "object") return "";
    var environment = initialState.environment || {};
    var tick = initialState.tick != null ? initialState.tick : (environment.tick != null ? environment.tick : "");
    var monthLabel = initialState.monthLabel || environment.monthLabel || (tick !== "" ? "Month " + tick : "");
    var eventType = initialState.eventType || environment.rateEvent || "Normal Month";
    var depositRate = formatRateForTicker(initialState.depositRate != null ? initialState.depositRate : environment.depositRate);
    var loanRate = formatRateForTicker(initialState.loanRate != null ? initialState.loanRate : environment.loanRate);
    var mortgageRate = formatRateForTicker(initialState.mortgageRate != null ? initialState.mortgageRate : environment.mortgageRate);
    var headline = initialState.macroNews || environment.macroNews || initialState.economicBackground || environment.economicBackground || "";

    return [
      monthLabel,
      eventType,
      depositRate ? "1-year deposit rate " + depositRate : "",
      loanRate ? "1-year loan rate " + loanRate : "",
      mortgageRate ? "Mortgage rate " + mortgageRate : "",
      headline
    ].filter(Boolean).join(" · ");
  }

  function buildMacroNewsFallback(tick) {
    var background = ECONOMIC_BACKGROUNDS_CN[tick] || ECONOMIC_BACKGROUNDS_CN[0] || "";
    var shortText = ECONOMIC_TICKER_SHORT_CN[tick] || background;
    return {
      ticker: "Tick " + (tick + 1) + "/13 ｜ " + shortText,
      background: background,
      detail: "[Macro Background]\n" + background + "\n\n[News Details]\nNews details not yet available for this period. Displaying macro background summary."
    };
  }

  function normalizeMacroNewsEntry(entry, tick) {
    var fallback = buildMacroNewsFallback(tick);
    if (!entry) return fallback;
    if (typeof entry === "string") {
      var detailText = entry.indexOf("【宏观背景】") !== -1
        ? entry
        : "[Macro Background]\n" + fallback.background + "\n\n[News Details]\n" + entry;
      return {
        ticker: fallback.ticker,
        background: fallback.background,
        detail: detailText
      };
    }
    return {
      ticker: entry.ticker || fallback.ticker,
      background: entry.background || fallback.background,
      detail: entry.detail || ("[Macro Background]\n" + (entry.background || fallback.background) + "\n\n[News Details]\n" + (entry.news || entry.text || "News details not yet available for this period."))
    };
  }

  function applyInitialState(worldState, initialState) {
    if (!initialState || typeof initialState !== "object") return;
    var env = initialState.environment || {};
    var eventType = initialState.eventType || initialState.economyPhase || env.rateEvent || worldState.economyPhase;
    var macroNews = initialState.macroNews || env.macroNews || worldState.macroEvent;
    var depositRate = initialState.depositRate || env.depositRate || worldState.worldStats.averageDepositRate;
    var loanRate = initialState.loanRate || env.loanRate || worldState.worldStats.averageLoanRate;
    var mortgageRate = initialState.mortgageRate || env.mortgageRate;
    var economicBackground = initialState.economicBackground || env.economicBackground || "";

    worldState.tick = initialState.tick || worldState.tick;
    worldState.monthLabel = initialState.monthLabel || worldState.monthLabel;
    worldState.economyPhase = eventType;
    worldState.macroEvent = macroNews;
    worldState.worldStats.averageDepositRate = depositRate;
    worldState.worldStats.averageLoanRate = loanRate;
    worldState.worldStats.tickSummary = macroNews;
    worldState.environment.news = [
      "Month " + worldState.tick + ": " + eventType,
      "1-year deposit rate " + depositRate,
      "1-year loan rate " + loanRate,
      mortgageRate ? "Mortgage rate " + mortgageRate : "",
      economicBackground,
      macroNews
    ].filter(Boolean);
  }

  function fullMacroNewsDetail(entry) {
    if (!entry) return [];
    var detail = String(entry.detail || entry.ticker || "News details not yet available for this month.").trim();
    var blocks = detail.split(/\n\s*\n/).map(function(block) { return block.trim(); }).filter(Boolean);
    return blocks.length ? blocks : [detail];
  }

  function toTickerPlainText(value) {
    return String(value || "")
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<[^>]*>/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function buildFullEnvironmentTickerText(metrics, panelNews, fallbackText) {
    var metricText = (metrics || [])
      .map(function(m) { return m[0] + " " + m[1]; })
      .join(" ｜ ");
    var newsText = (panelNews || [])
      .map(toTickerPlainText)
      .filter(Boolean)
      .join(" ｜ ");
    return [metricText, newsText].filter(Boolean).join(" ｜ ") || fallbackText;
  }

  function ensureMarkup(mount) {
    var hud = (mount && mount.classList && mount.classList.contains("hud-layer"))
      ? mount
      : document.querySelector(".hud-layer");
    if (!hud) {
      hud = document.createElement("section");
      hud.className = "hud-layer";
      hud.id = "economic-info-hud";
      hud.setAttribute("aria-label", "Economic information overlay");
      mount.appendChild(hud);
    }

    if (!hud.querySelector("#environment-ticker")) {
      hud.insertAdjacentHTML("beforeend",
        '<section class="environment-ticker clickable" id="environment-ticker" aria-label="Environment info banner">' +
          '<div class="ticker-speaker">🔊</div>' +
          '<div class="ticker-viewport">' +
            '<div class="ticker-track" id="ticker-track"></div>' +
          '</div>' +
          '<button class="ticker-more" id="ticker-more" type="button">View News &gt;</button>' +
        '</section>' +

        '<section class="news-panel" id="environment-panel" aria-label="News list">' +
          '<div class="env-head">' +
            '<div>' +
              '<div class="panel-kicker">Market News</div>' +
              '<h2>This Month\'s News</h2>' +
            '</div>' +
            '<button class="icon-btn" type="button" id="environment-close" aria-label="Close news list">×</button>' +
          '</div>' +
          '<div class="env-body">' +
            '<section>' +
              '<div class="env-section-title">Environment Info</div>' +
              '<div class="env-metrics" id="environment-metrics"></div>' +
            '</section>' +
            '<section>' +
              '<div class="env-section-title">Static News</div>' +
              '<div class="env-news" id="environment-news"></div>' +
            '</section>' +
          '</div>' +
        '</section>' +

        '<footer class="world-status" id="world-status" aria-label="World status bar"></footer>'
      );
    }

    return {
      hud: hud,
      status: hud.querySelector("#world-status"),
      environmentTicker: hud.querySelector("#environment-ticker"),
      tickerTrack: hud.querySelector("#ticker-track"),
      environmentPanel: hud.querySelector("#environment-panel"),
      environmentClose: hud.querySelector("#environment-close"),
      environmentMetrics: hud.querySelector("#environment-metrics"),
      environmentNews: hud.querySelector("#environment-news")
    };
  }

  function renderWorldStatus(dom, worldState) {
    var cells = [
      ["Tick", worldState.tick],
      ["Economic Phase", worldState.economyPhase],
      ["Labor Households", "100"],
      ["Non-Labor Households", "40"],
      ["Necessity Firms", "10"],
      ["Luxury Firms", "2"],
      ["Commercial Banks", "2"],
      ["Central Bank", "1"],
      ["Government", "1"]
    ];
    dom.status.innerHTML = cells.map(function(cell) {
      return '<div class="status-cell"><span class="label">' + cell[0] + '</span><span class="value">' + cell[1] + '</span></div>';
    }).join("");
  }

  function updateTickerSpeed(dom) {
    if (!dom.tickerTrack) return;
    var viewportWidth = dom.tickerTrack.parentElement ? dom.tickerTrack.parentElement.clientWidth : 0;
    var travelDistance = Math.max(dom.tickerTrack.scrollWidth, viewportWidth);
    var duration = Math.max(
      TICKER_MIN_DURATION_SECONDS,
      Math.round(travelDistance / TICKER_PIXELS_PER_SECOND)
    );
    dom.tickerTrack.style.animationDuration = duration + "s";
  }

  function renderEnvironmentTicker(dom, worldState, macroNewsByTickData) {
    var initialState = readInitialStateFromSession();
    var news = (worldState.environment && worldState.environment.news) || [];
    var tick = getCurrentTickFromInitialState(initialState, worldState);
    var selectedTick = getSelectedTickNumber(initialState, worldState);
    var macroNewsEntry = normalizeMacroNewsEntry(macroNewsByTickData && macroNewsByTickData[String(tick)], tick);
    var tickerTextFromInitialState = buildTickerTextFromInitialState(initialState);
    var shortTickerText = ("Tick " + selectedTick + "/13 ｜ " + (ECONOMIC_TICKER_SHORT_CN[tick] || (macroNewsEntry && macroNewsEntry.background) || "")).trim();
    var panelNews = macroNewsEntry
      ? fullMacroNewsDetail(macroNewsEntry)
      : tickerTextFromInitialState
        ? tickerTextFromInitialState.split(" · ")
        : news;
    var metrics = buildEnvironmentMetrics(worldState, initialState);
    var tickerText = buildFullEnvironmentTickerText(metrics, panelNews, shortTickerText || (macroNewsEntry && macroNewsEntry.ticker) || tickerTextFromInitialState || (news.length
      ? news.join(" · ")
      : "Please select an economic time point to enter the city."));

    dom.tickerTrack.innerHTML = [tickerText, tickerText].map(function(text) {
      return '<span class="ticker-news">' + text + '</span>';
    }).join("");
    requestAnimationFrame(function() { updateTickerSpeed(dom); });
    dom.environmentMetrics.innerHTML = metrics.map(function(m) {
      return '<div class="env-metric-row"><span class="env-metric-label">' + m[0] + '</span><span class="env-metric-value">' + m[1] + '</span></div>';
    }).join("");
    dom.environmentNews.innerHTML = panelNews.map(function(item) {
      return '<div class="env-news-item">' + String(item).replace(/\n/g, "<br>") + '</div>';
    }).join("");
  }

  function isHudEventTarget(target) {
    if (!target || !target.closest) return false;
    return Boolean(target.closest(".hud-layer, .profile-card, .personal-detail-popover, .task-panel, .map-controls, .environment-ticker, .news-panel, .world-status, .building-finder, .building-finder-trigger, .guide-bubble, .guide-trigger, .popover, .entity-popover, .task-scene-overlay, .activity-log"));
  }

  function bindEvents(dom, controller, hooks) {
    hooks = hooks || {};
    dom.environmentTicker.addEventListener("click", function(event) {
      event.stopPropagation();
      controller.openEnvironmentPanel();
      if (typeof hooks.onEnvironmentOpen === 'function') hooks.onEnvironmentOpen();
    });
    dom.environmentClose.addEventListener("click", function(event) {
      event.stopPropagation();
      controller.closeEnvironmentPanel();
      if (typeof hooks.onEnvironmentClose === 'function') hooks.onEnvironmentClose();
    });
    document.addEventListener("click", function(event) {
      var isHudControl = isHudEventTarget(event.target);
      if (!event.target.closest || (!event.target.closest("[data-entity-id]") && !event.target.closest(".popover") && !isHudControl)) {
        controller.closeEnvironmentPanel();
      }
    });
    document.addEventListener("keydown", function(event) {
      if (event.key === "Escape") controller.closeEnvironmentPanel();
    });
  }

  function initEconomicInfoBars(options) {
    options = options || {};
    var mount = options.mount || document.body;
    var dom = ensureMarkup(mount);
    var worldState = options.worldState || cloneDefaultWorldState();
    if (!options.worldState) applyInitialState(worldState, readInitialStateFromSession());

    var controller = {
      render: function() {
        renderEnvironmentTicker(dom, worldState, macroNewsByTick);
        renderWorldStatus(dom, worldState);
      },
      openEnvironmentPanel: function() {
        renderEnvironmentTicker(dom, worldState, macroNewsByTick);
        dom.environmentPanel.classList.add("visible");
      },
      closeEnvironmentPanel: function() {
        dom.environmentPanel.classList.remove("visible");
      }
    };

    bindEvents(dom, controller, options);

    loadMacroNews().then(function() {
      controller.render();
    });

    controller.render();
    return controller;
  }

  global.EWMEconomicInfoBars = {
    init: initEconomicInfoBars
  };

})(window);
