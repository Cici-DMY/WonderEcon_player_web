/*
 * matcher.js — Person + task route -> route file matching
 * Only needs [personId] and [taskRoute (from-to / segment)] to resolve routes/*.json path.
 *
 * Specific matching rules (who walks which route) are maintained in these two tables, no other code changes needed:
 *   - PERSON_ATTRIBUTE_MAP: personId -> { wealthTier:1..5, labor:true|false }
 *   - RULES:               Advanced override rules array (returns on first match, highest priority)
 *
 * Resolution chain: personId -> attributes -> routeGroup
 *         -> segment(`${from}-${to}`) -> routeFile(`routes/${group}/${group} ${segment}.json`)
 */
(function (global) {
  "use strict";

  // ====== Maintenance section: define “who walks which tier route” here ======================
  // 键 = 人物ID；值 = 财富档(1..5) 与是否劳动力。现给示例，后续按需补全。
  const PERSON_ATTRIBUTE_MAP = {
    "walk_1": { wealthTier: 1, labor: true },
    "walk_2": { wealthTier: 1, labor: false }
  };

  // 取不到人物属性时的兜底。
  const DEFAULT_PERSON = { wealthTier: 1, labor: true };

  // 高级覆盖规则：按顺序匹配，命中即用。when 返回 true 则使用 use。
  // use 可给 { group } 或 { routeFile }。示例留空。
  // 例：{ when: ctx => ctx.taskRoute.taskId === "special", use: { routeFile: "routes/xxx/xxx 1-2.json" } }
  const RULES = [];
  // ================================================================

  // 全部可用路线索引（与 routes/ 目录实际文件保持一致）。
  const ROUTES_INDEX = {
    "tier1_wealth_labor":    ["1-2", "2-3", "3-4", "4-5", "5-6", "6-7"],
    "tier1_wealth_nonlabor": ["1-2", "2-3", "3-4"],
    "tier2_wealth_labor":    ["1-2", "2-3", "3-4", "4-5", "5-6", "6-7"],
    "tier2_wealth_nonlabor": ["1-2", "2-3", "3-4"],
    "tier3_wealth_labor":    ["1-2", "2-3", "3-4", "4-5", "5-6"],
    "tier3_wealth_nonlabor": ["1-2", "2-3", "3-4"],
    "tier4_wealth_labor":    ["1-2", "2-3", "3-4", "4-5", "5-6"],
    "tier4_wealth_nonlabor": ["1-2", "2-3", "3-4"],
    "tier5_wealth_labor":    ["1-2", "2-3", "3-4", "4-5", "5-6"],
    "tier5_wealth_nonlabor": ["1-2", "2-3", "3-4"]
  };

  function getRouteBaseDir() {
    return (global.EWMWalkConfig && global.EWMWalkConfig.routeBasePath) || "routes";
  }

  function personToAttributes(personId) {
    return PERSON_ATTRIBUTE_MAP[personId] || DEFAULT_PERSON;
  }

  function attributesToGroup(attr) {
    const tier = attr.wealthTier || 1;
    const laborText = attr.labor ? "labor" : "nonlabor";
    return `tier${tier}_wealth_${laborText}`;
  }

  function taskToSegment(taskRoute) {
    if (!taskRoute) return null;
    if (taskRoute.segment) return String(taskRoute.segment);
    if (taskRoute.from != null && taskRoute.to != null) {
      return `${taskRoute.from}-${taskRoute.to}`;
    }
    return null;
  }

  function composeRouteFile(group, segment) {
    return `${getRouteBaseDir().replace(/\/+$/, "")}/${group}/${group} ${segment}.json`;
  }

  function segmentExists(group, segment) {
    return Array.isArray(ROUTES_INDEX[group]) && ROUTES_INDEX[group].includes(segment);
  }

  /**
   * 主入口：给人物ID + 任务路线，解析出路线文件与分组。
   * @returns { applied, personId, attributes, group, segment, routeFile, reason }
   */
  function matchRoute(personId, taskRoute) {
    const ctx = { personId, taskRoute, attributes: personToAttributes(personId) };

    // 1) 高级规则优先
    for (const rule of RULES) {
      try {
        if (rule.when && rule.when(ctx)) {
          if (rule.use?.routeFile) {
            return { applied: true, personId, attributes: ctx.attributes,
              group: null, segment: taskToSegment(taskRoute), routeFile: rule.use.routeFile, reason: "rule" };
          }
          if (rule.use?.group) {
            const seg = taskToSegment(taskRoute);
            if (seg && segmentExists(rule.use.group, seg)) {
              return { applied: true, personId, attributes: ctx.attributes,
                group: rule.use.group, segment: seg, routeFile: composeRouteFile(rule.use.group, seg), reason: "rule" };
            }
          }
        }
      } catch (e) { console.warn("[matcher] 规则执行出错", e); }
    }

    // 2) 默认推导
    const group = attributesToGroup(ctx.attributes);
    const segment = taskToSegment(taskRoute);
    if (!segment) {
      return { applied: false, personId, attributes: ctx.attributes, group, segment: null, routeFile: null, reason: "missing task segment (from-to/segment)" };
    }
    if (!segmentExists(group, segment)) {
      return { applied: false, personId, attributes: ctx.attributes, group, segment, routeFile: null, reason: `route index has no ${group} ${segment}` };
    }
    return { applied: true, personId, attributes: ctx.attributes, group, segment, routeFile: composeRouteFile(group, segment), reason: "derived" };
  }

  global.EWMMatcher = {
    matchRoute,
    // 维护表外露，便于运行时动态补充
    PERSON_ATTRIBUTE_MAP,
    DEFAULT_PERSON,
    RULES,
    ROUTES_INDEX,
    helpers: { personToAttributes, attributesToGroup, taskToSegment, composeRouteFile, segmentExists }
  };
})(typeof window !== "undefined" ? window : globalThis);
