var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __decorateClass = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc(target, key) : target;
  for (var i6 = decorators.length - 1, decorator; i6 >= 0; i6--)
    if (decorator = decorators[i6])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp(target, key, result);
  return result;
};

// node_modules/@lit/reactive-element/css-tag.js
var t = globalThis;
var e = t.ShadowRoot && (void 0 === t.ShadyCSS || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
var s = Symbol();
var o = /* @__PURE__ */ new WeakMap();
var n = class {
  constructor(t6, e6, o7) {
    if (this._$cssResult$ = true, o7 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t6, this.t = e6;
  }
  get styleSheet() {
    let t6 = this.o;
    const s5 = this.t;
    if (e && void 0 === t6) {
      const e6 = void 0 !== s5 && 1 === s5.length;
      e6 && (t6 = o.get(s5)), void 0 === t6 && ((this.o = t6 = new CSSStyleSheet()).replaceSync(this.cssText), e6 && o.set(s5, t6));
    }
    return t6;
  }
  toString() {
    return this.cssText;
  }
};
var r = (t6) => new n("string" == typeof t6 ? t6 : t6 + "", void 0, s);
var S = (s5, o7) => {
  if (e) s5.adoptedStyleSheets = o7.map(((t6) => t6 instanceof CSSStyleSheet ? t6 : t6.styleSheet));
  else for (const e6 of o7) {
    const o8 = document.createElement("style"), n5 = t.litNonce;
    void 0 !== n5 && o8.setAttribute("nonce", n5), o8.textContent = e6.cssText, s5.appendChild(o8);
  }
};
var c = e ? (t6) => t6 : (t6) => t6 instanceof CSSStyleSheet ? ((t7) => {
  let e6 = "";
  for (const s5 of t7.cssRules) e6 += s5.cssText;
  return r(e6);
})(t6) : t6;

// node_modules/@lit/reactive-element/reactive-element.js
var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
var a = globalThis;
var c2 = a.trustedTypes;
var l = c2 ? c2.emptyScript : "";
var p = a.reactiveElementPolyfillSupport;
var d = (t6, s5) => t6;
var u = { toAttribute(t6, s5) {
  switch (s5) {
    case Boolean:
      t6 = t6 ? l : null;
      break;
    case Object:
    case Array:
      t6 = null == t6 ? t6 : JSON.stringify(t6);
  }
  return t6;
}, fromAttribute(t6, s5) {
  let i6 = t6;
  switch (s5) {
    case Boolean:
      i6 = null !== t6;
      break;
    case Number:
      i6 = null === t6 ? null : Number(t6);
      break;
    case Object:
    case Array:
      try {
        i6 = JSON.parse(t6);
      } catch (t7) {
        i6 = null;
      }
  }
  return i6;
} };
var f = (t6, s5) => !i2(t6, s5);
var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
Symbol.metadata ??= Symbol("metadata"), a.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var y = class extends HTMLElement {
  static addInitializer(t6) {
    this._$Ei(), (this.l ??= []).push(t6);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t6, s5 = b) {
    if (s5.state && (s5.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t6) && ((s5 = Object.create(s5)).wrapped = true), this.elementProperties.set(t6, s5), !s5.noAccessor) {
      const i6 = Symbol(), h3 = this.getPropertyDescriptor(t6, i6, s5);
      void 0 !== h3 && e2(this.prototype, t6, h3);
    }
  }
  static getPropertyDescriptor(t6, s5, i6) {
    const { get: e6, set: r6 } = h(this.prototype, t6) ?? { get() {
      return this[s5];
    }, set(t7) {
      this[s5] = t7;
    } };
    return { get: e6, set(s6) {
      const h3 = e6?.call(this);
      r6?.call(this, s6), this.requestUpdate(t6, h3, i6);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t6) {
    return this.elementProperties.get(t6) ?? b;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d("elementProperties"))) return;
    const t6 = n2(this);
    t6.finalize(), void 0 !== t6.l && (this.l = [...t6.l]), this.elementProperties = new Map(t6.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
      const t7 = this.properties, s5 = [...r2(t7), ...o2(t7)];
      for (const i6 of s5) this.createProperty(i6, t7[i6]);
    }
    const t6 = this[Symbol.metadata];
    if (null !== t6) {
      const s5 = litPropertyMetadata.get(t6);
      if (void 0 !== s5) for (const [t7, i6] of s5) this.elementProperties.set(t7, i6);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t7, s5] of this.elementProperties) {
      const i6 = this._$Eu(t7, s5);
      void 0 !== i6 && this._$Eh.set(i6, t7);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s5) {
    const i6 = [];
    if (Array.isArray(s5)) {
      const e6 = new Set(s5.flat(1 / 0).reverse());
      for (const s6 of e6) i6.unshift(c(s6));
    } else void 0 !== s5 && i6.push(c(s5));
    return i6;
  }
  static _$Eu(t6, s5) {
    const i6 = s5.attribute;
    return false === i6 ? void 0 : "string" == typeof i6 ? i6 : "string" == typeof t6 ? t6.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise(((t6) => this.enableUpdating = t6)), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach(((t6) => t6(this)));
  }
  addController(t6) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(t6), void 0 !== this.renderRoot && this.isConnected && t6.hostConnected?.();
  }
  removeController(t6) {
    this._$EO?.delete(t6);
  }
  _$E_() {
    const t6 = /* @__PURE__ */ new Map(), s5 = this.constructor.elementProperties;
    for (const i6 of s5.keys()) this.hasOwnProperty(i6) && (t6.set(i6, this[i6]), delete this[i6]);
    t6.size > 0 && (this._$Ep = t6);
  }
  createRenderRoot() {
    const t6 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S(t6, this.constructor.elementStyles), t6;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach(((t6) => t6.hostConnected?.()));
  }
  enableUpdating(t6) {
  }
  disconnectedCallback() {
    this._$EO?.forEach(((t6) => t6.hostDisconnected?.()));
  }
  attributeChangedCallback(t6, s5, i6) {
    this._$AK(t6, i6);
  }
  _$ET(t6, s5) {
    const i6 = this.constructor.elementProperties.get(t6), e6 = this.constructor._$Eu(t6, i6);
    if (void 0 !== e6 && true === i6.reflect) {
      const h3 = (void 0 !== i6.converter?.toAttribute ? i6.converter : u).toAttribute(s5, i6.type);
      this._$Em = t6, null == h3 ? this.removeAttribute(e6) : this.setAttribute(e6, h3), this._$Em = null;
    }
  }
  _$AK(t6, s5) {
    const i6 = this.constructor, e6 = i6._$Eh.get(t6);
    if (void 0 !== e6 && this._$Em !== e6) {
      const t7 = i6.getPropertyOptions(e6), h3 = "function" == typeof t7.converter ? { fromAttribute: t7.converter } : void 0 !== t7.converter?.fromAttribute ? t7.converter : u;
      this._$Em = e6;
      const r6 = h3.fromAttribute(s5, t7.type);
      this[e6] = r6 ?? this._$Ej?.get(e6) ?? r6, this._$Em = null;
    }
  }
  requestUpdate(t6, s5, i6) {
    if (void 0 !== t6) {
      const e6 = this.constructor, h3 = this[t6];
      if (i6 ??= e6.getPropertyOptions(t6), !((i6.hasChanged ?? f)(h3, s5) || i6.useDefault && i6.reflect && h3 === this._$Ej?.get(t6) && !this.hasAttribute(e6._$Eu(t6, i6)))) return;
      this.C(t6, s5, i6);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t6, s5, { useDefault: i6, reflect: e6, wrapped: h3 }, r6) {
    i6 && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t6) && (this._$Ej.set(t6, r6 ?? s5 ?? this[t6]), true !== h3 || void 0 !== r6) || (this._$AL.has(t6) || (this.hasUpdated || i6 || (s5 = void 0), this._$AL.set(t6, s5)), true === e6 && this._$Em !== t6 && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t6));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t7) {
      Promise.reject(t7);
    }
    const t6 = this.scheduleUpdate();
    return null != t6 && await t6, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [t8, s6] of this._$Ep) this[t8] = s6;
        this._$Ep = void 0;
      }
      const t7 = this.constructor.elementProperties;
      if (t7.size > 0) for (const [s6, i6] of t7) {
        const { wrapped: t8 } = i6, e6 = this[s6];
        true !== t8 || this._$AL.has(s6) || void 0 === e6 || this.C(s6, void 0, i6, e6);
      }
    }
    let t6 = false;
    const s5 = this._$AL;
    try {
      t6 = this.shouldUpdate(s5), t6 ? (this.willUpdate(s5), this._$EO?.forEach(((t7) => t7.hostUpdate?.())), this.update(s5)) : this._$EM();
    } catch (s6) {
      throw t6 = false, this._$EM(), s6;
    }
    t6 && this._$AE(s5);
  }
  willUpdate(t6) {
  }
  _$AE(t6) {
    this._$EO?.forEach(((t7) => t7.hostUpdated?.())), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t6)), this.updated(t6);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t6) {
    return true;
  }
  update(t6) {
    this._$Eq &&= this._$Eq.forEach(((t7) => this._$ET(t7, this[t7]))), this._$EM();
  }
  updated(t6) {
  }
  firstUpdated(t6) {
  }
};
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p?.({ ReactiveElement: y }), (a.reactiveElementVersions ??= []).push("2.1.1");

