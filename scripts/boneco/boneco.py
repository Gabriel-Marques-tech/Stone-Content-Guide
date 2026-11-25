"""Lojista 3D em miniatura e um palco por desenho do roteiro (Blender como módulo, Cycles)."""
import math, sys, time
from pathlib import Path
import bpy
from mathutils import Vector

PI = math.pi
def lin(h):
    h = h.lstrip("#"); v = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    return [x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in v] + [1]
MATS = {}
def mat(cor, rug=.45, emit=0, verniz=.0):
    k = (cor, rug, emit, verniz)
    if k in MATS: return MATS[k]
    m = bpy.data.materials.new(cor); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(cor); b.inputs["Roughness"].default_value = rug
    b.inputs["Coat Weight"].default_value = verniz
    if emit: b.inputs["Emission Color"].default_value = lin(cor); b.inputs["Emission Strength"].default_value = emit
    MATS[k] = m; return m
PELE, CABELO, AVENTAL, CAMISA, CALCA = "#C98A5E", "#33241E", "#F7F7F2", "#0B8F52", "#2B3A46"
BRANCO, PRETO, LIMA, VERDE, GRAFITE, CINZA = "#F7F7F2", "#141A17", "#B9F24B", "#00C862", "#27322E", "#9AA8A1"

def por(o, pai=None, cor=BRANCO, suave=True, **k):
    o.data.materials.append(mat(cor, **k)) if not isinstance(cor, bpy.types.Material) else o.data.materials.append(cor)
    if suave and o.type == "MESH":
        for p in o.data.polygons: p.use_smooth = True
    if pai: o.parent = pai
    return o
def vazio(loc=(0,0,0), pai=None):
    o = bpy.data.objects.new("v", None); bpy.context.collection.objects.link(o); o.location = loc; o.parent = pai; return o
def esfera(loc, esc, cor, pai=None, **k):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=loc); o = bpy.context.object
    o.scale = (esc,)*3 if isinstance(esc, (int, float)) else esc; return por(o, pai, cor, **k)
def caixa(loc, dim, cor, pai=None, r=.06, **k):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.scale = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = o.modifiers.new("b", "BEVEL"); b.width = min(r, min(dim)*.48); b.segments = 5
    por(o, pai, cor, **k); return o
def cilindro(loc, raio, alt, cor, pai=None, rot=(0,0,0), r=.03, raio2=None, **k):
    bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=raio, radius2=raio if raio2 is None else raio2, depth=alt, location=loc, rotation=rot); o = bpy.context.object
    b = o.modifiers.new("b", "BEVEL"); b.width = min(r, alt*.45); b.segments = 4; b.limit_method = "ANGLE"; b.angle_limit = .6
    por(o, pai, cor, suave=True, **k); return o
def toro(loc, R, r, cor, pai=None, rot=(0,0,0), **k):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=64, minor_segments=20); return por(bpy.context.object, pai, cor, **k)
def tubo(pts, raio, cor, pai=None, **k):
    c = bpy.data.curves.new("t", "CURVE"); c.dimensions = "3D"; c.bevel_depth = raio; c.bevel_resolution = 8; c.use_fill_caps = True; c.resolution_u = 24
    s = c.splines.new("BEZIER"); s.bezier_points.add(len(pts)-1); o = bpy.data.objects.new("t", c); bpy.context.collection.objects.link(o)
    mover_tubo(o, pts); por(o, pai, cor, **k); return o
def mover_tubo(o, pts):
    for p, q in zip(o.data.splines[0].bezier_points, pts):
        p.co = q; p.handle_left_type = p.handle_right_type = "AUTO"
def texto(t, loc, tam, cor, pai=None, rot=(PI/2,0,0), esp=.02):
    c = bpy.data.curves.new("x", "FONT"); c.body = t; c.size = tam; c.align_x = "CENTER"; c.align_y = "CENTER"; c.extrude = esp; c.offset = .012*tam
    o = bpy.data.objects.new("x", c); bpy.context.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; por(o, pai, cor); return o

