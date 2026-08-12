/**
 * 读取 city_layout.json + households.json + firms.json + banks.json，生成房屋/企业/银行→Agent 映射 JSON。
 * 用法: node build_house_agent_map.js
 * 输出: house_agent_map.json (包含 houses + firms + banks 三个分区)
 */
const fs = require('fs');
const path = require('path');

const LAYOUT_PATH = path.join(__dirname, '..', '..', 'city_layout.json');
const HOUSEHOLDS_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'households.json');
const FIRMS_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'firms.json');
const BANKS_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'banks.json');
const CENTRAL_BANK_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'central_bank.json');
const GOVERNMENT_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'government.json');
const INFO_ENV_PATH = path.join(__dirname, '..', 'interaction', 'code', 'results', 'information_environment.json');
const OUTPUT_PATH = path.join(__dirname, 'house_agent_map.json');

// 银行 buildingId → agentId
const BANK_AGENT_MAP = { 'bank_01': 0, 'bank_02': 1 };

const WEALTH_LAYERS = {
  'layer-6':  { level: 5, labor: ['house09'],              nonlabor: ['house_1_1', 'house_1_2'] },
  'layer-7':  { level: 4, labor: ['house07'],              nonlabor: ['house04'] },
  'layer-10': { level: 3, labor: ['house05'],              nonlabor: ['house06'] },
  'layer-9':  { level: 2, labor: ['house02'],              nonlabor: ['house03'] },
  'layer-11': { level: 1, labor: ['house01'],              nonlabor: ['house10'] },
};

// agent ID 区间
const AGENT_RANGES = {
  labor:    { 5: [0, 19],   4: [20, 39],  3: [40, 59],  2: [60, 79],  1: [80, 99] },
  nonlabor: { 5: [100, 107], 4: [108, 115], 3: [116, 123], 2: [124, 131], 1: [132, 139] },
};

// 企业 mapping: name → buildingId (与 main_map.html loadScene 完全一致)
const FIRM_BUILDING_NAMES = {
  'necessity_1': 'necessity_01', 'necessity_2': 'necessity_02', 'necessity_3': 'necessity_03',
  'necessity_4': 'necessity_04', 'necessity_5': 'necessity_05', 'necessity_7': 'necessity_07',
  'necessity_8': 'necessity_08', 'necessity_9': 'necessity_09', 'necessity_10': 'necessity_10',
  'luxury_shop_1': 'luxury_01', 'luxury_shop_2': 'luxury_02',
};

function getHouseType(src, layerId) {
  const wl = WEALTH_LAYERS[layerId];
  if (!wl || !src) return null;
  if (layerId === 'layer-6') {
    if (src.indexOf('house_1_1') !== -1 || src.indexOf('house_1_2') !== -1) return 'nonlabor';
    if (src.indexOf('house09') !== -1) return 'labor';
  } else {
    for (const p of wl.labor)   { if (src.indexOf(p) !== -1) return 'labor'; }
    for (const p of wl.nonlabor) { if (src.indexOf(p) !== -1) return 'nonlabor'; }
  }
  return null;
}

// ---------- 读取 JSON ----------
const layout = JSON.parse(fs.readFileSync(LAYOUT_PATH, 'utf8'));
const layoutItems = layout.items || layout;
const households = JSON.parse(fs.readFileSync(HOUSEHOLDS_PATH, 'utf8'));
const agents = households.agents || households;
const firmsData = JSON.parse(fs.readFileSync(FIRMS_PATH, 'utf8'));
const firmInit = firmsData.initialization || {};
const firmAgents = firmsData.agents || firmsData;

// ---------- 处理所有 item，按 zIndex 排序 ----------
const entries = Object.keys(layoutItems).map(id => ({ id, info: layoutItems[id] }));
entries.sort((a, b) => (parseInt(a.info.zIndex) || 10) - (parseInt(b.info.zIndex) || 10));

// ======================== 房屋处理 ========================
const houseCounters = {};
const houseList = [];

entries.forEach(({ id, info }) => {
  if (!info.src || info.src.indexOf('house') === -1) return;
  const layerId = info.layer || 'layer-1';
  const houseType = getHouseType(info.src, layerId);
  if (!houseType) return;

  const wl = WEALTH_LAYERS[layerId];
  if (!wl) return;

  const groupKey = wl.level + '_' + houseType;
  if (!houseCounters[groupKey]) houseCounters[groupKey] = 0;
  houseCounters[groupKey]++;
  const num = String(houseCounters[groupKey]).padStart(2, '0');
  const buildingId = 'house_' + wl.level + '_' + houseType + '_' + num;

  houseList.push({
    buildingId: buildingId,
    wealthLevel: wl.level,
    houseType: houseType,
    groupKey: groupKey,
    index: houseCounters[groupKey],
  });
});

function getHouseAgentId(wealthLevel, houseType, index) {
  const range = AGENT_RANGES[houseType][wealthLevel];
  if (!range) throw new Error('No agent range for ' + houseType + ' wealth ' + wealthLevel);
  const agentId = range[0] + index - 1;
  if (agentId > range[1]) throw new Error('Agent index out of range: ' + houseType + ' W' + wealthLevel + ' #' + index);
  return agentId;
}

