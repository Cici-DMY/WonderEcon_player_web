/* ============================================================
   popover.js — 建筑实体气泡弹窗模块
   从 player_world_city_ui.html 完整提取，自包含零外部依赖

   用法：
     <link rel="stylesheet" href="popover.css">
     <div class="popover" id="entityPopover"></div>
     <script src="popover.js"></script>
     <script>
       EWMPopover.init({ popover: 'entityPopover', scene: 'scene' });
       // 点击建筑时: EWMPopover.handleClick(buildingElement);
     </script>
   ============================================================ */

(function (global) {
  'use strict';

  /* ============================================================
     DATA — 适配"城市外景最终版"新地图，后续替换地图时只需改此段
     ============================================================ */

  // 建筑 name → buildingId
  var BUILDING_NAMES = {
    'commercial_bank_1': 'bank_01',
    'commercial_bank_2': 'bank_02',
    'central_bank': 'central_bank',
    'government': 'government',
    'labor_market': 'labor_market',
    'supermarket': 'supermarket',
    'necessity_1': 'necessity_01', 'necessity_2': 'necessity_02', 'necessity_3': 'necessity_03',
    'necessity_4': 'necessity_04', 'necessity_5': 'necessity_05', 'necessity_7': 'necessity_07',
    'necessity_8': 'necessity_08', 'necessity_9': 'necessity_09', 'necessity_10': 'necessity_10',
    'luxury_shop_1': 'luxury_01', 'luxury_shop_2': 'luxury_02',
    'stock_exchange': 'stock_exchange'
  };

  // layer → wealth level + 房屋类型 (新地图规则)
  var WEALTH_LAYERS = {
    'layer-6':  { level: 5, labor: ['house09'], nonlabor: ['house_1_1', 'house_1_2'] },
    'layer-7':  { level: 4, labor: ['house07'], nonlabor: ['house04'] },
    'layer-10': { level: 3, labor: ['house05'], nonlabor: ['house06'] },
    'layer-9':  { level: 2, labor: ['house02'], nonlabor: ['house03'] },
    'layer-11': { level: 1, labor: ['house01'], nonlabor: ['house10'] }
  };

  // buildingId → entityId
  function mapBuildingIdToEntityId(buildingId) {
    if (!buildingId) return null;
    if (buildingId === 'bank_01')       return 'bank-0';
    if (buildingId === 'bank_02')       return 'bank-1';
    if (buildingId === 'central_bank')  return 'central-bank';
    if (buildingId === 'government')    return 'government';
    if (buildingId === 'labor_market')  return 'labor-market';
    if (buildingId === 'supermarket')   return 'goods-market';
    if (buildingId === 'stock_exchange') return 'stock-market';
    if (buildingId.indexOf('house_') === 0)     return buildingId;
    return buildingId;
  }

  // 内部场景映射
  var INTERIOR_SCENE_MAP = {
    'bank-0': {
      label: 'Commercial Bank', sceneId: 'bank',
      taskPages: {
        loan_decision: 'modules/interaction/bank-loan-scene/bank_loan_scene_UI.html',
        deposit_decision: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_UI.html'
      },
      browsePages: {
        loan_decision: 'modules/interaction/bank-loan-scene/bank_loan_scene_browse.html',
        deposit_decision: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_browse.html'
      },
      page: 'modules/interaction/bank-loan-scene/bank_loan_scene_UI.html',
      browsePage: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_browse.html'
    },
    'bank-1': {
      label: 'Commercial Bank', sceneId: 'bank',
      taskPages: {
        loan_decision: 'modules/interaction/bank-loan-scene/bank_loan_scene_UI.html',
        deposit_decision: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_UI.html'
      },
      browsePages: {
        loan_decision: 'modules/interaction/bank-loan-scene/bank_loan_scene_browse.html',
        deposit_decision: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_browse.html'
      },
      page: 'modules/interaction/bank-loan-scene/bank_loan_scene_UI.html',
      browsePage: 'modules/interaction/bank-deposit-scene/bank_deposit_scene_browse.html'
    },
    'labor-market': { label: 'Labor Market', sceneId: 'labor_market',  page: 'modules/interaction/labor_scene/labor_scene_UI.html', browsePage: 'modules/interaction/labor_scene/labor_scene_browse.html' },
    'stock-market': { label: 'Stock Exchange', sceneId: 'stock_market', page: 'modules/interaction/stock_scene/stock_scene_UI.html', browsePage: 'modules/interaction/stock_scene/stock_scene_browse.html' },
    'goods-market': { label: 'supermarket',     sceneId: 'supermarket',  page: 'modules/interaction/market_scene/supermarket_scene_UI.html', browsePage: 'modules/interaction/market_scene/supermarket_scene_browse.html' },
    'supermarket':  { label: 'supermarket',     sceneId: 'supermarket',  page: 'modules/interaction/market_scene/supermarket_scene_UI.html', browsePage: 'modules/interaction/market_scene/supermarket_scene_browse.html' },
    'central-bank': { label: 'central_bank',    sceneId: 'central_bank', page: 'modules/interaction/central_bank_scene/central_bank_scene_browse.html', browsePage: 'modules/interaction/central_bank_scene/central_bank_scene_browse.html' },
    'government':   { label: 'government_building', sceneId: 'government', page: 'modules/interaction/government_scene/government_scene_browse.html', browsePage: 'modules/interaction/government_scene/government_scene_browse.html' },
    'house':        { label: 'home', sceneId: 'home', page: 'modules/interaction/home_scene/home_scene_browse.html', browsePage: 'modules/interaction/home_scene/home_scene_browse.html' }
  };

  var ENTERPRISE_SCENE_MAP = {
    luxury: {
      enterpriseType: 'luxury', label: 'Enterprise', sceneId: 'company1_scene',
      page: 'modules/interaction/company1_scene/company1_scene_UI.html',
      browsePage: 'modules/interaction/company1_scene/company1_scene_browse.html'
    },
    necessity: {
      enterpriseType: 'necessity', label: 'Enterprise', sceneId: 'company2_scene',
      page: 'modules/interaction/company2_scene/company2_scene_UI.html',
      browsePage: 'modules/interaction/company2_scene/company2_scene_browse.html'
    }
  };

  var AVAILABLE_INTERIOR_PAGES = [
    'modules/interaction/bank-loan-scene/bank_loan_scene_UI.html',
    'modules/interaction/bank-deposit-scene/bank_deposit_scene_UI.html',
    'modules/interaction/labor_scene/labor_scene_UI.html',
    'modules/interaction/stock_scene/stock_scene_UI.html',
    'modules/interaction/market_scene/supermarket_scene_UI.html',
    'modules/interaction/company1_scene/company1_scene_UI.html',
    'modules/interaction/company2_scene/company2_scene_UI.html',
    'modules/interaction/labor_scene/labor_scene_browse.html',
    'modules/interaction/stock_scene/stock_scene_browse.html',
    'modules/interaction/market_scene/supermarket_scene_browse.html',
    'modules/interaction/bank-loan-scene/bank_loan_scene_browse.html',
    'modules/interaction/bank-deposit-scene/bank_deposit_scene_browse.html',
    'modules/interaction/company1_scene/company1_scene_browse.html',
    'modules/interaction/company2_scene/company2_scene_browse.html',
    'modules/interaction/central_bank_scene/central_bank_scene_browse.html',
    'modules/interaction/government_scene/government_scene_browse.html',
    'modules/interaction/home_scene/home_scene_browse.html'
  ];

  // 建筑类型标签
  var TYPE_LABELS = {
    household: 'Household / Player', house: 'Household', bank: 'Bank',
    central_bank: 'central_bank', government: 'Government', firm: 'Enterprise',
    goods_market: 'supermarket', stock_market: 'Stock Exchange', labor_market: 'Labor Market',
    data_platform: 'Data Platform'
  };

  // 建筑描述
  var ENTITY_DESCRIPTIONS = {
    'bank-0':       'Commercial bank responsible for deposits, loans, mortgages, and other financial services.',
    'bank-1':       'Commercial bank responsible for deposits, loans, mortgages, and other financial services.',
    'central-bank': 'Central bank responsible for interest rate policy and the macro financial environment.',
    'government':   'Government building responsible for taxation, subsidies, and public policy.',
    'labor-market': 'Labor market for viewing employment opportunities, wage levels, and job-seeking status.',
    'stock-market': 'Stock exchange for viewing stock prices and investment decisions.',
    'supermarket':  'Supermarket and shops for consuming goods and comparing prices.',
    'goods-market': 'Supermarket and shops for consuming goods and comparing prices.'
  };

  // ============================================================
  // 经济实体数据 (同旧版 mockWorldState.entities)
  // ============================================================
  var ENTITIES = [
    {
      id: 'player', type: 'household', name: 'Player / Household', icon: '\u{1F3E0}',
      label: 'PLAYER', summary: 'The player enters the economic world as a consumer and observer. Complete this tick\'s financial and consumption decisions.',
      metrics: [['Identity', 'Labor Force'], ['Wealth Tier', '3'], ['Risk Preference', 'balanced'], ['Cash', '42,000 CNY'], ['Total Assets', '52,000 CNY']],
      actions: [{ label: 'View player status', type: 'view_player' }, { label: 'View current task', type: 'view_task' }]
    },
    {
      id: 'bank-0', type: 'bank', name: 'Commercial Bank 0', icon: '\u{1F3E6}',
      label: 'BANK', summary: 'Conservative commercial bank providing deposit and loan services. Current target for the player\'s loan decision.',
      metrics: [['Deposit Rate', '2.50%'], ['Loan Rate', '5.56%'], ['Risk Preference', 'Conservative'], ['Avg Loan', '8,600 CNY'], ['Capital Adequacy', '12.4%']],
      actions: [{ label: 'View loan terms', type: 'view_loan' }, { label: 'Go to Loan Decision', type: 'go_loan_decision' }, { label: 'Make deposit', type: 'deposit' }]
    },
    {
      id: 'bank-1', type: 'bank', name: 'Commercial Bank 1', icon: '\u{1F3E6}',
      label: 'BANK', summary: 'Commercial bank branch providing deposits, loans, and basic financial services.',
      metrics: [['Deposit Rate', '2.50%'], ['Loan Rate', '5.56%'], ['Risk Preference', 'Prudent'], ['Avg Loan', '8,200 CNY'], ['Capital Adequacy', '12.1%']],
      actions: [{ label: 'View loan terms', type: 'view_loan' }, { label: 'Go to Loan Decision', type: 'go_loan_decision' }, { label: 'Make deposit', type: 'deposit' }]
    },
    {
      id: 'central-bank', type: 'central_bank', name: 'central_bank', icon: '\u{1F3DB}️',
      label: 'CBANK', summary: 'Influences commercial banks, firms, and household expectations through benchmark rates and policy signals.',
      metrics: [['Policy Action', 'Rate hike 25bp'], ['Benchmark Deposit', '2.50%'], ['Benchmark Loan', '5.56%'], ['Policy Stance', 'Tightening']],
      actions: [{ label: 'View policy', type: 'view_policy' }, { label: 'View rate path', type: 'view_rate_path' }]
    },
    {
      id: 'government', type: 'government', name: 'Government', icon: '\u{1F3E2}',
      label: 'GOV', summary: 'Responsible for taxation, subsidies, public spending, and industrial policy. Affects residents\' available funds.',
      metrics: [['Income Tax', '800 CNY'], ['Gov. Subsidy', '500 CNY'], ['R&D Bonus', '0 CNY'], ['Policy Goal', 'Curb inflation']],
      actions: [{ label: 'View fiscal policy', type: 'view_fiscal' }, { label: 'View subsidies', type: 'view_subsidy' }]
    },
    {
      id: 'firm-0', type: 'firm', name: 'Enterprise Firm 0', icon: '\u{1F3ED}',
      label: 'FIRM', summary: 'Mid-size production firm that determines wages, hiring, and goods supply. One of the player\'s employers.',
      metrics: [['Total Staff', '12'], ['Output/Worker', '10 units'], ['Last Period Wage', '8,000 CNY'], ['Operating Status', 'Rising costs']],
      actions: [{ label: 'View employer', type: 'view_employer' }, { label: 'Evaluate wage', type: 'evaluate_wage' }]
    },
    {
      id: 'supermarket', type: 'goods_market', name: 'supermarket', icon: '\u{1F6D2}',
      label: 'STORE', summary: 'Consumer goods market where the player allocates budget for necessities and non-necessities.',
      metrics: [['Avg Price (incl. tax)', '55.30 CNY/unit'], ['Avg Consumption', '4.8 units'], ['Inflation Pressure', 'Elevated'], ['Suggested Budget', '80%-100%']],
      actions: [{ label: 'Arrange consumption', type: 'go_consumption' }, { label: 'Compare prices', type: 'compare_goods' }]
    },
    {
      id: 'stock-market', type: 'stock_market', name: 'Stock Exchange', icon: '\u{1F4C8}',
      label: 'STOCK', summary: 'Risk asset market. Prices are influenced by interest rates, corporate profits, and market sentiment.',
      metrics: [['Price', '102.50 CNY/share'], ['Shares Held', '50 shares'], ['Last Investment', '5,000 CNY'], ['Market Sentiment', 'Cautious']],
      actions: [{ label: 'Adjust position', type: 'go_stock_decision' }, { label: 'View stock prices', type: 'view_stock_price' }]
    },
    {
      id: 'labor-market', type: 'labor_market', name: 'Labor Market', icon: '\u{1F465}',
      label: 'JOBS', summary: 'Labor matching market affecting the player\'s employment, wage income, and loan eligibility.',
      metrics: [['Employment Rate', '88%'], ['Average Wage', '5,200 CNY'], ['Current Status', 'Employed'], ['Unemployment Risk', 'Medium-low']],
      actions: [{ label: 'Go to employment decision', type: 'go_labor_decision' }, { label: 'View jobs', type: 'view_jobs' }]
    },
    {
      id: 'data-hub', type: 'data_platform', name: 'Data Hub', icon: '\u{1F4CA}',
      label: 'DATA', summary: 'Aggregates economic world operational status for observing agent group metrics and macro events.',
      metrics: [['Households', '320'], ['Firms', '18'], ['Banks', '5'], ['Shops', '12']],
      actions: [{ label: 'Open Data Hub', type: 'open_data_center' }, { label: 'View world stats', type: 'view_world_stats' }]
    }
  ];

  // ============================================================
  // 内部状态
  // ============================================================
  var popoverEl = null;
  var sceneEl = null;
  var activeEntityId = null;
  var popoverTimer = null;
  var isTaskTriggered = false;
  var sceneLayoutLayers = [];
  var buildingElements = new Map();
  var config = {
    interactionServerOrigin: (function() {
      if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') return '';
      var m = location.pathname.match(/^\/[^/]+/);
      return m ? m[0] : '';
    })(),
    onEnterBuilding: null,
    onActivityLog: null,
    onShowToast: null,
    onClose: null,
    onAfterOpen: null,
    onFinishGuide: null,
    onRenderAgentList: null,
    getTaskId: null
  };

  // ============================================================
  // 工具函数
  // ============================================================
  function formatMoney(value) {
    if (value === null || value === undefined || value === '') return 'Pending';
    if (typeof value === 'number') return value.toLocaleString('en-US') + ' CNY';
    return String(value);
  }

  function formatOptionalMoney(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'number') return value.toLocaleString('en-US') + ' CNY';
    return String(value);
  }

  function normalizeSearchText(value) {
    return String(value || '').toLowerCase().replace(/\s+/g, '');
  }

  function includesAnyPattern(text, patterns) {
    text = String(text || '');
    return (patterns || []).some(function (p) { return text.indexOf(p) !== -1; });
  }

  function isHouseEntity(entityId) {
    return typeof entityId === 'string' && entityId.indexOf('house_') === 0;
  }

  function isFirmEntity(entityId) {
    return typeof entityId === 'string' && (entityId.indexOf('necessity_') === 0 || entityId.indexOf('luxury_') === 0);
  }

  function isBankEntity(entityId) {
    return entityId === 'bank_01' || entityId === 'bank_02';
  }

  function entityTypeLabel(type) {
    return TYPE_LABELS[type] || type || 'Unknown';
  }

  function getWealthLevelFromLayer(layerId, layers) {
    layers = Array.isArray(layers) ? layers : [];
    var layer = null;
    for (var i = 0; i < layers.length; i++) {
      if (layers[i].id === layerId) { layer = layers[i]; break; }
    }
    if (!layer) return WEALTH_LAYERS[layerId] ? WEALTH_LAYERS[layerId].level : null;
    var name = layer.name || '';
    var match = name.match(/财富\s*(\d+)/);
    if (match) return Number(match[1]);
    return WEALTH_LAYERS[layerId] ? WEALTH_LAYERS[layerId].level : null;
  }

  function getSceneEl() {
    return sceneEl || document.getElementById('scene') || document.querySelector('.scene');
  }

  // ============================================================
  // 房屋类型推断
  // ============================================================
  function getHouseType(src, layerId) {
    var wl = WEALTH_LAYERS[layerId];
    if (!wl || !src) return null;
    if (layerId === 'layer-6') {
      if (src.indexOf('house_1_1') !== -1 || src.indexOf('house_1_2') !== -1) return 'nonlabor';
      if (src.indexOf('house09') !== -1) return 'labor';
    } else {
      if (includesAnyPattern(src, wl.labor || [])) return 'labor';
      if (includesAnyPattern(src, wl.nonlabor || [])) return 'nonlabor';
    }
    return null;
  }

  function inferHouseCategory(itemOrNode) {
    var layerId = itemOrNode.layer || (itemOrNode.dataset && itemOrNode.dataset.layer) || '';
    var src = itemOrNode.src || (itemOrNode.dataset && itemOrNode.dataset.src) || '';
    var houseType = getHouseType(src, layerId);
    var wealthLevel = WEALTH_LAYERS[layerId] ? WEALTH_LAYERS[layerId].level : null;
    if (!houseType || !wealthLevel) return null;
    return {
      layerId: layerId,
      wealthLevel: wealthLevel,
      houseType: houseType,
      identityType: houseType === 'labor' ? 'Labor Force' : 'Non-Labor Force',
      identityKey: houseType === 'labor' ? 'labor' : 'nonlabor',
      key: 'wealth' + wealthLevel + '_' + (houseType === 'labor' ? 'labor' : 'nonlabor')
    };
  }

  function isResidentialHouseItem(itemOrNode) {
    return Boolean(inferHouseCategory(itemOrNode));
  }

  function buildHouseDisplayName(category, index) {
    return 'Wealth ' + category.wealthLevel + '-' + category.identityType + ' Household-' + pad2(index);
  }

  function pad2(n) {
    return String(n).length < 2 ? '0' + n : String(n);
  }

  // ============================================================
  // 企业类型推断
  // ============================================================
  function inferEnterpriseType(itemOrNode) {
    var dataset = itemOrNode.dataset || {};
    var name = itemOrNode.name || '';
    var itemSrc = itemOrNode.src || '';
    var text = [
      name, dataset.name || '', dataset.buildingId || '',
      itemSrc, dataset.src || ''
    ].filter(Boolean).join(' ').toLowerCase();
    if (text.indexOf('奢侈品') !== -1 || text.indexOf('luxury') !== -1) {
      return { type: 'luxury', displayName: 'Enterprise' };
    }
    if (text.indexOf('必需品') !== -1 || text.indexOf('necessity') !== -1 || text.indexOf('necessary') !== -1) {
      return { type: 'necessity', displayName: 'Enterprise' };
    }
    return null;
  }

  // ============================================================
  // 实体查询
  // ============================================================
  function getEntity(entityId) {
    var aliases = { 'goods-market': 'supermarket', 'player-home': 'player' };
    if (entityId && entityId.indexOf('house_') === 0) {
      var found = null;
      ENTITIES.forEach(function (e) { if (e.id === 'player') found = e; });
      return found;
    }
    for (var i = 0; i < ENTITIES.length; i++) {
      if (ENTITIES[i].id === entityId) return ENTITIES[i];
    }
    var aliasId = aliases[entityId];
    if (aliasId) {
      for (var j = 0; j < ENTITIES.length; j++) {
        if (ENTITIES[j].id === aliasId) return ENTITIES[j];
      }
    }
    return null;
  }

  function resolveSceneEntityId(entityId) {
    if (!entityId) return '';
    var hasEntity = false;
    ENTITIES.forEach(function (e) { if (e.id === entityId) hasEntity = true; });
    if (hasEntity) return entityId;
    var aliases = {
      'data-platform': 'data-hub', 'data_platform': 'data-hub',
      'goods-market': 'supermarket', 'goods_market': 'supermarket',
      'player-home': 'player', store: 'supermarket', jobs: 'labor-market'
    };
    if (entityId.indexOf('house_') === 0) return 'player';
    return aliases[entityId] || entityId;
  }

  function getEntityDescription(entityId, entity, isHouse, isFirm, isBank) {
    if (isHouse) return 'Household agent dwellings. View household attributes including risk preference, beta, and wealth class.';
    if (isFirm) return 'Production firm agent. View firm attributes including scale level, listed status, risk preference, and ability.';
    if (isBank) return 'Commercial bank agent. View bank attributes including relative scale and risk preference.';
    return ENTITY_DESCRIPTIONS[entityId] || ENTITY_DESCRIPTIONS[entity && entity.id] ||
      (entity && entity.summary) || 'No description available.';
  }

  function getEntryButtonLabel(entityId, entity) {
    if (isHouseEntity(entityId)) return 'Enter room';
    if (isFirmEntity(entityId)) return 'Enter Firm';
    if (entityId === 'bank-0' || entityId === 'bank-1' || entityId === 'bank_01' || entityId === 'bank_02') {
      var taskId = typeof config.getTaskId === 'function' ? config.getTaskId() : null;
      if (taskId === 'loan_decision') return 'Enter Loan Decision';
      if (taskId === 'deposit_decision') return 'Enter Deposit Decision';
      return 'Enter Commercial Bank';
    }
    if (entityId === 'central-bank') return 'Enter Central Bank';
    if (entityId === 'government')   return 'Enter Government Building';
    if (entityId === 'labor-market')  return 'Enter Labor Market';
    if (entityId === 'stock-market')  return 'Enter Stock Exchange';
    if (entityId === 'goods-market' || entityId === 'supermarket') return 'Enter Supermarket';
    return 'Enter ' + ((entity && entity.name) || 'building');
  }

  // ============================================================
  // 场景元素搜索 (适配新地图 .building 类名 + dataset.buildingId)
  // ============================================================
  function findSceneItemByEntityId(entityId) {
    var scn = getSceneEl();
    if (!scn) return null;

    var resolvedId = resolveSceneEntityId(entityId);
    var items = scn.querySelectorAll('.building, .scene-item');

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      if (item.dataset.entityId === entityId ||
          item.dataset.entityId === resolvedId ||
          item.dataset.resolvedEntityId === resolvedId) {
        return item;
      }
    }

    if (isHouseEntity(entityId)) {
      for (var j = 0; j < items.length; j++) {
        if (items[j].dataset.buildingId === entityId) return items[j];
      }
    }

    for (var k = 0; k < items.length; k++) {
      var bid = items[k].dataset.buildingId;
      if (bid && mapBuildingIdToEntityId(bid) === resolvedId) return items[k];
    }

    var entity = getEntity(resolvedId);
    if (!entity) return null;
    for (var m = 0; m < items.length; m++) {
      var haystack = normalizeSearchText(
        (items[m].id || '') + ' ' + (items[m].dataset.name || '') + ' ' + (items[m].dataset.buildingId || '')
      );
      var tokens = [entity.id, entity.name, entity.label, entity.type].filter(Boolean);
      for (var n = 0; n < tokens.length; n++) {
        if (haystack.indexOf(normalizeSearchText(tokens[n])) !== -1) return items[m];
      }
    }
    return null;
  }

  function findSceneItemByIdOrName(idOrName) {
    var scn = getSceneEl();
    if (!scn) return null;
    var query = normalizeSearchText(idOrName);
    if (!query) return null;
    var items = scn.querySelectorAll('.building, .scene-item');
    for (var i = 0; i < items.length; i++) {
      var haystack = normalizeSearchText(
        (items[i].id || '') + ' ' +
        (items[i].dataset.name || '') + ' ' +
        (items[i].dataset.buildingId || '') + ' ' +
        (items[i].dataset.entityId || '')
      );
      if (haystack.indexOf(query) !== -1) return items[i];
    }
    return null;
  }

  // ============================================================
  // 房屋→Agent 映射数据
  // ============================================================
  var houseAgentMap = null;
  var firmAgentMap = null;
  var bankAgentMap = null;
  var centralBankData = null;
  var governmentData = null;
  var supermarketData = null;
  var laborMarketData = null;
  var stockMarketData = null;

  function betaToLevel(beta) {
    if (beta == null) return '—';
    if (beta <= 0.54) return 'Very Low (L1)';
    if (beta <= 0.87) return 'Low (L2)';
    if (beta <= 1.15) return 'Moderate (L3)';
    if (beta <= 1.51) return 'High (L4)';
    return 'Very High (L5)';
  }

  function getCurrentTick() {
    try {
      var s = JSON.parse(sessionStorage.getItem('EWMInitialState') || 'null');
      return (s && s.tick != null) ? Number(s.tick) - 1 : null;
    } catch(e) { return null; }
  }

  // ============================================================
  // 环境实体动态数据
  // ============================================================
  function isEnvEntity(entityId) {
    if (entityId === 'goods-market') entityId = 'supermarket';
    return ['government', 'central-bank', 'supermarket', 'labor-market', 'stock-market'].indexOf(entityId) !== -1;
  }

  var ENV_METRICS = {
    'government': [
      ['Personal Income Tax', 'personal_income_tax_rate', 'percent'],
      ['Corporate Income Tax', 'corporate_income_tax_rate', 'percent'],
      ['Corporate VAT', 'corporate_vat_rate', 'percent'],
      ['Welfare Distribution', 'last_distribution_pct', 'percentMul'],
      ['Total Tax Revenue', 'current_total_tax', 'money'],
    ],
    'central-bank': [
      ['Deposit Rate 1YR', 'deposit_1yr', 'percent'],
      ['Loan Rate 1YR', 'loan_1yr', 'percent'],
      ['Loan Rate 5YR+', 'loan_5yr_plus', 'percent'],
      ['Mortgage Rate', 'mortgage_rate', 'percent'],
      ['Injection Status', 'last_injected', 'bool'],
      ['Injection %', 'last_injection_pct', 'percent'],
    ],
    'supermarket': [
      ['Avg Necessity Price', 'last_avg_taxed_goods_price_necessity', 'price'],
      ['Avg Luxury Price', 'last_avg_taxed_goods_price_luxury', 'price'],
    ],
    'labor-market': [
      ['Employment Rate', 'last_employment_rate', 'percent'],
      ['Average Wage', 'last_avg_household_wage', 'money'],
    ],
    'stock-market': [
      ['Necessity Stock Price', 'current_stock_price_necessity', 'price'],
      ['Necessity Trading Volume', 'current_stock_volume_necessity', 'number'],
      ['Luxury Stock Price', 'current_stock_price_luxury', 'price'],
      ['Luxury Trading Volume', 'current_stock_volume_luxury', 'number'],
    ],
  };

  function getEnvData(entityId) {
    if (entityId === 'goods-market') entityId = 'supermarket';
    switch (entityId) {
      case 'government':   return governmentData;
      case 'central-bank': return centralBankData;
      case 'supermarket':  return supermarketData;
      case 'labor-market': return laborMarketData;
      case 'stock-market': return stockMarketData;
      default: return null;
    }
  }

  function formatEnvValue(val, fmt) {
    if (val == null) return '—';
    switch (fmt) {
      case 'percent': return (val * 100).toFixed(2) + '%';
      case 'percentMul': return (val * 100).toFixed(0) + '%';
      case 'money': return typeof val === 'number' ? Math.round(val).toLocaleString('en-US') + ' CNY' : String(val);
      case 'price': return typeof val === 'number' ? val.toFixed(2) + ' CNY' : String(val);
      case 'qty': return typeof val === 'number' ? val.toFixed(1) + ' units' : String(val);
      case 'bool': return val ? 'Injected' : 'Withdrawn';
      case 'number': return typeof val === 'number' ? val.toFixed(1) : String(val);
      default: return String(val);
    }
  }

  function enrichEntityWithEnvData(entity, entityId) {
    var resolved = entityId === 'goods-market' ? 'supermarket' : entityId;
    var envConfig = ENV_METRICS[resolved];
    var data = getEnvData(resolved);
    if (!envConfig || !data || !data.byTick) return entity;

    var currentTick = getCurrentTick();
    var tickData = (currentTick != null) ? data.byTick[String(currentTick)] : null;
    if (!tickData) return entity;

    var newMetrics = envConfig.map(function (m) {
      return [m[0], formatEnvValue(tickData[m[1]], m[2])];
    });

    var clone = {};
    var keys = Object.keys(entity);
    for (var i = 0; i < keys.length; i++) { clone[keys[i]] = entity[keys[i]]; }
    clone.metrics = newMetrics;
    return clone;
  }

  // ============================================================
  // 动态生成房屋实体对象
  // ============================================================
  function parseHouseEntityId(entityId) {
    var parts = entityId.split('_');
    if (parts.length >= 4 && parts[0] === 'house') {
      return {
        level: parts[1],
        identityType: parts[2] === 'labor' ? 'Labor Force' :
                      parts[2] === 'nonlabor' ? 'Non-Labor Force' : '',
        number: parts.slice(3).join('_')
      };
    }
    return null;
  }

  function buildHousePopoverEntity(entityId, sourceElement) {
    var agentData = houseAgentMap && houseAgentMap[entityId];
    var agentId = agentData ? agentData.agentId : null;
    var currentTick = getCurrentTick();

    var identityType = agentData ? agentData.identityType : '';
    if (!identityType) {
      var isItem = sourceElement && (sourceElement.classList.contains('building') || sourceElement.classList.contains('scene-item'));
      var item = isItem ? sourceElement : findSceneItemByEntityId(entityId);
      identityType = (item && item.dataset && (item.dataset.identityType || item.dataset.houseType)) || '';
    }
    if (!identityType) {
      var parsed = parseHouseEntityId(entityId);
      if (parsed) identityType = parsed.identityType;
    }
    if (!identityType) identityType = 'Unrecognized';

    var wealthLabel = '';
    if (agentData && agentData.wealthByTick && currentTick != null) {
      var tickWealth = agentData.wealthByTick[String(currentTick)];
      if (tickWealth != null) wealthLabel = 'Wealth ' + tickWealth;
    }
    if (!wealthLabel) {
      var layer2 = (sourceElement && sourceElement.dataset && sourceElement.dataset.layer) || '';
      var level2 = getWealthLevelFromLayer(layer2, sceneLayoutLayers);
      if (level2) wealthLabel = 'Wealth ' + level2;
    }
    if (!wealthLabel) {
      var p2 = parseHouseEntityId(entityId);
      if (p2) wealthLabel = 'Wealth ' + p2.level;
    }
    if (!wealthLabel) wealthLabel = 'Unrecognized';

    var houseName = agentId != null ? 'Household ' + (agentId + 1) : ('Household ' + entityId.replace(/^house_/, ''));
    var riskPref = (agentData && agentData.riskPreference) ? agentData.riskPreference : '—';
    var betaLabel = betaToLevel(agentData ? agentData.beta : null);

    return {
      id: entityId,
      label: 'Household',
      name: houseName,
      type: 'house',
      summary: 'Household agent dwelling. View household attributes including risk preference, beta, and wealth class.',
      metrics: [
        ['Wealth Class', wealthLabel],
        ['Identity Type', identityType],
        ['Risk Preference', riskPref],
        ['Ability', betaLabel],
        ['Entry Status', 'Reserved']
      ],
      actions: []
    };
  }

  function buildFirmPopoverEntity(entityId, sourceElement) {
    var firmData = firmAgentMap && firmAgentMap[entityId];
    var agentId = firmData ? firmData.agentId : null;
    var currentTick = getCurrentTick();

    var sector = firmData ? firmData.sector : '';
    var firmType = sector === 'luxury' ? 'Luxury' : 'Necessity';
    var isListed = firmData ? (firmData.isListed ? 'Listed' : 'Unlisted') : '—';

    var scaleLabel = '';
    if (firmData && firmData.scaleByTick && currentTick != null) {
      var tickScale = firmData.scaleByTick[String(currentTick)];
      if (tickScale != null) scaleLabel = 'Level ' + tickScale;
    }
    if (!scaleLabel) {
      scaleLabel = firmData && firmData.initialScaleLevel != null ? 'Level ' + firmData.initialScaleLevel : '—';
    }

    var riskPref = (firmData && firmData.riskPreference) ? firmData.riskPreference : '—';
    var betaLabel = betaToLevel(firmData ? firmData.beta : null);
    var firmName = agentId != null ? 'Firm ' + (agentId + 1) : ('Firm ' + entityId);

    return {
      id: entityId,
      label: 'Firm',
      name: firmName,
      type: 'firm',
      summary: 'Production firm agent. View firm attributes including scale level, listed status, risk preference, and ability.',
      metrics: [
        ['Firm Type', firmType],
        ['Listed', isListed],
        ['Scale', scaleLabel],
        ['Risk Preference', riskPref],
        ['Ability', betaLabel]
      ],
      actions: []
    };
  }

  function buildBankPopoverEntity(entityId, sourceElement) {
    var bankData = bankAgentMap && bankAgentMap[entityId];
    var agentId = bankData ? bankData.agentId : null;
    var currentTick = getCurrentTick();

    var scaleLabel = '—';
    if (bankData && bankData.relativeScaleByTick && currentTick != null) {
      var tickScale = bankData.relativeScaleByTick[String(currentTick)];
      if (tickScale != null) scaleLabel = tickScale;
    }

    var riskPref = (bankData && bankData.riskPreference) ? bankData.riskPreference : '—';
    var bankName = agentId != null ? 'Bank ' + (agentId + 1) : entityId;

    return {
      id: entityId,
      label: 'Bank',
      name: bankName,
      type: 'bank',
      summary: 'Commercial bank agent. View bank attributes including relative scale and risk preference.',
      metrics: [
        ['Relative Scale', scaleLabel],
        ['Risk Preference', riskPref]
      ],
      actions: []
    };
  }

  function getPopoverEntity(entityId) {
    return isHouseEntity(entityId) ? buildHousePopoverEntity(entityId) : getEntity(entityId);
  }

  // ============================================================
  // 气泡定位
  // ============================================================
  function placePopover(labelEl, popEl) {
    if (!labelEl || !popEl) return;
    var labelRect = labelEl.getBoundingClientRect();
    var popRect = popEl.getBoundingClientRect();
    var left = labelRect.right + 12;
    var top = labelRect.top - 8;

    if (left + popRect.width > window.innerWidth - 16) {
      left = labelRect.left - popRect.width - 12;
    }
    if (left < 16) left = 16;
    if (top + popRect.height > window.innerHeight - 16) {
      top = window.innerHeight - popRect.height - 16;
    }
    if (top < 16) top = 16;

    popEl.style.left = left + 'px';
    popEl.style.top = top + 'px';
  }

  function positionPopover(entity) {
    if (!entity) return;
    var labelEl = findSceneItemByEntityId(entity.id) || buildingElements.get(entity.id);
    placePopover(labelEl, popoverEl);
  }

  function syncEntitySelection() {
    buildingElements.forEach(function (node, entityId) {
      node.classList.toggle('active', entityId === activeEntityId);
    });
  }

  function renderAgentList() {
    if (typeof config.onRenderAgentList === 'function') {
      config.onRenderAgentList(ENTITIES, activeEntityId);
    }
  }

  function registerBuildingElement(entityId, node) {
    if (!entityId || !node) return;
    buildingElements.set(entityId, node);
    var resolvedId = resolveSceneEntityId(entityId);
    if (resolvedId && resolvedId !== entityId) {
      buildingElements.set(resolvedId, node);
    }
  }

  // ============================================================
  // 气泡核心: 打开 / 关闭
  // ============================================================

  function closePopover() {
    window.clearTimeout(popoverTimer);
    popoverTimer = null;
    activeEntityId = null;
    if (popoverEl) {
      popoverEl.classList.remove('visible', 'fading');
    }
    syncEntitySelection();
    renderAgentList();
    if (typeof config.onClose === 'function') config.onClose();
  }

  function openEntityPopover(entityId, options) {
    options = options || {};
    closePopover();
    window.clearTimeout(popoverTimer);

    isTaskTriggered = Boolean(options.fromTask);

    var originalEntityId = entityId;
    var isHouse = isHouseEntity(originalEntityId);
    var isFirm = isFirmEntity(originalEntityId);
    var isBank = isBankEntity(originalEntityId);
    var isDynamic = isHouse || isFirm || isBank;
    var resolvedEntityId = isDynamic ? originalEntityId : resolveSceneEntityId(entityId);
    var entity = isHouse
      ? buildHousePopoverEntity(originalEntityId, options.sourceElement)
      : isFirm
        ? buildFirmPopoverEntity(originalEntityId, options.sourceElement)
        : isBank
          ? buildBankPopoverEntity(originalEntityId, options.sourceElement)
          : getEntity(resolvedEntityId);

    if (!entity) return;

    if (!isDynamic && isEnvEntity(resolvedEntityId)) {
      entity = enrichEntityWithEnvData(entity, resolvedEntityId);
    }

    var interiorEntityId = isDynamic
      ? originalEntityId
      : (INTERIOR_SCENE_MAP[originalEntityId] ? originalEntityId : resolvedEntityId);
    var sceneMapKey = isHouse ? 'house' : interiorEntityId;
    var entryLabel = getEntryButtonLabel(interiorEntityId, entity);
    var description = getEntityDescription(interiorEntityId, entity, isHouse, isFirm, isBank);

    activeEntityId = isDynamic ? originalEntityId : resolvedEntityId;
    syncEntitySelection();
    renderAgentList();

    if (!popoverEl) { popoverEl = document.getElementById('entityPopover'); }
    if (!popoverEl) return;

    popoverEl.classList.remove('fading');

    var metricsHTML = (entity.metrics || []).map(function (m) {
      return '<div class="popover-metric-row"><span>' + m[0] + '</span><span>' + m[1] + '</span></div>';
    }).join('');

    var scene = INTERIOR_SCENE_MAP[sceneMapKey];
    var hasBrowse = scene && scene.browsePage;
    var hasEnterpriseBrowse = false;
    var browseOnly = scene && scene.page === scene.browsePage;
    var taskEnabled = isCurrentTaskTarget(interiorEntityId);
    var taskDisabledAttr = taskEnabled ? '' : ' disabled';

    popoverEl.innerHTML =
      '<div class="popover-head">' +
        '<div>' +
          '<div class="popover-name">' + (entity.name || '') + '</div>' +
          '<div class="popover-auto">Click x to close</div>' +
        '</div>' +
        '<button class="icon-btn" type="button" aria-label="Close popover" data-close-popover>&times;</button>' +
      '</div>' +
      '<div class="popover-summary">' + description + '</div>' +
      '<div class="popover-metrics">' + metricsHTML + '</div>' +
      '<div class="popover-actions">' +
        (browseOnly
          ? (hasBrowse ? '<button class="popover-enter-btn popover-browse-btn" type="button" data-browse-building="' + interiorEntityId + '">Browse Scene</button>' : '')
          : '<button class="popover-enter-btn popover-task-btn" type="button" data-enter-building="' + interiorEntityId + '"' + taskDisabledAttr + '>' + entryLabel + '</button>' +
            (hasBrowse ? '<button class="popover-enter-btn popover-browse-btn" type="button" data-browse-building="' + interiorEntityId + '">Browse Scene</button>' : '')) +
      '</div>';

    var closeBtn = popoverEl.querySelector('[data-close-popover]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) { e.stopPropagation(); closePopover(); });
    }

    var enterBtn = popoverEl.querySelector('[data-enter-building]');
    if (enterBtn) {
      enterBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (typeof config.onFinishGuide === 'function') config.onFinishGuide();
        handleEnterBuilding(enterBtn.dataset.enterBuilding, entity);
      });
    }

    var browseBtn = popoverEl.querySelector('[data-browse-building]');
    if (browseBtn) {
      browseBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        handleBrowseBuilding(browseBtn.dataset.browseBuilding);
      });
    }

    var isSourceItem = options.sourceElement &&
      (options.sourceElement.classList.contains('building') || options.sourceElement.classList.contains('scene-item'));
    if (isSourceItem) {
      placePopover(options.sourceElement, popoverEl);
    } else {
      positionPopover(entity);
    }

    popoverEl.classList.add('visible');
    popoverTimer = null;

    if (typeof config.onAfterOpen === 'function') {
      config.onAfterOpen(interiorEntityId, entity);
    }

    if (!options.skipLog) logActivity(entity.name || '', 'Opened entity attributes popover.');
  }

  function openSceneItemPopover(sceneItem) {
    if (!sceneItem) return;
    closePopover();
    window.clearTimeout(popoverTimer);
    activeEntityId = null;

    var enterprise = inferEnterpriseType(sceneItem);
    var name = (sceneItem.dataset && (sceneItem.dataset.houseName || sceneItem.dataset.houseDisplayName || sceneItem.dataset.name)) ||
               sceneItem.id || 'Scene building';
    var src = (sceneItem.dataset && sceneItem.dataset.src) || 'None';
    var isHouse = Boolean(sceneItem.dataset && sceneItem.dataset.houseType);

    if (!popoverEl) { popoverEl = document.getElementById('entityPopover'); }
    if (!popoverEl) return;

    popoverEl.classList.remove('fading');

    var houseExtraHTML = isHouse ? (
      '<div class="popover-metric-row"><span>Wealth Class</span><span>' + (sceneItem.dataset.wealthLabel || 'Unrecognized') + '</span></div>' +
      '<div class="popover-metric-row"><span>Identity Type</span><span>' + (sceneItem.dataset.identityType || 'Household') + '</span></div>'
    ) : '<div class="popover-metric-row"><span>Building Type</span><span>Ordinary scene object</span></div>';

    popoverEl.innerHTML =
      '<div class="popover-head">' +
        '<div>' +
          '<div class="popover-label">' + (sceneItem.dataset.type || 'JSON ITEM') + '</div>' +
          '<div class="popover-name">' + name + '</div>' +
          '<div class="popover-type">Type: ' + (isHouse ? 'Household' : 'Scene building') + '<br>Status: Rendered per final JSON</div>' +
          '<div class="popover-auto">Click x to close</div>' +
        '</div>' +
        '<button class="icon-btn" type="button" aria-label="Close popover" data-close-popover>&times;</button>' +
      '</div>' +
      '<div class="popover-summary">This building comes from the city scene JSON. Texture, coordinates, and layer are rendered per configuration.</div>' +
      '<div class="popover-metrics">' +
        '<div class="popover-metric-row"><span>ID</span><span>' + (sceneItem.id || '') + '</span></div>' +
        '<div class="popover-metric-row"><span>Layer</span><span>' + (sceneItem.dataset.layer || 'Unlabeled') + '</span></div>' +
        '<div class="popover-metric-row"><span>Texture</span><span>' + src + '</span></div>' +
        houseExtraHTML +
      '</div>';

    var closeBtn = popoverEl.querySelector('[data-close-popover]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) { e.stopPropagation(); closePopover(); });
    }
    placePopover(sceneItem, popoverEl);
    popoverEl.classList.add('visible');
    popoverTimer = null;
    logActivity(name, 'Opened JSON building attributes popover.');
  }

  function openEnterprisePopover(sceneItem, enterprise) {
    if (!sceneItem || !enterprise) return;
    closePopover();
    window.clearTimeout(popoverTimer);
    activeEntityId = null;

    enterprise = enterprise || inferEnterpriseType(sceneItem);
    if (!enterprise) return;

    var enterpriseKind = enterprise.type === 'luxury' ? 'Luxury Firm' : 'Necessity Firm';
    var src = (sceneItem.dataset && sceneItem.dataset.src) || 'None';

    if (!popoverEl) { popoverEl = document.getElementById('entityPopover'); }
    if (!popoverEl) return;

    var enterpriseScene = ENTERPRISE_SCENE_MAP[enterprise.type];
    var enterpriseBrowsePage = enterpriseScene && enterpriseScene.browsePage;
    var enterpriseEntityId = 'enterprise-' + enterprise.type;
    var enterpriseTaskEnabled = isCurrentTaskTarget('labor-market') || isCurrentTaskTarget(enterpriseEntityId);
    var enterpriseTaskDisabled = enterpriseTaskEnabled ? '' : ' disabled';

    popoverEl.classList.remove('fading');
    popoverEl.innerHTML =
      '<div class="popover-head">' +
        '<div>' +
          '<div class="popover-label">Enterprise</div>' +
          '<div class="popover-name">Enterprise</div>' +
          '<div class="popover-type">Type: Enterprise<br>Status: Normal operation</div>' +
          '<div class="popover-auto">Click x to close</div>' +
        '</div>' +
        '<button class="icon-btn" type="button" aria-label="Close popover" data-close-popover>&times;</button>' +
      '</div>' +
      '<div class="popover-summary">This building belongs to an enterprise entity. It can serve as a workplace in employment tasks.</div>' +
      '<div class="popover-metrics">' +
        '<div class="popover-metric-row"><span>Enterprise Type</span><span>' + enterpriseKind + '</span></div>' +
        '<div class="popover-metric-row"><span>Building Name</span><span>' + ((sceneItem.dataset && sceneItem.dataset.name) || sceneItem.id || 'Enterprise') + '</span></div>' +
        '<div class="popover-metric-row"><span>Layer</span><span>' + (sceneItem.dataset.layer || 'Unlabeled') + '</span></div>' +
        '<div class="popover-metric-row"><span>Texture</span><span>' + src + '</span></div>' +
      '</div>' +
      '<div class="popover-actions">' +
        (enterpriseBrowsePage ? '<button class="popover-enter-btn popover-browse-btn" type="button" data-browse-enterprise="' + enterprise.type + '">Browse Scene</button>' : '') +
      '</div>';

    var closeBtn = popoverEl.querySelector('[data-close-popover]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) { e.stopPropagation(); closePopover(); });
    }
    var enterBtn = popoverEl.querySelector('[data-enter-enterprise]');
    if (enterBtn) {
      enterBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (typeof config.onFinishGuide === 'function') config.onFinishGuide();
        handleEnterpriseEnter(enterBtn.dataset.enterEnterprise);
      });
    }
    var browseEntBtn = popoverEl.querySelector('[data-browse-enterprise]');
    if (browseEntBtn) {
      browseEntBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        handleBrowseEnterprise(browseEntBtn.dataset.browseEnterprise);
      });
    }
    placePopover(sceneItem, popoverEl);
    popoverEl.classList.add('visible');
    popoverTimer = null;
    logActivity('Enterprise', 'Opened enterprise attributes popover.');
  }

  // ============================================================
  // 入口按钮逻辑 & 场景跳转（与旧版 enterInteriorScene 一致）
  // ============================================================

  function getCurrentTaskIdForInterior() {
    if (window.EWMTaskFlow) {
      var st = window.EWMTaskFlow.getState();
      if (st && st.current && st.current !== 'complete') return st.current;
    }
    try {
      var s = JSON.parse(sessionStorage.getItem('EWMInitialState') || 'null');
      return (s && s.player && s.player.initialTaskId) || '';
    } catch(e) { return ''; }
  }

  function resolveInteriorPage(scene, taskId) {
    if (!scene) return '';
    taskId = taskId || getCurrentTaskIdForInterior();
    return (scene.taskPages && scene.taskPages[taskId]) || scene.page || '';
  }

  function resolveBrowsePage(scene, taskId) {
    if (!scene) return '';
    taskId = taskId || getCurrentTaskIdForInterior();
    return (scene.browsePages && scene.browsePages[taskId]) || scene.browsePage || '';
  }

  function isCurrentTaskTarget(entityId) {
    if (!window.EWMTaskFlow) return false;
    var st = window.EWMTaskFlow.getState();
    if (!st || st.current === 'complete') return false;
    return st.targetEntityId === entityId;
  }

  function normalizeInteriorSpriteId(value) {
    if (!value) return '';
    var clean = String(value).trim().replace(/^\.?\//, '');
    var match = clean.match(/walk_\d+/);
    return match ? match[0] : '';
  }

  function deriveInteriorSpriteIdFromPlayer(player) {
    if (!player || typeof player !== 'object') return '';
    var explicit = normalizeInteriorSpriteId(
      player.spriteId || player.avatarId || player.characterId || player.personSprite || player.personId
    );
    if (explicit) return explicit;
    var wealthLevel = Number(player.wealthLevel || player.wealth_level || player.wealth || player.tier || player.level);
    var identityText = String([
      player.identity, player.group, player.role, player.roleName,
      player.identityType, player.employmentType, player.isEmployed,
      player.is_employed, player.isLaborForce, player.is_labor_force
    ].filter(function(v) { return v !== undefined && v !== null; }).join(' ')).toLowerCase();
    if (isFinite(wealthLevel)) {
      if (identityText.indexOf('nonlabor') !== -1 || identityText.indexOf('non-labor') !== -1 ||
          identityText.indexOf('non_labor') !== -1 || identityText.indexOf('非劳动力') !== -1) {
        return 'walk_' + Math.min(10, Math.max(6, wealthLevel + 5));
      }
      if (identityText.indexOf('labor') !== -1 || identityText.indexOf('劳动力') !== -1) {
        return 'walk_' + Math.min(5, Math.max(1, wealthLevel));
      }
      if (identityText.indexOf('true') !== -1 || identityText.indexOf('employed') !== -1) {
        return 'walk_' + Math.min(5, Math.max(1, wealthLevel));
      }
      return 'walk_' + Math.min(5, Math.max(1, wealthLevel));
    }
    return '';
  }

  function getInteriorSpriteId() {
    try {
      var s = JSON.parse(sessionStorage.getItem('EWMInitialState') || 'null');
      return deriveInteriorSpriteIdFromPlayer((s && s.player) || {});
    } catch(e) { return ''; }
  }

  function buildInteriorSceneUrl(page, spriteId) {
    var url = /^https?:\/\//.test(page) ? page : (config.interactionServerOrigin + '/' + page);
    var normalized = normalizeInteriorSpriteId(spriteId);
    if (!normalized) return url;
    return url + (url.indexOf('?') !== -1 ? '&' : '?') + 'sprite=' + encodeURIComponent(normalized);
  }

  function handleEnterpriseEnter(enterpriseType) {
    var scene = ENTERPRISE_SCENE_MAP[enterpriseType];
    if (!scene) {
      toastMessage('Unrecognized enterprise destination');
      return;
    }
    if (AVAILABLE_INTERIOR_PAGES.indexOf(scene.page) === -1) {
      toastMessage('Enterprise scene page missing');
      return;
    }
    var spriteId = getInteriorSpriteId();
    sessionStorage.setItem('EWMCurrentTask', 'employment');
    sessionStorage.setItem('EWMCurrentEnterpriseType', enterpriseType);
    sessionStorage.setItem('EWMCurrentEnterpriseName', 'Enterprise');
    sessionStorage.setItem('EWMCurrentInteriorScene', JSON.stringify({
      entityId: 'enterprise-' + enterpriseType,
      sceneId: scene.sceneId,
      label: 'Enterprise',
      taskId: 'labor_decision',
      enterpriseType: enterpriseType,
      page: scene.page,
      fromPage: 'main_map.html',
      spriteId: spriteId,
      mode: 'task',
      enteredAt: new Date().toISOString()
    }));
    logActivity('Employment Decision', 'Entered ' + scene.label + ' scene.');
    window.location.href = buildInteriorSceneUrl(scene.page, spriteId);
  }

  function handleEnterBuilding(entityId, entity) {
    if (isHouseEntity(entityId)) {
      entityId = 'house';
    }

    if (entityId === 'bank_01') entityId = 'bank-0';
    if (entityId === 'bank_02') entityId = 'bank-1';

    if (isFirmEntity(entityId)) {
      var firmData = firmAgentMap && firmAgentMap[entityId];
      var entType = firmData ? firmData.sector : (entityId.indexOf('luxury') !== -1 ? 'luxury' : 'necessity');
      handleEnterpriseEnter(entType);
      return;
    }

    if (entityId === 'enterprise-luxury' || entityId === 'enterprise-necessity') {
      var entType2 = entityId === 'enterprise-luxury' ? 'luxury' : 'necessity';
      handleEnterpriseEnter(entType2);
      return;
    }

    var scene = INTERIOR_SCENE_MAP[entityId];
    var taskId = getCurrentTaskIdForInterior();
    var page = resolveInteriorPage(scene, taskId);

    if (!scene) {
      toastMessage('Entry reserved');
      return;
    }
    if (AVAILABLE_INTERIOR_PAGES.indexOf(page) === -1) {
      toastMessage('Entry reserved');
      return;
    }

    if (typeof config.onEnterBuilding === 'function') {
      var result = config.onEnterBuilding(entityId, entity, page);
      if (result === false) return;
    }

    var spriteId = getInteriorSpriteId();
    sessionStorage.setItem('EWMCurrentInteriorScene', JSON.stringify({
      entityId: entityId,
      sceneId: scene.sceneId,
      label: scene.label,
      taskId: taskId,
      page: page,
      fromPage: 'main_map.html',
      spriteId: spriteId,
      mode: 'task',
      enteredAt: new Date().toISOString()
    }));
    logActivity(entity.name || '', 'Entering interior scene: ' + page);
    window.location.href = buildInteriorSceneUrl(page, spriteId);
  }

  function handleBrowseBuilding(entityId) {
    if (isHouseEntity(entityId)) {
      entityId = 'house';
    }
    if (entityId === 'bank_01') entityId = 'bank-0';
    if (entityId === 'bank_02') entityId = 'bank-1';

    if (isFirmEntity(entityId)) {
      var firmData = firmAgentMap && firmAgentMap[entityId];
      var entType = firmData ? firmData.sector : (entityId.indexOf('luxury') !== -1 ? 'luxury' : 'necessity');
      handleBrowseEnterprise(entType);
      return;
    }
    if (entityId === 'enterprise-luxury' || entityId === 'enterprise-necessity') {
      handleBrowseEnterprise(entityId === 'enterprise-luxury' ? 'luxury' : 'necessity');
      return;
    }

    var scene = INTERIOR_SCENE_MAP[entityId];
    var browsePage = resolveBrowsePage(scene);
    if (!scene || !browsePage) {
      toastMessage('Browse not available for this building');
      return;
    }
    if (AVAILABLE_INTERIOR_PAGES.indexOf(browsePage) === -1) {
      toastMessage('Browse scene page missing');
      return;
    }
    var spriteId = getInteriorSpriteId();
    logActivity(entityId, 'Browsing scene: ' + browsePage);
    window.location.href = buildInteriorSceneUrl(browsePage, spriteId);
  }

  function handleBrowseEnterprise(enterpriseType) {
    var scene = ENTERPRISE_SCENE_MAP[enterpriseType];
    if (!scene || !scene.browsePage) {
      toastMessage('Browse not available');
      return;
    }
    if (AVAILABLE_INTERIOR_PAGES.indexOf(scene.browsePage) === -1) {
      toastMessage('Browse scene page missing');
      return;
    }
    var spriteId = getInteriorSpriteId();
    logActivity('Enterprise', 'Browsing ' + scene.label + ' scene.');
    window.location.href = buildInteriorSceneUrl(scene.browsePage, spriteId);
  }

  // ============================================================
  // 场景物件点击分发
  // ============================================================
  function handleSceneItemClick(sceneItem) {
    if (!sceneItem) return;

    var buildingId = sceneItem.dataset.buildingId;
    var entityId = mapBuildingIdToEntityId(buildingId);

    if (isHouseEntity(entityId)) {
      openEntityPopover(entityId, { sourceElement: sceneItem });
      return;
    }

    if (isFirmEntity(entityId || buildingId)) {
      openEntityPopover(entityId || buildingId, { sourceElement: sceneItem });
      return;
    }

    var enterprise = inferEnterpriseType(sceneItem);
    if (enterprise) {
      openEnterprisePopover(sceneItem, enterprise);
      return;
    }

    if (isBankEntity(buildingId)) {
      openEntityPopover(buildingId, { sourceElement: sceneItem });
      return;
    }

    if (entityId && getEntity(entityId)) {
      openEntityPopover(entityId, { sourceElement: sceneItem });
      return;
    }

    openSceneItemPopover(sceneItem);
  }

  // ============================================================
  // 辅助
  // ============================================================
  function logActivity(source, text) {
    if (typeof config.onActivityLog === 'function') {
      config.onActivityLog(source, text);
    }
  }

  function toastMessage(msg) {
    if (typeof config.onShowToast === 'function') {
      config.onShowToast(msg);
    }
    logActivity('Hint', msg);
  }

  // ============================================================
  // 全局键盘 & 点击外部关闭
  // ============================================================
  function onDocumentClick(e) {
    if (!popoverEl || !popoverEl.classList.contains('visible')) return;
    if (popoverEl.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.building, .scene-item, [data-building-id]')) return;
    closePopover();
  }

  function onDocumentKeydown(e) {
    if (e.key === 'Escape' && popoverEl && popoverEl.classList.contains('visible')) {
      closePopover();
    }
  }

  // ============================================================
  // 动态数据更新 (对应旧版 updateWorldState)
  // ============================================================
  function deepMerge(target, source) {
    var keys = Object.keys(source || {});
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var next = source[key];
      if (next && typeof next === 'object' && !Array.isArray(next)) {
        target[key] = target[key] || {};
        deepMerge(target[key], next);
      } else {
        target[key] = next;
      }
    }
    return target;
  }

  function updateWorldState(data) {
    if (!data || typeof data !== 'object') return;

    if (Array.isArray(data.entities)) {
      for (var i = 0; i < data.entities.length; i++) {
        var incoming = data.entities[i];
        var existing = getEntity(incoming.id);
        if (existing) {
          if (incoming.metrics) existing.metrics = incoming.metrics;
          if (incoming.actions) existing.actions = incoming.actions;
          if (incoming.summary) existing.summary = incoming.summary;
          if (incoming.name) existing.name = incoming.name;
        } else {
          ENTITIES.push(incoming);
        }
      }
    }

    if (data.environment || data.worldStats) {
      config.worldStats = config.worldStats || {};
      deepMerge(config.worldStats, data.environment || data.worldStats || {});
    }

    if (data.player) {
      config.player = config.player || {};
      deepMerge(config.player, data.player);
    }

    if (activeEntityId && popoverEl && popoverEl.classList.contains('visible')) {
      openEntityPopover(activeEntityId, { skipLog: true });
    }

    logActivity('Backend API', 'updateWorldState refreshed economic entity data.');
  }

  // ============================================================
  // PUBLIC API
  // ============================================================
  global.EWMPopover = {
    init: function (opts) {
      opts = opts || {};
      popoverEl = opts.popoverEl || document.getElementById(opts.popoverId || 'entityPopover');
      sceneEl   = opts.sceneEl   || document.getElementById(opts.sceneId || 'scene');
      sceneLayoutLayers = Array.isArray(opts.layers) ? opts.layers : [];

      if (opts.config) {
        var keys = Object.keys(opts.config);
        for (var i = 0; i < keys.length; i++) {
          if (config.hasOwnProperty(keys[i])) {
            config[keys[i]] = opts.config[keys[i]];
          }
        }
      }

      document.removeEventListener('click', onDocumentClick);
      document.removeEventListener('keydown', onDocumentKeydown);
      document.addEventListener('click', onDocumentClick);
      document.addEventListener('keydown', onDocumentKeydown);

      if (!houseAgentMap) {
        houseAgentMap = {};
        firmAgentMap = {};
        var xhr = new XMLHttpRequest();
        xhr.open('GET', 'modules/popover/house_agent_map.json', true);
        xhr.onload = function () {
          if (xhr.status === 200) {
            try {
              var data = JSON.parse(xhr.responseText);
              houseAgentMap = data.houses || data;
              firmAgentMap = data.firms || null;
              bankAgentMap = data.banks || null;
              centralBankData = data.centralBank || null;
              governmentData = data.government || null;
              supermarketData = data.supermarket || null;
              laborMarketData = data.laborMarket || null;
              stockMarketData = data.stockMarket || null;
            } catch(e) {}
          }
        };
        xhr.send();
      }
    },

    open: openEntityPopover,
    openForTask: function(entityId) { openEntityPopover(entityId, { fromTask: true }); },
    close: closePopover,
    handleClick: handleSceneItemClick,
    updateWorldState: updateWorldState,
    registerBuildingElement: registerBuildingElement,
    syncEntitySelection: syncEntitySelection,
    getActiveEntityId: function () { return activeEntityId; },
    isOpen: function () { return popoverEl ? popoverEl.classList.contains('visible') : false; },
    setLayers: function (layers) { sceneLayoutLayers = Array.isArray(layers) ? layers : []; },
    config: config,

    mapBuildingIdToEntityId: mapBuildingIdToEntityId,
    getEntity: getEntity,
    findSceneItemByEntityId: findSceneItemByEntityId,
    inferEnterpriseType: inferEnterpriseType,
    enterEnterprise: function(type) { isTaskTriggered = true; handleEnterpriseEnter(type); },
    BUILDING_NAMES: BUILDING_NAMES,
    ENTITIES: ENTITIES,

    loadHouseAgentMap: function (url) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url || 'modules/popover/house_agent_map.json', true);
      xhr.onload = function () {
        if (xhr.status === 200) {
          try {
            var data = JSON.parse(xhr.responseText);
            houseAgentMap = data.houses || data;
            firmAgentMap = data.firms || null;
            bankAgentMap = data.banks || null;
            centralBankData = data.centralBank || null;
            governmentData = data.government || null;
            supermarketData = data.supermarket || null;
            laborMarketData = data.laborMarket || null;
            stockMarketData = data.stockMarket || null;
          } catch(e) {
            console.warn('[EWMPopover] Failed to parse agent map', e);
          }
        }
      };
      xhr.onerror = function () {
        console.warn('[EWMPopover] Failed to load agent map from ' + url);
      };
      xhr.send();
    },

    setHouseAgentData: function (data) {
      if (data && data.houses) {
        houseAgentMap = data.houses;
        firmAgentMap = data.firms || null;
        bankAgentMap = data.banks || null;
        centralBankData = data.centralBank || null;
        governmentData = data.government || null;
        supermarketData = data.supermarket || null;
        laborMarketData = data.laborMarket || null;
        stockMarketData = data.stockMarket || null;
      } else {
        houseAgentMap = data;
      }
    }
  };

})(window);