class Boneco:
    """Cabeça grande, corpo de vinil, avental. Mãos são alvos: o braço é um tubo do ombro até elas."""
    def __init__(s, loc=(0,0,0), avental=AVENTAL, cabelo=CABELO, pele=PELE, camisa=CAMISA, coque=False, pai=None):
        s.r = vazio(loc, pai); s.tronco = vazio((0,0,0), s.r); t = s.tronco; s.pele = pele
        for x in (-.17, .17):
            cilindro((x,0,.16), .15, .34, CALCA, s.r, r=.06); esfera((x,-.06,.07), (.17,.22,.1), BRANCO, s.r)
        esfera((0,0,.66), (.43,.36,.5), camisa, t)
        esfera((0,0,.5), (.4,.34,.36), CALCA, t)
        # avental: casca na frente do tronco
        a = esfera((0,-.018,.62), (.447,.372,.47), avental, t)
        bo = a.modifiers.new("c", "BOOLEAN"); bpy.ops.mesh.primitive_cube_add(size=2, location=(0,-.62,.66)); c = bpy.context.object; c.scale = (.34,.6,.4); c.hide_render = True; c.parent = t; bo.object = c; bo.operation = "INTERSECT"
        p = esfera((0,-.018,.62), (.449,.376,.472), avental, t); bo = p.modifiers.new("c", "BOOLEAN"); bpy.ops.mesh.primitive_cube_add(size=2, location=(0,-.62,.98)); c = bpy.context.object; c.scale = (.22,.6,.2); c.hide_render = True; c.parent = t; bo.object = c; bo.operation = "INTERSECT"
        toro((0,-.01,.66), .43, .024, avental, t).scale = (1,.86,1)
        tubo([(-.19,-.26,1.02),(-.2,-.12,1.16),(-.14,.1,1.18)], .022, avental, t); tubo([(.19,-.26,1.02),(.2,-.12,1.16),(.14,.1,1.18)], .022, avental, t)
        caixa((0,-.375,.56), (.26,.05,.16), VERDE if avental == AVENTAL else BRANCO, t, r=.03)
        s.cab = vazio((0,0,1.14), t); h = s.cab
        esfera((0,0,.42), (.52,.47,.46), pele, h, rug=.5)
        for x in (-.52,.52): esfera((x,.02,.38), (.09,.07,.12), pele, h, rug=.5)
        esfera((0,-.47,.36), (.06,.06,.05), "#BC7B50", h, rug=.5)
        # cabelo: casca atrás e em cima, com topete
        cb = esfera((0,.04,.48), (.545,.49,.46), cabelo, h, rug=.6); bo = cb.modifiers.new("c", "BOOLEAN"); bpy.ops.mesh.primitive_cube_add(size=2, location=(0,-.5,.1)); c = bpy.context.object; c.scale = (.8,.62,.55); c.rotation_euler = (-.12,0,0); c.parent = h; c.hide_render = True; bo.object = c; bo.operation = "DIFFERENCE"
        for x, z, e in ((-.2,.79,.17),(.03,.83,.19),(.25,.78,.15)): esfera((x,-.27,z), (e,.16,e*.66), cabelo, h, rug=.6)
        if coque: esfera((0,.18,1.0), .2, cabelo, h, rug=.6)
        s.olhos = []
        for x in (-.18,.18):
            o = esfera((x,-.425,.46), (.055,.04,.075), PRETO, h, rug=.15); s.olhos.append(o); esfera((x+.018,-.462,.485), .015, BRANCO, h, rug=.3)
            tubo([(x-.075,-.415,.6),(x,-.425,.64),(x+.075,-.405,.605)], .019, cabelo, h)
        for x in (-.3,.3): esfera((x,-.375,.31), (.075,.03,.05), "#D9826B", h, rug=.6)
        s.sorriso = tubo([(-.12,-.452,.27),(0,-.475,.215),(.12,-.452,.27)], .018, "#6B2E22", h)
        s.boca = esfera((0,-.452,.235), (.1,.03,.07), "#5A1F1A", h, rug=.5); s.lingua = esfera((0,-.472,.205), (.06,.02,.025), "#E0736B", h)
        s.bracos = []
        for lado in (-1, 1):
            o = tubo([(0,0,0)]*3, .105, pele, t, rug=.5); m = tubo([(0,0,0)]*2, .128, camisa, t); mao = esfera((0,0,0), (.125,.12,.125), pele, t, rug=.5)
            s.bracos.append((lado, o, m, mao))
        s.mao(-1, (-.6,-.1,.5)); s.mao(1, (.6,-.1,.5)); s.falar(0)
    def mao(s, lado, alvo, cotovelo=None):
        for l, o, m, mao in s.bracos:
            if l != lado: continue
            om = Vector((l*.36,0,.92)); al = Vector(alvo)
            meio = Vector(cotovelo) if cotovelo else (om+al)/2 + Vector((l*.14, .02, -.12))
            mover_tubo(o, [om, meio, al]); mover_tubo(m, [om, om.lerp(meio,.55)]); mao.location = al
    def falar(s, a):
        ab = a > .12; s.boca.hide_render = s.lingua.hide_render = not ab; s.sorriso.hide_render = ab
        s.boca.scale = (.1+.03*(1-a), .03, .022+.048*a); s.lingua.location.z = .235-.04*a
    def piscar(s, t):
        f = .12 if .46 < t < .52 else 1
        for o in s.olhos: o.scale.z = .075*f

def palco(largura=360, altura=640, amostras=24):
    bpy.ops.wm.read_factory_settings(use_empty=True); MATS.clear()
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = amostras; sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.use_adaptive_sampling = True; sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 1
    sc.render.use_persistent_data = True; sc.render.resolution_x, sc.render.resolution_y = largura, altura; sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"; sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.9,.95,1,1); w.node_tree.nodes["Background"].inputs[1].default_value = .42
    def luz(loc, forca, tam, alvo=(0,0,1), cor=(1,1,1)):
        l = bpy.data.lights.new("l", "AREA"); l.energy = forca; l.size = tam; l.color = cor; o = bpy.data.objects.new("l", l); bpy.context.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(alvo)-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    luz((-3.2,-4,4.6), 330, 2.6, cor=(1,.97,.92)); luz((4,-3,2.6), 95, 3, cor=(.9,.97,1)); luz((2.4,3.4,3.8), 260, 2, cor=(.95,1,.95))
    bpy.ops.mesh.primitive_plane_add(size=40); bpy.context.object.is_shadow_catcher = True
    cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co); sc.camera = co
    co.location = (0,-12,2.55); co.rotation_euler = (Vector((0,0,1.2))-co.location).to_track_quat("-Z","Y").to_euler(); cam.lens = 89; cam.sensor_fit = "VERTICAL"; cam.sensor_height = 36
    return sc

def onda(t, n=1, f=0): return math.sin(2*PI*(n*t+f))
def suave(t, a, b):
    x = max(0, min(1, (t-a)/(b-a))); return x*x*(3-2*x)
def vai(t, a, b, c, d): return suave(t,a,b)-suave(t,c,d)  # sobe entre a e b, desce entre c e d
def falando(t): return max(0, .5+.5*math.sin(2*PI*6*t))*(.55+.45*math.sin(2*PI*2*t+.7)**2)
