// Ponte entre o celular e o telão. Cada sala é um código secreto; nada fica guardado depois de 6 h.
import { createHash } from "node:crypto";
import { getCache } from "@vercel/functions";

const TTL = 6 * 3600, COMANDOS = new Set(["avancar", "voltar", "pausar", "som", "extras", "preta", "ir"]);
const CAB = { "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store" };
const resposta = (corpo, status = 200) => Response.json(corpo, { status, headers: CAB });
const inteiro = (v, max) => (Number.isInteger(v) && v >= 0 && v <= max ? v : null);
const cache = () => getCache({ namespace: "lapida-controle" });

function chave(request) {
  const sala = new URL(request.url).searchParams.get("sala") || "";
  return /^[A-Z2-9]{8}$/.test(sala) ? createHash("sha256").update(sala).digest("hex") : null;
}

export async function GET(request) {
  const k = chave(request);
  if (!k) return resposta({ erro: "sala inválida" }, 400);
  const c = cache(), [fila, estado] = await Promise.all([c.get(k + ":fila"), c.get(k + ":estado")]);
  return resposta({ fila: fila || [], estado: estado || null, agora: Date.now() });
}

export async function POST(request) {
  const k = chave(request), texto = k ? await request.text() : "";
  if (!k) return resposta({ erro: "sala inválida" }, 400);
  let b;
  try { b = texto.length < 1000 ? JSON.parse(texto) : null; } catch { b = null; }
  const c = cache();
  if (b?.estado) {
    const { i, p, n, total, preta, tocando, mudo, ult } = b.estado;
    if ([inteiro(i, 99), inteiro(p, 9), inteiro(n, 9), inteiro(total, 99)].includes(null)) return resposta({ erro: "estado inválido" }, 400);
    await c.set(k + ":estado", { i, p, n, total, preta: !!preta, tocando: !!tocando, mudo: !!mudo, ult: /^[a-z0-9]{6,20}$/.test(ult || "") ? ult : "", t: Date.now() }, { ttl: TTL });
    return resposta({ ok: true });
  }
  // o celular manda a lista dos últimos toques: gravar sem ler antes não perde nada se a leitura vier atrasada
  const lista = Array.isArray(b?.fila) && b.fila.length && b.fila.length <= 8 ? b.fila : null, agora = Date.now();
  const certo = (x) => COMANDOS.has(x?.cmd) && /^[a-z0-9]{6,20}$/.test(x.id || "") && inteiro(x.idade, 60000) !== null && (x.cmd !== "ir" || inteiro(x.i, 99) !== null);
  if (!lista?.every(certo)) return resposta({ erro: "comando inválido" }, 400);
  await c.set(k + ":fila", lista.map((x) => ({ id: x.id, cmd: x.cmd, t: agora - x.idade, ...(x.cmd === "ir" && { i: x.i }) })), { ttl: TTL });
  return resposta({ ok: true });
}