// node_modules/lit-html/lit-html.js
var t2 = globalThis;
var i3 = t2.trustedTypes;
var s2 = i3 ? i3.createPolicy("lit-html", { createHTML: (t6) => t6 }) : void 0;
var e3 = "$lit$";
var h2 = `lit$${Math.random().toFixed(9).slice(2)}$`;
var o3 = "?" + h2;
var n3 = `<${o3}>`;
var r3 = document;
var l2 = () => r3.createComment("");
var c3 = (t6) => null === t6 || "object" != typeof t6 && "function" != typeof t6;
var a2 = Array.isArray;
var u2 = (t6) => a2(t6) || "function" == typeof t6?.[Symbol.iterator];
var d2 = "[ 	\n\f\r]";
var f2 = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
var v = /-->/g;
var _ = />/g;
var m = RegExp(`>|${d2}(?:([^\\s"'>=/]+)(${d2}*=${d2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
var p2 = /'/g;
var g = /"/g;
var $ = /^(?:script|style|textarea|title)$/i;
var y2 = (t6) => (i6, ...s5) => ({ _$litType$: t6, strings: i6, values: s5 });
var x = y2(1);
var b2 = y2(2);
var w = y2(3);
var T = Symbol.for("lit-noChange");
var E = Symbol.for("lit-nothing");
var A = /* @__PURE__ */ new WeakMap();
var C = r3.createTreeWalker(r3, 129);
function P(t6, i6) {
  if (!a2(t6) || !t6.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== s2 ? s2.createHTML(i6) : i6;
}
var V = (t6, i6) => {
  const s5 = t6.length - 1, o7 = [];
  let r6, l3 = 2 === i6 ? "<svg>" : 3 === i6 ? "<math>" : "", c5 = f2;
  for (let i7 = 0; i7 < s5; i7++) {
    const s6 = t6[i7];
    let a3, u5, d3 = -1, y3 = 0;
    for (; y3 < s6.length && (c5.lastIndex = y3, u5 = c5.exec(s6), null !== u5); ) y3 = c5.lastIndex, c5 === f2 ? "!--" === u5[1] ? c5 = v : void 0 !== u5[1] ? c5 = _ : void 0 !== u5[2] ? ($.test(u5[2]) && (r6 = RegExp("</" + u5[2], "g")), c5 = m) : void 0 !== u5[3] && (c5 = m) : c5 === m ? ">" === u5[0] ? (c5 = r6 ?? f2, d3 = -1) : void 0 === u5[1] ? d3 = -2 : (d3 = c5.lastIndex - u5[2].length, a3 = u5[1], c5 = void 0 === u5[3] ? m : '"' === u5[3] ? g : p2) : c5 === g || c5 === p2 ? c5 = m : c5 === v || c5 === _ ? c5 = f2 : (c5 = m, r6 = void 0);
    const x2 = c5 === m && t6[i7 + 1].startsWith("/>") ? " " : "";
    l3 += c5 === f2 ? s6 + n3 : d3 >= 0 ? (o7.push(a3), s6.slice(0, d3) + e3 + s6.slice(d3) + h2 + x2) : s6 + h2 + (-2 === d3 ? i7 : x2);
  }
  return [P(t6, l3 + (t6[s5] || "<?>") + (2 === i6 ? "</svg>" : 3 === i6 ? "</math>" : "")), o7];
};
var N = class _N {
  constructor({ strings: t6, _$litType$: s5 }, n5) {
    let r6;
    this.parts = [];
    let c5 = 0, a3 = 0;
    const u5 = t6.length - 1, d3 = this.parts, [f3, v3] = V(t6, s5);
    if (this.el = _N.createElement(f3, n5), C.currentNode = this.el.content, 2 === s5 || 3 === s5) {
      const t7 = this.el.content.firstChild;
      t7.replaceWith(...t7.childNodes);
    }
    for (; null !== (r6 = C.nextNode()) && d3.length < u5; ) {
      if (1 === r6.nodeType) {
        if (r6.hasAttributes()) for (const t7 of r6.getAttributeNames()) if (t7.endsWith(e3)) {
          const i6 = v3[a3++], s6 = r6.getAttribute(t7).split(h2), e6 = /([.?@])?(.*)/.exec(i6);
          d3.push({ type: 1, index: c5, name: e6[2], strings: s6, ctor: "." === e6[1] ? H : "?" === e6[1] ? I : "@" === e6[1] ? L : k }), r6.removeAttribute(t7);
        } else t7.startsWith(h2) && (d3.push({ type: 6, index: c5 }), r6.removeAttribute(t7));
        if ($.test(r6.tagName)) {
          const t7 = r6.textContent.split(h2), s6 = t7.length - 1;
          if (s6 > 0) {
            r6.textContent = i3 ? i3.emptyScript : "";
            for (let i6 = 0; i6 < s6; i6++) r6.append(t7[i6], l2()), C.nextNode(), d3.push({ type: 2, index: ++c5 });
            r6.append(t7[s6], l2());
          }
        }
      } else if (8 === r6.nodeType) if (r6.data === o3) d3.push({ type: 2, index: c5 });
      else {
        let t7 = -1;
        for (; -1 !== (t7 = r6.data.indexOf(h2, t7 + 1)); ) d3.push({ type: 7, index: c5 }), t7 += h2.length - 1;
      }
      c5++;
    }
  }
  static createElement(t6, i6) {
    const s5 = r3.createElement("template");
    return s5.innerHTML = t6, s5;
  }
};
function S2(t6, i6, s5 = t6, e6) {
  if (i6 === T) return i6;
  let h3 = void 0 !== e6 ? s5._$Co?.[e6] : s5._$Cl;
  const o7 = c3(i6) ? void 0 : i6._$litDirective$;
  return h3?.constructor !== o7 && (h3?._$AO?.(false), void 0 === o7 ? h3 = void 0 : (h3 = new o7(t6), h3._$AT(t6, s5, e6)), void 0 !== e6 ? (s5._$Co ??= [])[e6] = h3 : s5._$Cl = h3), void 0 !== h3 && (i6 = S2(t6, h3._$AS(t6, i6.values), h3, e6)), i6;
}
var M = class {
  constructor(t6, i6) {
    this._$AV = [], this._$AN = void 0, this._$AD = t6, this._$AM = i6;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t6) {
    const { el: { content: i6 }, parts: s5 } = this._$AD, e6 = (t6?.creationScope ?? r3).importNode(i6, true);
    C.currentNode = e6;
    let h3 = C.nextNode(), o7 = 0, n5 = 0, l3 = s5[0];
    for (; void 0 !== l3; ) {
      if (o7 === l3.index) {
        let i7;
        2 === l3.type ? i7 = new R(h3, h3.nextSibling, this, t6) : 1 === l3.type ? i7 = new l3.ctor(h3, l3.name, l3.strings, this, t6) : 6 === l3.type && (i7 = new z(h3, this, t6)), this._$AV.push(i7), l3 = s5[++n5];
      }
      o7 !== l3?.index && (h3 = C.nextNode(), o7++);
    }
    return C.currentNode = r3, e6;
  }
  p(t6) {
    let i6 = 0;
    for (const s5 of this._$AV) void 0 !== s5 && (void 0 !== s5.strings ? (s5._$AI(t6, s5, i6), i6 += s5.strings.length - 2) : s5._$AI(t6[i6])), i6++;
  }
};
var R = class _R {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t6, i6, s5, e6) {
    this.type = 2, this._$AH = E, this._$AN = void 0, this._$AA = t6, this._$AB = i6, this._$AM = s5, this.options = e6, this._$Cv = e6?.isConnected ?? true;
  }
  get parentNode() {
    let t6 = this._$AA.parentNode;
    const i6 = this._$AM;
    return void 0 !== i6 && 11 === t6?.nodeType && (t6 = i6.parentNode), t6;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t6, i6 = this) {
    t6 = S2(this, t6, i6), c3(t6) ? t6 === E || null == t6 || "" === t6 ? (this._$AH !== E && this._$AR(), this._$AH = E) : t6 !== this._$AH && t6 !== T && this._(t6) : void 0 !== t6._$litType$ ? this.$(t6) : void 0 !== t6.nodeType ? this.T(t6) : u2(t6) ? this.k(t6) : this._(t6);
  }
  O(t6) {
    return this._$AA.parentNode.insertBefore(t6, this._$AB);
  }
  T(t6) {
    this._$AH !== t6 && (this._$AR(), this._$AH = this.O(t6));
  }
  _(t6) {
    this._$AH !== E && c3(this._$AH) ? this._$AA.nextSibling.data = t6 : this.T(r3.createTextNode(t6)), this._$AH = t6;
  }
  $(t6) {
    const { values: i6, _$litType$: s5 } = t6, e6 = "number" == typeof s5 ? this._$AC(t6) : (void 0 === s5.el && (s5.el = N.createElement(P(s5.h, s5.h[0]), this.options)), s5);
    if (this._$AH?._$AD === e6) this._$AH.p(i6);
    else {
      const t7 = new M(e6, this), s6 = t7.u(this.options);
      t7.p(i6), this.T(s6), this._$AH = t7;
    }
  }
  _$AC(t6) {
    let i6 = A.get(t6.strings);
    return void 0 === i6 && A.set(t6.strings, i6 = new N(t6)), i6;
  }
  k(t6) {
    a2(this._$AH) || (this._$AH = [], this._$AR());
    const i6 = this._$AH;
    let s5, e6 = 0;
    for (const h3 of t6) e6 === i6.length ? i6.push(s5 = new _R(this.O(l2()), this.O(l2()), this, this.options)) : s5 = i6[e6], s5._$AI(h3), e6++;
    e6 < i6.length && (this._$AR(s5 && s5._$AB.nextSibling, e6), i6.length = e6);
  }
  _$AR(t6 = this._$AA.nextSibling, i6) {
    for (this._$AP?.(false, true, i6); t6 !== this._$AB; ) {
      const i7 = t6.nextSibling;
      t6.remove(), t6 = i7;
    }
  }
  setConnected(t6) {
    void 0 === this._$AM && (this._$Cv = t6, this._$AP?.(t6));
  }
};
var k = class {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t6, i6, s5, e6, h3) {
    this.type = 1, this._$AH = E, this._$AN = void 0, this.element = t6, this.name = i6, this._$AM = e6, this.options = h3, s5.length > 2 || "" !== s5[0] || "" !== s5[1] ? (this._$AH = Array(s5.length - 1).fill(new String()), this.strings = s5) : this._$AH = E;
  }
  _$AI(t6, i6 = this, s5, e6) {
    const h3 = this.strings;
    let o7 = false;
    if (void 0 === h3) t6 = S2(this, t6, i6, 0), o7 = !c3(t6) || t6 !== this._$AH && t6 !== T, o7 && (this._$AH = t6);
    else {
      const e7 = t6;
      let n5, r6;
      for (t6 = h3[0], n5 = 0; n5 < h3.length - 1; n5++) r6 = S2(this, e7[s5 + n5], i6, n5), r6 === T && (r6 = this._$AH[n5]), o7 ||= !c3(r6) || r6 !== this._$AH[n5], r6 === E ? t6 = E : t6 !== E && (t6 += (r6 ?? "") + h3[n5 + 1]), this._$AH[n5] = r6;
    }
    o7 && !e6 && this.j(t6);
  }
  j(t6) {
    t6 === E ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t6 ?? "");
  }
};
var H = class extends k {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t6) {
    this.element[this.name] = t6 === E ? void 0 : t6;
  }
};
var I = class extends k {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t6) {
    this.element.toggleAttribute(this.name, !!t6 && t6 !== E);
  }
};
var L = class extends k {
  constructor(t6, i6, s5, e6, h3) {
    super(t6, i6, s5, e6, h3), this.type = 5;
  }
  _$AI(t6, i6 = this) {
    if ((t6 = S2(this, t6, i6, 0) ?? E) === T) return;
    const s5 = this._$AH, e6 = t6 === E && s5 !== E || t6.capture !== s5.capture || t6.once !== s5.once || t6.passive !== s5.passive, h3 = t6 !== E && (s5 === E || e6);
    e6 && this.element.removeEventListener(this.name, this, s5), h3 && this.element.addEventListener(this.name, this, t6), this._$AH = t6;
  }
  handleEvent(t6) {
    "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t6) : this._$AH.handleEvent(t6);
  }
};
var z = class {
  constructor(t6, i6, s5) {
    this.element = t6, this.type = 6, this._$AN = void 0, this._$AM = i6, this.options = s5;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t6) {
    S2(this, t6);
  }
};
var Z = { M: e3, P: h2, A: o3, C: 1, L: V, R: M, D: u2, V: S2, I: R, H: k, N: I, U: L, B: H, F: z };
var j = t2.litHtmlPolyfillSupport;
j?.(N, R), (t2.litHtmlVersions ??= []).push("3.3.1");
var B = (t6, i6, s5) => {
  const e6 = s5?.renderBefore ?? i6;
  let h3 = e6._$litPart$;
  if (void 0 === h3) {
    const t7 = s5?.renderBefore ?? null;
    e6._$litPart$ = h3 = new R(i6.insertBefore(l2(), t7), t7, void 0, s5 ?? {});
  }
  return h3._$AI(t6), h3;
};

// node_modules/lit-element/lit-element.js
var s3 = globalThis;
var i4 = class extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const t6 = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t6.firstChild, t6;
  }
  update(t6) {
    const r6 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t6), this._$Do = B(r6, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return T;
  }
};
i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
var o4 = s3.litElementPolyfillSupport;
o4?.({ LitElement: i4 });
(s3.litElementVersions ??= []).push("4.2.1");

// node_modules/@lit/reactive-element/decorators/custom-element.js
var t3 = (t6) => (e6, o7) => {
  void 0 !== o7 ? o7.addInitializer((() => {
    customElements.define(t6, e6);
  })) : customElements.define(t6, e6);
};

// node_modules/@lit/reactive-element/decorators/property.js
var o5 = { attribute: true, type: String, converter: u, reflect: false, hasChanged: f };
var r4 = (t6 = o5, e6, r6) => {
  const { kind: n5, metadata: i6 } = r6;
  let s5 = globalThis.litPropertyMetadata.get(i6);
  if (void 0 === s5 && globalThis.litPropertyMetadata.set(i6, s5 = /* @__PURE__ */ new Map()), "setter" === n5 && ((t6 = Object.create(t6)).wrapped = true), s5.set(r6.name, t6), "accessor" === n5) {
    const { name: o7 } = r6;
    return { set(r7) {
      const n6 = e6.get.call(this);
      e6.set.call(this, r7), this.requestUpdate(o7, n6, t6);
    }, init(e7) {
      return void 0 !== e7 && this.C(o7, void 0, t6, e7), e7;
    } };
  }
  if ("setter" === n5) {
    const { name: o7 } = r6;
    return function(r7) {
      const n6 = this[o7];
      e6.call(this, r7), this.requestUpdate(o7, n6, t6);
    };
  }
  throw Error("Unsupported decorator location: " + n5);
};
function n4(t6) {
  return (e6, o7) => "object" == typeof o7 ? r4(t6, e6, o7) : ((t7, e7, o8) => {
    const r6 = e7.hasOwnProperty(o8);
    return e7.constructor.createProperty(o8, t7), r6 ? Object.getOwnPropertyDescriptor(e7, o8) : void 0;
  })(t6, e6, o7);
}

// node_modules/lit-html/directive.js
var t4 = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3, BOOLEAN_ATTRIBUTE: 4, EVENT: 5, ELEMENT: 6 };
var e5 = (t6) => (...e6) => ({ _$litDirective$: t6, values: e6 });
var i5 = class {
  constructor(t6) {
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AT(t6, e6, i6) {
    this._$Ct = t6, this._$AM = e6, this._$Ci = i6;
  }
  _$AS(t6, e6) {
    return this.update(t6, e6);
  }
  update(t6, e6) {
    return this.render(...e6);
  }
};

// node_modules/lit-html/directive-helpers.js
var { I: t5 } = Z;
var r5 = () => document.createComment("");
var s4 = (o7, i6, n5) => {
  const e6 = o7._$AA.parentNode, l3 = void 0 === i6 ? o7._$AB : i6._$AA;
  if (void 0 === n5) {
    const i7 = e6.insertBefore(r5(), l3), d3 = e6.insertBefore(r5(), l3);
    n5 = new t5(i7, d3, o7, o7.options);
  } else {
    const t6 = n5._$AB.nextSibling, i7 = n5._$AM, d3 = i7 !== o7;
    if (d3) {
      let t7;
      n5._$AQ?.(o7), n5._$AM = o7, void 0 !== n5._$AP && (t7 = o7._$AU) !== i7._$AU && n5._$AP(t7);
    }
    if (t6 !== l3 || d3) {
      let o8 = n5._$AA;
      for (; o8 !== t6; ) {
        const t7 = o8.nextSibling;
        e6.insertBefore(o8, l3), o8 = t7;
      }
    }
  }
  return n5;
};
var v2 = (o7, t6, i6 = o7) => (o7._$AI(t6, i6), o7);
var u3 = {};
var m2 = (o7, t6 = u3) => o7._$AH = t6;
var p3 = (o7) => o7._$AH;
var M2 = (o7) => {
  o7._$AR(), o7._$AA.remove();
};

// node_modules/lit-html/directives/repeat.js
var u4 = (e6, s5, t6) => {
  const r6 = /* @__PURE__ */ new Map();
  for (let l3 = s5; l3 <= t6; l3++) r6.set(e6[l3], l3);
  return r6;
};
var c4 = e5(class extends i5 {
  constructor(e6) {
    if (super(e6), e6.type !== t4.CHILD) throw Error("repeat() can only be used in text expressions");
  }
  dt(e6, s5, t6) {
    let r6;
    void 0 === t6 ? t6 = s5 : void 0 !== s5 && (r6 = s5);
    const l3 = [], o7 = [];
    let i6 = 0;
    for (const s6 of e6) l3[i6] = r6 ? r6(s6, i6) : i6, o7[i6] = t6(s6, i6), i6++;
    return { values: o7, keys: l3 };
  }
  render(e6, s5, t6) {
    return this.dt(e6, s5, t6).values;
  }
  update(s5, [t6, r6, c5]) {
    const d3 = p3(s5), { values: p4, keys: a3 } = this.dt(t6, r6, c5);
    if (!Array.isArray(d3)) return this.ut = a3, p4;
    const h3 = this.ut ??= [], v3 = [];
    let m3, y3, x2 = 0, j2 = d3.length - 1, k2 = 0, w2 = p4.length - 1;
    for (; x2 <= j2 && k2 <= w2; ) if (null === d3[x2]) x2++;
    else if (null === d3[j2]) j2--;
    else if (h3[x2] === a3[k2]) v3[k2] = v2(d3[x2], p4[k2]), x2++, k2++;
    else if (h3[j2] === a3[w2]) v3[w2] = v2(d3[j2], p4[w2]), j2--, w2--;
    else if (h3[x2] === a3[w2]) v3[w2] = v2(d3[x2], p4[w2]), s4(s5, v3[w2 + 1], d3[x2]), x2++, w2--;
    else if (h3[j2] === a3[k2]) v3[k2] = v2(d3[j2], p4[k2]), s4(s5, d3[x2], d3[j2]), j2--, k2++;
    else if (void 0 === m3 && (m3 = u4(a3, k2, w2), y3 = u4(h3, x2, j2)), m3.has(h3[x2])) if (m3.has(h3[j2])) {
      const e6 = y3.get(a3[k2]), t7 = void 0 !== e6 ? d3[e6] : null;
      if (null === t7) {
        const e7 = s4(s5, d3[x2]);
        v2(e7, p4[k2]), v3[k2] = e7;
      } else v3[k2] = v2(t7, p4[k2]), s4(s5, d3[x2], t7), d3[e6] = null;
      k2++;
    } else M2(d3[j2]), j2--;
    else M2(d3[x2]), x2++;
    for (; k2 <= w2; ) {
      const e6 = s4(s5, v3[w2 + 1]);
      v2(e6, p4[k2]), v3[k2++] = e6;
    }
    for (; x2 <= j2; ) {
      const e6 = d3[x2++];
      null !== e6 && M2(e6);
    }
    return this.ut = a3, m2(s5, v3), T;
  }
});

// node_modules/lit-html/directives/if-defined.js
var o6 = (o7) => o7 ?? E;

// _okd07jsz2:C:\Users\romai\Documents\1-programation\1-chrono_des_vignes_2.0\front-end\css\form.css
var form_default = `/*! tailwindcss v4.1.13 | MIT License | https://tailwindcss.com */@layer properties;@layer theme,base,components,utilities;@layer theme{:root,:host{--font-sans: ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";--font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;--color-indigo-500: oklch(58.5% .233 277.117);--color-indigo-600: oklch(51.1% .262 276.966);--color-gray-50: oklch(98.5% .002 247.839);--color-gray-100: oklch(96.7% .003 264.542);--color-gray-300: oklch(87.2% .01 258.338);--color-gray-400: oklch(70.7% .022 261.325);--color-gray-500: oklch(55.1% .027 264.364);--color-gray-600: oklch(44.6% .03 256.802);--color-gray-900: oklch(21% .034 264.665);--color-gray-950: oklch(13% .028 261.692);--color-white: #fff;--spacing: .25rem;--text-xs: .75rem;--text-sm: .875rem;--text-sm--line-height: calc(1.25 / .875);--text-base: 1rem;--text-base--line-height: 1.5 ;--font-weight-medium: 500;--font-weight-semibold: 600;--radius-sm: .25rem;--radius-md: .375rem;--radius-lg: .5rem;--default-font-family: var(--font-sans);--default-mono-font-family: var(--font-mono)}}@layer base{*,:after,:before,::backdrop,::file-selector-button{box-sizing:border-box;margin:0;padding:0;border:0 solid}html,:host{line-height:1.5;-webkit-text-size-adjust:100%;tab-size:4;font-family:var(--default-font-family, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji");font-feature-settings:var(--default-font-feature-settings, normal);font-variation-settings:var(--default-font-variation-settings, normal);-webkit-tap-highlight-color:transparent}hr{height:0;color:inherit;border-top-width:1px}abbr:where([title]){-webkit-text-decoration:underline dotted;text-decoration:underline dotted}h1,h2,h3,h4,h5,h6{font-size:inherit;font-weight:inherit}a{color:inherit;-webkit-text-decoration:inherit;text-decoration:inherit}b,strong{font-weight:bolder}code,kbd,samp,pre{font-family:var(--default-mono-font-family, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace);font-feature-settings:var(--default-mono-font-feature-settings, normal);font-variation-settings:var(--default-mono-font-variation-settings, normal);font-size:1em}small{font-size:80%}sub,sup{font-size:75%;line-height:0;position:relative;vertical-align:baseline}sub{bottom:-.25em}sup{top:-.5em}table{text-indent:0;border-color:inherit;border-collapse:collapse}:-moz-focusring{outline:auto}progress{vertical-align:baseline}summary{display:list-item}ol,ul,menu{list-style:none}img,svg,video,canvas,audio,iframe,embed,object{display:block;vertical-align:middle}img,video{max-width:100%;height:auto}button,input,select,optgroup,textarea,::file-selector-button{font:inherit;font-feature-settings:inherit;font-variation-settings:inherit;letter-spacing:inherit;color:inherit;border-radius:0;background-color:transparent;opacity:1}:where(select:is([multiple],[size])) optgroup{font-weight:bolder}:where(select:is([multiple],[size])) optgroup option{padding-inline-start:20px}::file-selector-button{margin-inline-end:4px}::placeholder{opacity:1}@supports (not (-webkit-appearance: -apple-pay-button)) or (contain-intrinsic-size: 1px){::placeholder{color:currentcolor;@supports (color: color-mix(in lab,red,red)){color:color-mix(in oklab,currentcolor 50%,transparent)}}}textarea{resize:vertical}::-webkit-search-decoration{-webkit-appearance:none}::-webkit-date-and-time-value{min-height:1lh;text-align:inherit}::-webkit-datetime-edit{display:inline-flex}::-webkit-datetime-edit-fields-wrapper{padding:0}::-webkit-datetime-edit,::-webkit-datetime-edit-year-field,::-webkit-datetime-edit-month-field,::-webkit-datetime-edit-day-field,::-webkit-datetime-edit-hour-field,::-webkit-datetime-edit-minute-field,::-webkit-datetime-edit-second-field,::-webkit-datetime-edit-millisecond-field,::-webkit-datetime-edit-meridiem-field{padding-block:0}::-webkit-calendar-picker-indicator{line-height:1}:-moz-ui-invalid{box-shadow:none}button,input:where([type=button],[type=reset],[type=submit]),::file-selector-button{appearance:button}::-webkit-inner-spin-button,::-webkit-outer-spin-button{height:auto}[hidden]:where(:not([hidden=until-found])){display:none!important}}@layer utilities{.pointer-events-none{pointer-events:none}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border-width:0}.relative{position:relative}.static{position:static}.col-span-full{grid-column:1 / -1}.col-start-1{grid-column-start:1}.row-start-1{grid-row-start:1}.container{width:100%;@media (width >= 40rem){max-width:40rem}@media (width >= 48rem){max-width:48rem}@media (width >= 64rem){max-width:64rem}@media (width >= 80rem){max-width:80rem}@media (width >= 96rem){max-width:96rem}}.mx-auto{margin-inline:auto}.mt-1{margin-top:calc(var(--spacing) * 1)}.mt-2{margin-top:calc(var(--spacing) * 2)}.mt-4{margin-top:calc(var(--spacing) * 4)}.mt-6{margin-top:calc(var(--spacing) * 6)}.mt-10{margin-top:calc(var(--spacing) * 10)}.mr-2{margin-right:calc(var(--spacing) * 2)}.block{display:block}.flex{display:flex}.grid{display:grid}.inline{display:inline}.size-3\\.5{width:calc(var(--spacing) * 3.5);height:calc(var(--spacing) * 3.5)}.size-4{width:calc(var(--spacing) * 4);height:calc(var(--spacing) * 4)}.size-5{width:calc(var(--spacing) * 5);height:calc(var(--spacing) * 5)}.size-12{width:calc(var(--spacing) * 12);height:calc(var(--spacing) * 12)}.h-6{height:calc(var(--spacing) * 6)}.w-full{width:100%}.shrink-0{flex-shrink:0}.cursor-pointer{cursor:pointer}.appearance-none{appearance:none}.grid-cols-1{grid-template-columns:repeat(1,minmax(0,1fr))}.items-center{align-items:center}.justify-center{justify-content:center}.gap-3{gap:calc(var(--spacing) * 3)}.space-y-6{:where(&>:not(:last-child)){--tw-space-y-reverse: 0;margin-block-start:calc(calc(var(--spacing) * 6) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * 6) * calc(1 - var(--tw-space-y-reverse)))}}.space-y-10{:where(&>:not(:last-child)){--tw-space-y-reverse: 0;margin-block-start:calc(calc(var(--spacing) * 10) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * 10) * calc(1 - var(--tw-space-y-reverse)))}}.space-y-12{:where(&>:not(:last-child)){--tw-space-y-reverse: 0;margin-block-start:calc(calc(var(--spacing) * 12) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * 12) * calc(1 - var(--tw-space-y-reverse)))}}.gap-x-3{column-gap:calc(var(--spacing) * 3)}.gap-x-6{column-gap:calc(var(--spacing) * 6)}.gap-y-8{row-gap:calc(var(--spacing) * 8)}.self-center{align-self:center}.justify-self-center{justify-self:center}.justify-self-end{justify-self:flex-end}.rounded-full{border-radius:calc(infinity * 1px)}.rounded-lg{border-radius:var(--radius-lg)}.rounded-md{border-radius:var(--radius-md)}.rounded-sm{border-radius:var(--radius-sm)}.border{border-style:var(--tw-border-style);border-width:1px}.border-b{border-bottom-style:var(--tw-border-style);border-bottom-width:1px}.border-dashed{--tw-border-style: dashed;border-style:dashed}.border-gray-300{border-color:var(--color-gray-300)}.border-gray-900\\/10{border-color:color-mix(in srgb,oklch(21% .034 264.665) 10%,transparent);@supports (color: color-mix(in lab,red,red)){border-color:color-mix(in oklab,var(--color-gray-900) 10%,transparent)}}.border-gray-900\\/25{border-color:color-mix(in srgb,oklch(21% .034 264.665) 25%,transparent);@supports (color: color-mix(in lab,red,red)){border-color:color-mix(in oklab,var(--color-gray-900) 25%,transparent)}}.bg-transparent{background-color:transparent}.bg-white{background-color:var(--color-white)}.stroke-white{stroke:var(--color-white)}.px-3{padding-inline:calc(var(--spacing) * 3)}.px-6{padding-inline:calc(var(--spacing) * 6)}.py-1\\.5{padding-block:calc(var(--spacing) * 1.5)}.py-2{padding-block:calc(var(--spacing) * 2)}.py-10{padding-block:calc(var(--spacing) * 10)}.pr-8{padding-right:calc(var(--spacing) * 8)}.pb-12{padding-bottom:calc(var(--spacing) * 12)}.pl-1{padding-left:calc(var(--spacing) * 1)}.pl-3{padding-left:calc(var(--spacing) * 3)}.text-center{text-align:center}.text-base{font-size:var(--text-base);line-height:var(--tw-leading, var(--text-base--line-height))}.text-base\\/7{font-size:var(--text-base);line-height:calc(var(--spacing) * 7)}.text-sm{font-size:var(--text-sm);line-height:var(--tw-leading, var(--text-sm--line-height))}.text-sm\\/6{font-size:var(--text-sm);line-height:calc(var(--spacing) * 6)}.text-xs\\/5{font-size:var(--text-xs);line-height:calc(var(--spacing) * 5)}.font-medium{--tw-font-weight: var(--font-weight-medium);font-weight:var(--font-weight-medium)}.font-semibold{--tw-font-weight: var(--font-weight-semibold);font-weight:var(--font-weight-semibold)}.text-gray-300{color:var(--color-gray-300)}.text-gray-500{color:var(--color-gray-500)}.text-gray-600{color:var(--color-gray-600)}.text-gray-900{color:var(--color-gray-900)}.text-indigo-600{color:var(--color-indigo-600)}.opacity-0{opacity:0%}.shadow-xs{--tw-shadow: 0 1px 2px 0 var(--tw-shadow-color, rgb(0 0 0 / .05));box-shadow:var(--tw-inset-shadow),var(--tw-inset-ring-shadow),var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow)}.inset-ring{--tw-inset-ring-shadow: inset 0 0 0 1px var(--tw-inset-ring-color, currentcolor);box-shadow:var(--tw-inset-shadow),var(--tw-inset-ring-shadow),var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow)}.inset-ring-gray-300{--tw-inset-ring-color: var(--color-gray-300)}.outline-1{outline-style:var(--tw-outline-style);outline-width:1px}.-outline-offset-1{outline-offset:-1px}.outline-gray-300{outline-color:var(--color-gray-300)}.group-has-checked\\:opacity-100{&:is(:where(.group):has(*:checked) *){opacity:100%}}.group-has-indeterminate\\:opacity-100{&:is(:where(.group):has(*:indeterminate) *){opacity:100%}}.group-has-disabled\\:stroke-gray-950\\/25{&:is(:where(.group):has(*:disabled) *){stroke:color-mix(in srgb,oklch(13% .028 261.692) 25%,transparent);@supports (color: color-mix(in lab,red,red)){stroke:color-mix(in oklab,var(--color-gray-950) 25%,transparent)}}}.placeholder\\:text-gray-400{&::placeholder{color:var(--color-gray-400)}}.before\\:absolute{&:before{content:var(--tw-content);position:absolute}}.before\\:inset-1{&:before{content:var(--tw-content);inset:calc(var(--spacing) * 1)}}.before\\:rounded-full{&:before{content:var(--tw-content);border-radius:calc(infinity * 1px)}}.before\\:bg-white{&:before{content:var(--tw-content);background-color:var(--color-white)}}.not-checked\\:before\\:hidden{&:not(*:checked){&:before{content:var(--tw-content);display:none}}}.checked\\:border-indigo-600{&:checked{border-color:var(--color-indigo-600)}}.checked\\:bg-indigo-600{&:checked{background-color:var(--color-indigo-600)}}.indeterminate\\:border-indigo-600{&:indeterminate{border-color:var(--color-indigo-600)}}.indeterminate\\:bg-indigo-600{&:indeterminate{background-color:var(--color-indigo-600)}}.focus-within\\:outline-2{&:focus-within{outline-style:var(--tw-outline-style);outline-width:2px}}.focus-within\\:outline-offset-2{&:focus-within{outline-offset:2px}}.focus-within\\:outline-indigo-600{&:focus-within{outline-color:var(--color-indigo-600)}}.hover\\:bg-gray-50{&:hover{@media (hover: hover){background-color:var(--color-gray-50)}}}.hover\\:text-indigo-500{&:hover{@media (hover: hover){color:var(--color-indigo-500)}}}.focus\\:outline-2{&:focus{outline-style:var(--tw-outline-style);outline-width:2px}}.focus\\:-outline-offset-2{&:focus{outline-offset:-2px}}.focus\\:outline-indigo-600{&:focus{outline-color:var(--color-indigo-600)}}.focus-visible\\:outline-2{&:focus-visible{outline-style:var(--tw-outline-style);outline-width:2px}}.focus-visible\\:outline-offset-2{&:focus-visible{outline-offset:2px}}.focus-visible\\:outline-indigo-600{&:focus-visible{outline-color:var(--color-indigo-600)}}.disabled\\:border-gray-300{&:disabled{border-color:var(--color-gray-300)}}.disabled\\:bg-gray-100{&:disabled{background-color:var(--color-gray-100)}}.disabled\\:before\\:bg-gray-400{&:disabled{&:before{content:var(--tw-content);background-color:var(--color-gray-400)}}}.disabled\\:checked\\:bg-gray-100{&:disabled{&:checked{background-color:var(--color-gray-100)}}}.sm\\:col-span-2{@media (width >= 40rem){grid-column:span 2 / span 2}}.sm\\:col-span-3{@media (width >= 40rem){grid-column:span 3 / span 3}}.sm\\:col-span-4{@media (width >= 40rem){grid-column:span 4 / span 4}}.sm\\:col-start-1{@media (width >= 40rem){grid-column-start:1}}.sm\\:size-4{@media (width >= 40rem){width:calc(var(--spacing) * 4);height:calc(var(--spacing) * 4)}}.sm\\:grid-cols-6{@media (width >= 40rem){grid-template-columns:repeat(6,minmax(0,1fr))}}.sm\\:text-sm\\/6{@media (width >= 40rem){font-size:var(--text-sm);line-height:calc(var(--spacing) * 6)}}.forced-colors\\:appearance-auto{@media (forced-colors: active){appearance:auto}}.forced-colors\\:before\\:hidden{@media (forced-colors: active){&:before{content:var(--tw-content);display:none}}}}@layer base{[type=text],input:where(:not([type])),[type=email],[type=url],[type=password],[type=number],[type=date],[type=datetime-local],[type=month],[type=search],[type=tel],[type=time],[type=week],[multiple],textarea,select{appearance:none;background-color:#fff;border-color:#6a7282;border-width:1px;border-radius:0;padding:.5rem .75rem;font-size:1rem;line-height:1.5rem;--tw-shadow: 0 0 #0000;&:focus{outline:2px solid transparent;outline-offset:2px;--tw-ring-inset: var(--tw-empty, );--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-color: oklch(54.6% .245 262.881);--tw-ring-offset-shadow: var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow: var(--tw-ring-inset) 0 0 0 calc(1px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow);border-color:#155dfc}}input::placeholder,textarea::placeholder{color:#6a7282;opacity:1}::-webkit-datetime-edit-fields-wrapper{padding:0}::-webkit-date-and-time-value{min-height:1.5em}::-webkit-date-and-time-value{text-align:inherit}::-webkit-datetime-edit{display:inline-flex}::-webkit-datetime-edit,::-webkit-datetime-edit-year-field,::-webkit-datetime-edit-month-field,::-webkit-datetime-edit-day-field,::-webkit-datetime-edit-hour-field,::-webkit-datetime-edit-minute-field,::-webkit-datetime-edit-second-field,::-webkit-datetime-edit-millisecond-field,::-webkit-datetime-edit-meridiem-field{padding-top:0;padding-bottom:0}select{background-image:url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='oklch(55.1%25 0.027 264.364)' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");background-position:right .5rem center;background-repeat:no-repeat;background-size:1.5em 1.5em;padding-right:2.5rem;print-color-adjust:exact}[multiple],[size]:where(select:not([size="1"])){background-image:initial;background-position:initial;background-repeat:unset;background-size:initial;padding-right:.75rem;print-color-adjust:unset}[type=checkbox],[type=radio]{appearance:none;padding:0;print-color-adjust:exact;display:inline-block;vertical-align:middle;background-origin:border-box;user-select:none;flex-shrink:0;height:1rem;width:1rem;color:#155dfc;background-color:#fff;border-color:#6a7282;border-width:1px;--tw-shadow: 0 0 #0000}[type=checkbox]{border-radius:0}[type=radio]{border-radius:100%}[type=checkbox]:focus,[type=radio]:focus{outline:2px solid transparent;outline-offset:2px;--tw-ring-inset: var(--tw-empty, );--tw-ring-offset-width: 2px;--tw-ring-offset-color: #fff;--tw-ring-color: oklch(54.6% .245 262.881);--tw-ring-offset-shadow: var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow: var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow),var(--tw-ring-shadow),var(--tw-shadow)}[type=checkbox]:checked,[type=radio]:checked{border-color:transparent;background-color:currentColor;background-size:100% 100%;background-position:center;background-repeat:no-repeat}[type=checkbox]:checked{background-image:url("data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e");@media (forced-colors: active){appearance:auto}}[type=radio]:checked{background-image:url("data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3ccircle cx='8' cy='8' r='3'/%3e%3c/svg%3e");@media (forced-colors: active){appearance:auto}}[type=checkbox]:checked:hover,[type=checkbox]:checked:focus,[type=radio]:checked:hover,[type=radio]:checked:focus{border-color:transparent;background-color:currentColor}[type=checkbox]:indeterminate{background-image:url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 16 16'%3e%3cpath stroke='white' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 8h8'/%3e%3c/svg%3e");border-color:transparent;background-color:currentColor;background-size:100% 100%;background-position:center;background-repeat:no-repeat;@media (forced-colors: active){appearance:auto}}[type=checkbox]:indeterminate:hover,[type=checkbox]:indeterminate:focus{border-color:transparent;background-color:currentColor}[type=file]{background:unset;border-color:inherit;border-width:0;border-radius:0;padding:0;font-size:unset;line-height:inherit}[type=file]:focus{outline:1px solid ButtonText;outline:1px auto -webkit-focus-ring-color}}@property --tw-space-y-reverse{syntax: "*"; inherits: false; initial-value: 0;}@property --tw-border-style{syntax: "*"; inherits: false; initial-value: solid;}@property --tw-font-weight{syntax: "*"; inherits: false;}@property --tw-shadow{syntax: "*"; inherits: false; initial-value: 0 0 #0000;}@property --tw-shadow-color{syntax: "*"; inherits: false;}@property --tw-shadow-alpha{syntax: "<percentage>"; inherits: false; initial-value: 100%;}@property --tw-inset-shadow{syntax: "*"; inherits: false; initial-value: 0 0 #0000;}@property --tw-inset-shadow-color{syntax: "*"; inherits: false;}@property --tw-inset-shadow-alpha{syntax: "<percentage>"; inherits: false; initial-value: 100%;}@property --tw-ring-color{syntax: "*"; inherits: false;}@property --tw-ring-shadow{syntax: "*"; inherits: false; initial-value: 0 0 #0000;}@property --tw-inset-ring-color{syntax: "*"; inherits: false;}@property --tw-inset-ring-shadow{syntax: "*"; inherits: false; initial-value: 0 0 #0000;}@property --tw-ring-inset{syntax: "*"; inherits: false;}@property --tw-ring-offset-width{syntax: "<length>"; inherits: false; initial-value: 0px;}@property --tw-ring-offset-color{syntax: "*"; inherits: false; initial-value: #fff;}@property --tw-ring-offset-shadow{syntax: "*"; inherits: false; initial-value: 0 0 #0000;}@property --tw-outline-style{syntax: "*"; inherits: false; initial-value: solid;}@property --tw-content{syntax: "*"; initial-value: ""; inherits: false;}@layer properties{@supports ((-webkit-hyphens: none) and (not (margin-trim: inline))) or ((-moz-orient: inline) and (not (color:rgb(from red r g b)))){*,:before,:after,::backdrop{--tw-space-y-reverse: 0;--tw-border-style: solid;--tw-font-weight: initial;--tw-shadow: 0 0 #0000;--tw-shadow-color: initial;--tw-shadow-alpha: 100%;--tw-inset-shadow: 0 0 #0000;--tw-inset-shadow-color: initial;--tw-inset-shadow-alpha: 100%;--tw-ring-color: initial;--tw-ring-shadow: 0 0 #0000;--tw-inset-ring-color: initial;--tw-inset-ring-shadow: 0 0 #0000;--tw-ring-inset: initial;--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-offset-shadow: 0 0 #0000;--tw-outline-style: solid;--tw-content: ""}}}
`;

// ts/forms.ts
var LitForm = class extends i4 {
  constructor() {
    super(...arguments);
    this.fields = [];
    this.onSubmit = () => {
    };
  }
  renderField(field) {
    switch (field.type) {
      case "group":
        return this.renderFieldGroup(field);
      case "string":
        return this.renderStringField(field);
      case "text":
        return this.renderTextField(field);
      default:
        break;
    }
  }
  renderStringField(field) {
    return x`
            <div class="col-span-full">
                <label for="${field.name}" class="block text-sm/6 font-medium text-gray-900">${field.label}</label>
                <div>
                    <input id="${field.name}" type="text" name="${field.name}" autocomplete="${o6(field.autocomplete)}" value="${o6(field.value)}" class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"/>
                </div>
            </div>
        `;
  }
  renderTextField(field) {
    return x`
            <div class="col-span-full">
                <label for="${field.name}" class="block text-sm/6 font-medium text-gray-900">${field.label}</label>
                <div class="mt-2">
                    <textarea id="${field.name}" name="${field.name}" rows="3" class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"></textarea>
                </div>
            </div>
        `;
  }
  renderFileField(field) {
    return x`
            <div class="col-span-full">
                    <label for="cover-photo" class="block text-sm/6 font-medium text-gray-900">Cover photo</label>
                    <div class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10">
                        <div class="text-center">
                            <svg viewBox="0 0 24 24" fill="currentColor" data-slot="icon" aria-hidden="true" class="mx-auto size-12 text-gray-300">
                                <path d="M1.5 6a2.25 2.25 0 0 1 2.25-2.25h16.5A2.25 2.25 0 0 1 22.5 6v12a2.25 2.25 0 0 1-2.25 2.25H3.75A2.25 2.25 0 0 1 1.5 18V6ZM3 16.06V18c0 .414.336.75.75.75h16.5A.75.75 0 0 0 21 18v-1.94l-2.69-2.689a1.5 1.5 0 0 0-2.12 0l-.88.879.97.97a.75.75 0 1 1-1.06 1.06l-5.16-5.159a1.5 1.5 0 0 0-2.12 0L3 16.061Zm10.125-7.81a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Z" clip-rule="evenodd" fill-rule="evenodd" />
                            </svg>
                            <div class="mt-4 flex text-sm/6 text-gray-600">
                                <label for="file-upload" class="relative cursor-pointer rounded-md bg-transparent font-semibold text-indigo-600 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-indigo-600 hover:text-indigo-500">
                                    <span>Upload a file</span>
                                    <input id="file-upload" type="file" name="file-upload" class="sr-only" />
                                </label>
                                <p class="pl-1">or drag and drop</p>
                            </div>
                            <p class="text-xs/5 text-gray-600">PNG, JPG, GIF up to 10MB</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
  }
  renderFieldGroup(field) {
    console.debug(field);
    return x`
        <div class="border-b border-gray-900/10 pb-12">
            <h2 class="text-base/7 font-semibold text-gray-900">${field.name}</h2>
            ${field.description == "" ? x`` : x`<p class="mt-1 text-sm/6 text-gray-600">${field.description}</p>`}


            <div class="mt-10 grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-6">
                ${c4(field.fields, (field2) => field2.name, (field2) => this.renderField(field2))}
            </div>
        </div>
        `;
  }
  submitCallback(event) {
    event.preventDefault();
    console.log("form submitted", event);
    this.onSubmit(event);
    return false;
  }
  render() {
    console.debug("render fields ", this.fields);
    return x`
            <form @onsubmit=${this.submitCallback} action='javascript:void(0)'>
                <div class="space-y-12">
                    ${c4(this.fields, (field) => field.name, (field) => this.renderField(field))}
                </div>
                <button type="submit" value="Submit">
            </form>
        `;
  }
};
LitForm.styles = [
  r(form_default)
];
__decorateClass([
  n4({ attribute: false })
], LitForm.prototype, "fields", 2);
__decorateClass([
  n4({ attribute: false })
], LitForm.prototype, "onSubmit", 2);
LitForm = __decorateClass([
  t3("lit-form")
], LitForm);
export {
  LitForm
};
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
@lit/reactive-element/decorators/custom-element.js:
@lit/reactive-element/decorators/property.js:
@lit/reactive-element/decorators/state.js:
@lit/reactive-element/decorators/event-options.js:
@lit/reactive-element/decorators/base.js:
@lit/reactive-element/decorators/query.js:
@lit/reactive-element/decorators/query-all.js:
@lit/reactive-element/decorators/query-async.js:
@lit/reactive-element/decorators/query-assigned-nodes.js:
lit-html/directive.js:
lit-html/directives/repeat.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/decorators/query-assigned-elements.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directive-helpers.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directives/if-defined.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
//# sourceMappingURL=/static/js/forms.js.map
