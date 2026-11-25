// Telão: escuta o celular. Só liga se a página foi aberta uma vez com ?c=CODIGO; sem internet, o deck segue igual.
(() => {
  const url = new URL(location.href), guarda = (f) => { try { return f(); } catch { return null; } };
  if (url.searchParams.has("c")) {
    const c = url.searchParams.get("c").toUpperCase();
    guarda(() => (c ? localStorage.setItem("lapida-sala", c) : localStorage.removeItem("lapida-sala")));
    url.searchParams.delete("c"); history.replaceState(null, "", url.pathname + url.search + location.hash);
    window.__sala = c;
  }
  const sala = window.__sala || guarda(() => localStorage.getItem("lapida-sala"));
  const preta = document.createElement("div");
  preta.hidden = true; preta.style.cssText = "position:fixed;inset:0;background:#000;z-index:999"; document.body.append(preta);
  const escurecer = () => { preta.hidden = !preta.hidden; };
  addEventListener("keydown", (e) => { if (e.key === "b") escurecer(); });
  if (!/^[A-Z2-9]{8}$/.test(sala || "")) return;
  const api = (/^(127\.|localhost)/.test(location.hostname) ? "https://lapida-omega.vercel.app" : "") + "/api/controle?sala=" + sala;
  const demo = document.getElementById("demo"), na_demo = () => slides[atual].classList.contains("s-demo");
  const FAZ = {
    avancar, voltar: recuar, preta: escurecer,
    extras: () => mostrar(slides.findIndex((s) => s.classList.contains("extra"))),
    som: () => { demo.muted = !demo.muted; },
    pausar: () => { if (na_demo()) demo.paused ? demo.play().catch(() => {}) : demo.pause(); },
    ir: (x) => mostrar(x.i),
  };
  let vistos = null, ult = "", ultimo = "", enviado = 0, atividade = Date.now();
  const estado = () => ({ i: atual, p: passo, n: +slides[atual].dataset.passos || 0, total: slides.length, preta: !preta.hidden, tocando: na_demo() && !demo.paused, mudo: demo.muted, ult });
  async function contarEstado() {
    const e = JSON.stringify(estado());
    if (e === ultimo && Date.now() - enviado < 3000) return;
    ultimo = e; enviado = Date.now();
    await fetch(api, { method: "POST", body: '{"estado":' + e + "}", signal: AbortSignal.timeout(4000) });
  }
  async function volta() {
    try {
      const r = await fetch(api, { cache: "no-store", signal: AbortSignal.timeout(4000) });
      const { fila, agora } = await r.json();
      if (!vistos) vistos = new Set(fila.filter((x) => agora - x.t > 4000).map((x) => x.id)); // comando velho não vale
      for (const x of fila) {
        if (vistos.has(x.id)) continue;
        vistos.add(x.id); ult = x.id; atividade = Date.now();
        if (agora - x.t < 8000 && Object.hasOwn(FAZ, x.cmd)) FAZ[x.cmd](x); // rede caiu: não despeja comandos atrasados
      }
      contarEstado().catch(() => {});
    } catch { /* sem internet: teclado segue valendo */ }
    setTimeout(volta, Date.now() - atividade < 600000 ? 220 : 1500);
  }
  volta();
})();
