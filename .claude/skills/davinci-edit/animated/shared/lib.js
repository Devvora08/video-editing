/* My First Week on YouTube: shared timeline helpers. Each chapter page calls FW(cfg) and builds on the returned kit. */
window.FW = function (cfg) {
  const gsap = window.gsap, tl = gsap.timeline({ paused: true });
  const E = 'power3.out', $ = s => document.querySelector(s), $$ = s => Array.from(document.querySelectorAll(s));
  const K = { tl, E, $, $$ };

  // background layers + navbar markup
  const stage = $('#stage');
  stage.insertAdjacentHTML('afterbegin', '<div id="bg"></div><div id="glow"></div><div class="blob" id="b1"></div><div class="blob" id="b2"></div><div id="grain"></div><div id="vig"></div>');
  const names = cfg.nav || window.NAV || [];   // chapter pill labels (chapters 1..N), injected by mk.py from plan.json
  stage.insertAdjacentHTML('beforeend', '<div id="nav">' + names.map((n, i) =>
    `<div class="p" id="np${i + 1}"><span class="n">${String(i + 1).padStart(2, '0')}</span><span>${n}</span><span class="ck">✓</span><div class="tr"><div class="fl"></div></div></div>`).join('') + '</div><div id="sub"></div>');

  // motion (no bounce / overshoot anywhere: soft ease-outs, transforms only)
  K.IN = (sel, at, from, d) => tl.fromTo(sel, Object.assign({ opacity: 0, y: 36 }, from || {}), { opacity: 1, x: 0, y: 0, scale: 1, rotation: 0, filter: 'blur(0px)', duration: Math.max(d || 0.65, 0.5), ease: E }, at);
  K.INS = (sel, at, from, st, d) => tl.fromTo(sel, Object.assign({ opacity: 0, y: 36 }, from || {}), { opacity: 1, x: 0, y: 0, scale: 1, rotation: 0, filter: 'blur(0px)', duration: d || 0.6, ease: E, stagger: st || 0.12 }, at);
  K.OUT = (sel, at, d) => tl.to(sel, { opacity: 0, y: -16, filter: 'blur(6px)', duration: d || 0.4, ease: 'power2.inOut' }, at);
  K.WIPE = (sel, at) => tl.fromTo(sel, { clipPath: 'inset(0% 0% 0% 100%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: 0.6, ease: 'power3.inOut' }, at);
  K.DRAW = (sel, at, d, ease) => $$(sel).forEach(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L + ' ' + L;
    tl.fromTo(p, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: d || 0.7, ease: ease || 'power2.inOut' }, at); });
  K.COUNT = (sel, at, to, d, fmt) => { const o = { v: 0 }; tl.to(o, { v: to, duration: d || 1.2, ease: 'power2.out',
    onUpdate: () => { $(sel).textContent = fmt ? fmt(o.v) : Math.round(o.v).toLocaleString('en-US'); } }, at); };
  K.TYPE = (sel, at, text, d) => { const o = { n: 0 }; tl.to(o, { n: text.length, duration: d || text.length * 0.045, ease: 'none',
    onUpdate: () => { $(sel).textContent = text.slice(0, Math.round(o.n)); } }, at); };
  K.PULSE = (sel, at, n) => tl.to(sel, { scale: 1.06, duration: 0.5, ease: 'sine.inOut', yoyo: true, repeat: (n || 1) * 2 - 1 }, at);
  K.FLOAT = (sel, at, d, amp) => tl.to(sel, { y: '-=' + (amp || 12), duration: 1.6, ease: 'sine.inOut', yoyo: true, repeat: Math.max(1, Math.floor((d || 6) / 1.6)), stagger: 0.25 }, at);

  // per-topic palette (dark bases so foreground stays crisp): base, glow, blob1, blob2
  K.BG = (at, p, d) => { const o = { duration: d === undefined ? 1.4 : d, ease: 'sine.inOut' };
    tl.to('#bg', Object.assign({ backgroundColor: p[0] }, o), at); tl.to('#glow', Object.assign({ '--gc': p[1] }, o), at);
    tl.to('#b1', Object.assign({ backgroundColor: p[2] }, o), at); tl.to('#b2', Object.assign({ backgroundColor: p[3] }, o), at); };
  const P0 = cfg.palette; gsap.set('#bg', { backgroundColor: P0[0] }); gsap.set('#glow', { '--gc': P0[1] }); gsap.set('#b1', { backgroundColor: P0[2] }); gsap.set('#b2', { backgroundColor: P0[3] });
  tl.fromTo('#b1', { x: 0, y: 0 }, { x: 240, y: 160, duration: cfg.duration, ease: 'sine.inOut' }, 0);
  tl.fromTo('#b2', { x: 0, y: 0 }, { x: -260, y: -150, duration: cfg.duration, ease: 'sine.inOut' }, 0);

  // navbar state: chapters before this one are done, this one fills over the page
  const ch = cfg.chapter; // 0 = opening (nav hidden until cfg.navAt)
  for (let i = 1; i < ch; i++) { gsap.set(`#np${i}`, { className: 'p done' }); gsap.set(`#np${i} .ck`, { scale: 1 }); gsap.set(`#np${i} .fl`, { scaleX: 1 }); }
  if (ch >= 1) { gsap.set(`#np${ch}`, { className: 'p on' });
    tl.fromTo(`#np${ch} .fl`, { scaleX: 0 }, { scaleX: 1, duration: cfg.duration - 0.6, ease: 'none' }, 0.3);
    tl.fromTo(`#np${ch}`, { boxShadow: '0 0 0 0 rgba(10,240,240,0)' }, { boxShadow: '0 0 26px 0 rgba(10,240,240,.35)', duration: 0.6, ease: E }, 0.2);
    if (cfg.doneAt) { tl.to(`#np${ch} .ck`, { scale: 1, duration: 0.45, ease: E }, cfg.doneAt); } }
  if (ch === 0) gsap.set('#nav', { opacity: 0, y: -30 });
  K.NAVIN = at => tl.to('#nav', { opacity: 1, y: 0, duration: 0.8, ease: E }, at);
  K.NAVOUT = at => tl.to('#nav', { opacity: 0, y: -20, duration: 0.5, ease: 'power2.inOut' }, at);

  // chapter title card: kicker, then the box draws in from its sides, text rises; leaves by retracting
  K.TITLE = (id, at, out) => { const s = '#' + id;
    tl.fromTo(s + ' .k', { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.6, ease: E }, at);
    tl.fromTo(s + ' .t1', { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: 'power3.inOut' }, at + 0.1);
    tl.fromTo(s + ' .t2', { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: 'power3.inOut' }, at + 0.1);
    tl.fromTo(s + ' .t3', { scaleY: 0 }, { scaleY: 1, duration: 0.55, ease: 'power3.inOut' }, at + 0.55);
    tl.fromTo(s + ' .t4', { scaleY: 0 }, { scaleY: 1, duration: 0.55, ease: 'power3.inOut' }, at + 0.55);
    tl.fromTo(s + ' .tt', { opacity: 0, y: 26, filter: 'blur(10px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: E }, at + 0.35);
    tl.to(s + ' .tt', { scale: 1.025, duration: out - at - 1.2, ease: 'none' }, at + 1.2);
    tl.to(s + ' .t1', { scaleX: 0, transformOrigin: 'right', duration: 0.5, ease: 'power2.in' }, out - 0.5);
    tl.to(s + ' .t2', { scaleX: 0, transformOrigin: 'left', duration: 0.5, ease: 'power2.in' }, out - 0.5);
    tl.to(s + ' .t3, ' + s + ' .t4', { scaleY: 0, duration: 0.4, ease: 'power2.in' }, out - 0.5);
    tl.to(s + ' .tt, ' + s + ' .k', { opacity: 0, filter: 'blur(8px)', duration: 0.45, ease: 'power2.in' }, out - 0.45); };

  // subtitles: plain white, swapped on phrase times
  K.SUBS = list => { tl.set('#sub', { textContent: '' }, 0);
    list.forEach(([a, b, t], i) => { tl.set('#sub', { textContent: t }, a); const nx = list[i + 1]; if (!nx || nx[0] - b > 0.05) tl.set('#sub', { textContent: '' }, b); }); };

  K.done = () => { tl.to({}, { duration: cfg.duration }, 0); window.__timelines = window.__timelines || {}; window.__timelines[cfg.id] = tl; };
  return K;
};