function buildHouseEntry(agentRecords, buildingId, houseType, wealthLevel) {
  const tick0 = agentRecords.find(r => r.tick === 0) ||
                (Array.isArray(agentRecords) ? agentRecords[0] : null);
  const init = (tick0 && tick0.tick_start) || {};

  const wealthByTick = {};
  for (let t = 0; t <= 12; t++) {
    const rec = (Array.isArray(agentRecords) ? agentRecords : [agentRecords])
      .find(r => r.tick === t);
    if (!rec) continue;
    let wealthVal = rec.tick_start ? rec.tick_start.wealth_level : null;
    const events = rec.events || [];
    for (const ev of events) {
      if (ev.fields && ev.fields.wealth_level && ev.fields.wealth_level.after !== undefined) {
        wealthVal = ev.fields.wealth_level.after;
        break;
      }
    }
    wealthByTick[String(t)] = wealthVal;
  }

  return {
    agentId: null, // filled below
    riskPreference: init.risk_preference || null,
    beta: init.beta || null,
    isLaborForce: init.is_labor_force != null ? init.is_labor_force : (houseType === 'labor'),
    identityType: houseType === 'labor' ? 'Labor Force' : 'Non-Labor Force',
    initialWealthLevel: init.initial_wealth_level || init.wealth_level || wealthLevel,
    wealthByTick: wealthByTick,
  };
}

const houseAgentMap = {};
houseList.forEach(h => {
  const agentId = getHouseAgentId(h.wealthLevel, h.houseType, h.index);
  const agentRecords = agents[String(agentId)];
  if (!agentRecords) {
    console.warn('Missing agent records for agent ' + agentId);
    return;
  }
  const entry = buildHouseEntry(agentRecords, h.buildingId, h.houseType, h.wealthLevel);
  entry.agentId = agentId;
  houseAgentMap[h.buildingId] = entry;
});

// ======================== 企业处理 ========================
const firmNameCounters = {};
const firmList = [];  // { buildingId, sector, index }

entries.forEach(({ id, info }) => {
  if (!FIRM_BUILDING_NAMES[info.name]) return;
  const sector = info.name.indexOf('luxury') !== -1 ? 'luxury' : 'necessity';

  if (!firmNameCounters[info.name]) firmNameCounters[info.name] = 0;
  firmNameCounters[info.name]++;

  let buildingId;
  if (info.name === 'necessity_3' && firmNameCounters[info.name] === 2) {
    buildingId = 'necessity_06';
  } else {
    buildingId = FIRM_BUILDING_NAMES[info.name];
  }

  if (!buildingId) return;

  firmList.push({ buildingId, sector });
});

// 按 sector 分别分配 agent ID: necessity → 0-9, luxury → 10-11
const sectorCounters = { necessity: 0, luxury: 0 };
const firmAgentMap = {};

firmList.forEach(f => {
  const idx = sectorCounters[f.sector]++;
  const agentId = f.sector === 'necessity' ? idx : (10 + idx);

  const initInfo = firmInit[String(agentId)] || {};
  const agentRecords = firmAgents[String(agentId)];

  // per-tick scale_level
  const scaleByTick = {};
  if (agentRecords) {
    for (let t = 0; t <= 12; t++) {
      const rec = (Array.isArray(agentRecords) ? agentRecords : [agentRecords])
        .find(r => r.tick === t);
      if (!rec) continue;
      let scaleVal = rec.tick_start ? rec.tick_start.scale_level : null;
      const events = rec.events || [];
      for (const ev of events) {
        if (ev.fields && ev.fields.scale_level && ev.fields.scale_level.after !== undefined) {
          scaleVal = ev.fields.scale_level.after;
          break;
        }
      }
      scaleByTick[String(t)] = scaleVal != null ? scaleVal : initInfo.scale_level;
    }
  }

  // 如果没有任何 tick 数据，用初始化值填充
  if (Object.keys(scaleByTick).length === 0) {
    for (let t = 0; t <= 12; t++) {
      scaleByTick[String(t)] = initInfo.scale_level;
    }
  }

  firmAgentMap[f.buildingId] = {
    agentId: agentId,
    sector: f.sector,
    isListed: initInfo.is_listed || false,
    riskPreference: initInfo.risk_preference || null,
    beta: initInfo.beta || null,
    initialScaleLevel: initInfo.scale_level || initInfo.initial_scale_level || null,
    scaleByTick: scaleByTick,
  };
});

// ======================== 银行处理 ========================
const banksData = JSON.parse(fs.readFileSync(BANKS_PATH, 'utf8'));
const bankInit = banksData.initialization || {};
const bankAgents = banksData.agents || banksData;

