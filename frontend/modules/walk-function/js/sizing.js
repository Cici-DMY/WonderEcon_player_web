/*
 * sizing.js — 人物 / 光圈 / 标签 尺寸
 * 数值取自 player_world_city_ui.html 的 CSS
 * (.player-avatar-on-map / ::before / .player-avatar-label)，保持与主地图一致。
 * 调用 applySizing(avatarEl) 把这些尺寸写到行走头像 DOM 上。
 */
(function (global) {
  "use strict";

  const SIZING = {
    person: {           // 行走头像：img 按自然尺寸(512×512)，再 scale(0.22) → 约 113px
      scale: 0.22,
      transform: "translate(-50%, -100%) translateY(40px) scale(0.22)",
      transformOrigin: "50% 100%",
      zIndex: 20000,
      dropShadow: "drop-shadow(0 18px 18px rgba(24,62,92,.34))"
    },
    aura: {             // 光圈（原版数值，scale(0.22)后约48px宽）
      width: 220,
      height: 70,
      bottom: -8,
      border: "10px solid rgba(47,128,237,.72)",
      borderRadius: 999,
      background: "rgba(255,255,255,.28)",
      boxShadow: "0 0 22px rgba(47,128,237,.42)"
    },
    label: {            // 标签（原版数值，scale(0.22)后约14px）
      text: "player",
      fontSize: 64,
      fontWeight: 900,
      padding: "12px 28px",
      borderRadius: 999,
      background: "rgba(255,255,255,.88)",
      color: "#165fbd",
      bottom: 10,
      boxShadow: "0 8px 18px rgba(31,92,147,.22)",
      zIndex: 4
    }
  };

  // 注入光圈(::before)与标签的尺寸样式（按主地图数值）。
  function ensureSizingStyle() {
    if (document.getElementById("ewm-walk-sizing-style")) return;
    const s = SIZING;
    const style = document.createElement("style");
    style.id = "ewm-walk-sizing-style";
    style.textContent = `
.ewm-walk-avatar{z-index:${s.person.zIndex};
  transform:${s.person.transform};transform-origin:${s.person.transformOrigin};
  filter:${s.person.dropShadow};position:absolute;pointer-events:none;}
.ewm-walk-avatar img{display:block;width:auto;height:auto;}
.ewm-walk-avatar::before{content:"";position:absolute;left:50%;bottom:${s.aura.bottom}px;
  width:${s.aura.width}px;height:${s.aura.height}px;border:${s.aura.border};
  border-radius:${s.aura.borderRadius}px;background:${s.aura.background};
  transform:translateX(-50%);box-shadow:${s.aura.boxShadow};}
.ewm-walk-avatar .ewm-walk-label{position:absolute;left:50%;bottom:${s.label.bottom}px;z-index:${s.label.zIndex};
  padding:${s.label.padding};border-radius:${s.label.borderRadius}px;background:${s.label.background};
  color:${s.label.color};font-size:${s.label.fontSize}px;font-weight:${s.label.fontWeight};
  transform:translateX(-50%);box-shadow:${s.label.boxShadow};white-space:nowrap;}`;
    document.head.appendChild(style);
  }

  /** 给一个头像 DOM 套上行走尺寸（class + 标签）。labelText 可改标签文字。 */
  function applySizing(avatarEl, labelText) {
    if (!avatarEl) return avatarEl;
    ensureSizingStyle();
    avatarEl.classList.add("ewm-walk-avatar");
    let label = avatarEl.querySelector(".ewm-walk-label");
    if (!label) {
      label = document.createElement("span");
      label.className = "ewm-walk-label";
      avatarEl.appendChild(label);
    }
    label.textContent = labelText || SIZING.label.text;
    return avatarEl;
  }

  global.EWMSizing = { SIZING, applySizing, ensureSizingStyle };
})(typeof window !== "undefined" ? window : globalThis);
