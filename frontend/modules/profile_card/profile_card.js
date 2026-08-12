/* ============================================================
   profile_card.js — 玩家身份卡片 + 详情弹窗模块
   从 player_world_city_ui.html 完整提取，自包含零外部依赖

   用法：
     <link rel="stylesheet" href="profile_card.css">
     <div id="profileCardContainer"></div>
     <script src="profile_card.js"></script>
     <script>
       EWMProfileCard.init({ container: 'profileCardContainer' });
       // 更新玩家数据: EWMProfileCard.update(playerData);
     </script>
   ============================================================ */

(function (global) {
  'use strict';

  var playerState = {
    name: "Player",
    role: "Player",
    identity: "Labor Force",
    wealthLevel: 3,
    riskPreference: "balanced",
    beta: null,
    lambda: null,
    cash: null,
    deposit: null,
    stockNecessity: null,
    stockLuxury: null,
    loan: null,
    totalAssets: null,
    currentEmployer: null,
    currentWage: null,
    employmentStatus: null,
    governmentSubsidy: null
  };

  var dom = {};
  var isExpanded = false;

  function formatMoney(value) {
    if (value == null || value === 0) return "N/A";
    return Number(value).toLocaleString("en-US", {maximumFractionDigits: 0}) + " CNY";
  }

  function createHTML() {
    return '' +
      '<section class="profile-card" id="ewm-profile-card" role="button" tabindex="0" aria-label="Player profile card">' +
        '<div class="profile-main">' +
          '<div class="avatar">P</div>' +
          '<div class="player-title">' +
            '<div class="player-name" id="ewm-player-name"></div>' +
          '</div>' +
          '<div class="profile-arrow">⌄</div>' +
          '<div class="profile-stats">' +
            '<div class="profile-stat">' +
              '<span class="label">Total Assets</span>' +
              '<span class="value" id="ewm-assets-value"></span>' +
            '</div>' +
            '<div class="profile-stat">' +
              '<span class="label">Wealth Tier</span>' +
              '<span class="value" id="ewm-wealth-value"></span>' +
            '</div>' +
            '<div class="profile-expand">Click to expand details</div>' +
          '</div>' +
        '</div>' +
      '</section>' +
      '<section class="personal-detail-popover" id="ewm-personal-detail-popover" aria-label="Player details popover">' +
        '<div class="personal-detail-head">' +
          '<div>' +
            '<div class="panel-kicker">Player Detail</div>' +
            '<h3>Personal Status Details</h3>' +
          '</div>' +
          '<button class="icon-btn" type="button" id="ewm-personal-detail-close" aria-label="Close personal details">×</button>' +
        '</div>' +
        '<div class="personal-detail-body" id="ewm-player-detail-grid"></div>' +
      '</section>';
  }

  function renderCard() {
    dom.playerName.textContent = playerState.name;
    dom.assetsValue.textContent = formatMoney(playerState.totalAssets);
    dom.wealthValue.textContent = playerState.wealthLevel;
  }

  function renderDetail() {
    var sections = [
      ["Basic Identity", [
        ["Identity", playerState.identity || "N/A"],
        ["Role", playerState.role || "N/A"],
        ["Wealth Tier", playerState.wealthLevel != null ? playerState.wealthLevel : "N/A"],
        ["Risk Preference", playerState.riskPreference || "N/A"],
        ["Beta", playerState.beta != null ? playerState.beta : "N/A"],
        ["Lambda", playerState.lambda != null ? playerState.lambda : "N/A"]
      ]],
      ["Assets & Funds", [
        ["Total Assets", formatMoney(playerState.totalAssets)],
        ["Available Funds", formatMoney(playerState.cash)],
        ["Deposit", formatMoney(playerState.deposit)],
        ["Stock (Necessity)", playerState.stockNecessity != null ? playerState.stockNecessity + " shares" : "N/A"],
        ["Stock (Luxury)", playerState.stockLuxury != null ? playerState.stockLuxury + " shares" : "N/A"],
        ["Loan", formatMoney(playerState.loan)]
      ]],
      ["Income & Employment", [
        ["Current Status", playerState.employmentStatus || "N/A"],
        ["Current Employer", playerState.currentEmployer || "N/A"],
        ["Current Wage", playerState.currentWage || "N/A"],
        ["Government Subsidy", playerState.governmentSubsidy || "N/A"]
      ]]
    ];

    dom.detailGrid.innerHTML = sections.map(function (sec) {
      var title = sec[0];
      var items = sec[1];
      return '<section class="personal-section">' +
        '<div class="personal-section-title">' + title + '</div>' +
        '<div class="personal-detail-grid">' +
          items.map(function (item) {
            return '<div class="detail-item">' +
              '<span class="label">' + item[0] + '</span>' +
              '<span class="value">' + item[1] + '</span>' +
            '</div>';
          }).join("") +
        '</div>' +
      '</section>';
    }).join("");
  }

  function openDetail() {
    renderDetail();
    dom.card.classList.add("expanded");
    dom.popover.classList.add("visible");
    isExpanded = true;
  }

  function closeDetail() {
    dom.card.classList.remove("expanded");
    dom.popover.classList.remove("visible");
    isExpanded = false;
  }

  function toggleDetail() {
    if (isExpanded) {
      closeDetail();
    } else {
      openDetail();
    }
  }

  function bindEvents() {
    dom.card.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleDetail();
    });

    dom.card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleDetail();
      }
    });

    dom.popover.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    dom.closeBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      closeDetail();
    });

    document.addEventListener("click", function () {
      if (isExpanded) closeDetail();
    });
  }

  function init(options) {
    options = options || {};
    var containerId = options.container || "profileCardContainer";
    var container = document.getElementById(containerId);
    if (!container) {
      container = document.createElement("div");
      container.id = containerId;
      document.body.appendChild(container);
    }

    container.innerHTML = createHTML();

    dom.card = document.getElementById("ewm-profile-card");
    dom.playerName = document.getElementById("ewm-player-name");
    dom.assetsValue = document.getElementById("ewm-assets-value");
    dom.wealthValue = document.getElementById("ewm-wealth-value");
    dom.popover = document.getElementById("ewm-personal-detail-popover");
    dom.closeBtn = document.getElementById("ewm-personal-detail-close");
    dom.detailGrid = document.getElementById("ewm-player-detail-grid");

    if (options.player) {
      update(options.player);
    } else {
      renderCard();
    }

    bindEvents();
  }

  function update(data) {
    if (!data || typeof data !== "object") return;
    for (var key in data) {
      if (data.hasOwnProperty(key) && playerState.hasOwnProperty(key)) {
        playerState[key] = data[key];
      }
    }
    renderCard();
    if (isExpanded) renderDetail();
  }

  function mapServerData(attrs) {
    if (!attrs || typeof attrs !== 'object') return {};
    var isEmployed = attrs.is_employed != null ? attrs.is_employed : null;
    var isLabor = attrs.is_labor_force != null ? attrs.is_labor_force : null;
    return {
      beta: attrs.beta != null ? attrs.beta : null,
      lambda: attrs.loss_aversion != null ? attrs.loss_aversion : null,
      totalAssets: attrs.current_total_assets != null ? attrs.current_total_assets : (attrs.last_total_assets != null ? attrs.last_total_assets : null),
      cash: attrs.total_available_funds != null ? attrs.total_available_funds : (attrs.current_remaining_assets != null ? attrs.current_remaining_assets : null),
      deposit: attrs.last_deposit_amount != null ? attrs.last_deposit_amount : null,
      stockNecessity: attrs.shares_held_necessity != null ? attrs.shares_held_necessity : null,
      stockLuxury: attrs.shares_held_luxury != null ? attrs.shares_held_luxury : null,
      loan: attrs.last_loan_amount != null ? attrs.last_loan_amount : (attrs.current_loan_amount != null ? attrs.current_loan_amount : null),
      wealthLevel: attrs.wealth_level != null ? attrs.wealth_level : (attrs.initial_wealth_level != null ? attrs.initial_wealth_level : null),
      employmentStatus: isEmployed === true ? 'Employed' : (isEmployed === false ? (isLabor ? 'Unemployed' : 'Non-Labor') : null),
      currentEmployer: attrs.employer_id != null ? 'Enterprise Firm ' + attrs.employer_id : 'None',
      currentWage: attrs.last_wage != null ? (Number(attrs.last_wage).toLocaleString('en-US') + ' CNY') : 'N/A',
      governmentSubsidy: attrs.current_subsidy != null ? (Number(attrs.current_subsidy).toFixed(0) + ' CNY') : 'N/A'
    };
  }

  function refreshFromServer() {
    fetch((typeof API_BASE !== 'undefined' ? API_BASE : '') + '/api/player_state', { method: 'POST' })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (!data.success || !data.player) return;
        var attrs = data.player.attributes || data.player;
        var mapped = mapServerData(attrs);
        update(mapped);
      })
      .catch(function(err) {
        console.warn('[EWMProfileCard] refreshFromServer failed', err);
      });
  }

  function getState() {
    return Object.assign({}, playerState);
  }

  global.EWMProfileCard = {
    init: init,
    update: update,
    refreshFromServer: refreshFromServer,
    open: openDetail,
    close: closeDetail,
    toggle: toggleDetail,
    getState: getState
  };

})(window);