const bankAgentMap = {};
Object.keys(BANK_AGENT_MAP).forEach(buildingId => {
  const agentId = BANK_AGENT_MAP[buildingId];
  const initInfo = bankInit[String(agentId)] || {};
  const agentRecords = bankAgents[String(agentId)];

  const scaleByTick = {};
  if (agentRecords) {
    for (let t = 0; t <= 12; t++) {
      const rec = (Array.isArray(agentRecords) ? agentRecords : [agentRecords])
        .find(r => r.tick === t);
      if (!rec) continue;
      let scaleVal = rec.tick_start ? rec.tick_start.relative_scale : null;
      const events = rec.events || [];
      for (const ev of events) {
        if (ev.fields && ev.fields.relative_scale && ev.fields.relative_scale.after !== undefined) {
          scaleVal = ev.fields.relative_scale.after;
          break;
        }
      }
      scaleByTick[String(t)] = scaleVal || initInfo.relative_scale || null;
    }
  }

  bankAgentMap[buildingId] = {
    agentId: agentId,
    riskPreference: initInfo.risk_preference || null,
    relativeScaleByTick: scaleByTick,
  };
});

// ======================== 环境实体 ========================
function extractTickEnd(ticks, fieldPaths) {
  const result = {};
  ticks.forEach(t => {
    const d = {};
    const src = t.tick_end || t.tick_start || {};
    for (const [key, field] of Object.entries(fieldPaths)) {
      d[key] = src[field];
    }
    result[String(t.tick)] = d;
  });
  return result;
}

// --- central bank ---
const centralBankRaw = JSON.parse(fs.readFileSync(CENTRAL_BANK_PATH, 'utf8'));
const centralBankTicks = centralBankRaw.ticks || [];

const centralBankData = {
  byTick: extractTickEnd(centralBankTicks, {
    deposit_1yr: 'deposit_1yr',
    loan_1yr: 'loan_1yr',
    loan_5yr_plus: 'loan_5yr_plus',
    last_injected: 'last_injected',
    last_injection_pct: 'last_injection_pct',
  }),
};

// --- government ---
const governmentRaw = JSON.parse(fs.readFileSync(GOVERNMENT_PATH, 'utf8'));
const governmentTicks = governmentRaw.ticks || [];

const governmentData = {
  byTick: extractTickEnd(governmentTicks, {
    personal_income_tax_rate: 'personal_income_tax_rate',
    corporate_income_tax_rate: 'corporate_income_tax_rate',
    corporate_vat_rate: 'corporate_vat_rate',
    current_total_tax: 'current_total_tax',
    last_distribution_pct: 'last_distribution_pct',
  }),
};

// --- information environment → supermarket / laborMarket / stockMarket ---
const infoEnvRaw = JSON.parse(fs.readFileSync(INFO_ENV_PATH, 'utf8'));
const infoTicks = infoEnvRaw.ticks || [];

const supermarketData = {
  byTick: extractTickEnd(infoTicks, {
    last_avg_taxed_goods_price_necessity: 'last_avg_taxed_goods_price_necessity',
    last_avg_taxed_goods_price_luxury: 'last_avg_taxed_goods_price_luxury',
    last_avg_household_consumption_qty_necessity: 'last_avg_household_consumption_qty_necessity',
    last_avg_household_consumption_qty_luxury: 'last_avg_household_consumption_qty_luxury',
  }),
};

const laborMarketData = {
  byTick: extractTickEnd(infoTicks, {
    last_employment_rate: 'last_employment_rate',
    last_avg_household_wage: 'last_avg_household_wage',
    last_avg_firm_employment: 'last_avg_firm_employment',
  }),
};

const stockMarketData = {
  byTick: extractTickEnd(infoTicks, {
    current_stock_price_necessity: 'current_stock_price_necessity',
    current_stock_volume_necessity: 'current_stock_volume_necessity',
    current_stock_price_luxury: 'current_stock_price_luxury',
    current_stock_volume_luxury: 'current_stock_volume_luxury',
  }),
};

// 补充: mortgage_rate → centralBank
infoTicks.forEach(t => {
  const ts = String(t.tick);
  const te = t.tick_end || {};
  if (centralBankData.byTick[ts]) {
    centralBankData.byTick[ts].mortgage_rate = te.current_mortgage_rate;
  }
});

// ---------- 输出 ----------
const output = {
  houses: houseAgentMap,
  firms: firmAgentMap,
  banks: bankAgentMap,
  centralBank: centralBankData,
  government: governmentData,
  supermarket: supermarketData,
  laborMarket: laborMarketData,
  stockMarket: stockMarketData,
};

console.log('Houses: ' + Object.keys(houseAgentMap).length);
console.log('Firms: ' + Object.keys(firmAgentMap).length);
console.log('Banks: ' + Object.keys(bankAgentMap).length);
console.log('Central Bank ticks: ' + Object.keys(centralBankData.byTick).length);
console.log('Government ticks: ' + Object.keys(governmentData.byTick).length);
console.log('Supermarket ticks: ' + Object.keys(supermarketData.byTick).length);
console.log('Labor Market ticks: ' + Object.keys(laborMarketData.byTick).length);
console.log('Stock Market ticks: ' + Object.keys(stockMarketData.byTick).length);

fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2), 'utf8');
console.log('Output: ' + OUTPUT_PATH);
