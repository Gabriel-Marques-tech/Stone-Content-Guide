import sys; from pathlib import Path
AQUI = Path(__file__).parent; sys.path.insert(0, str(AQUI))
from boneco import *
OURO, PAPELAO, VERM = "#FFC533", "#C79A66", "#FF5A4F"
def respira(b, t, dx=0):
    b.tronco.scale = (1-.012*onda(t,2), 1, 1+.018*onda(t,2)); b.cab.rotation_euler = (.03*onda(t,1,.2), .05*onda(t,1), dx+.06*onda(t,1,.1)); b.piscar(t)
def moeda(loc, pai=None, R=.2):
    v = vazio(loc, pai); cilindro((0,0,0), R, .09, OURO, v, rug=.25); toro((0,0,.045), R*.78, .018, "#E3A41C", v, rug=.3); return v
def escala(o, s): o.scale = (max(s,.0001),)*3
def estala(t, a, d=.1):
    x = max(0, min(1, (t-a)/d)); return 0 if x <= 0 else 1+1.6*(x-1)**3+.6*(x-1)**2 if x < 1 else 1
def some(t): return 1-suave(t,.93,1)
def visto(pai, loc, tam, cor=BRANCO, raio=.035): return tubo([(loc[0]-tam*.5,loc[1],loc[2]),(loc[0]-tam*.12,loc[1],loc[2]-tam*.38),(loc[0]+tam*.55,loc[1],loc[2]+tam*.45)], raio, cor, pai)

def rosto():
    b = Boneco(); fr = vazio((0,-.6,1.3)); escala(b.r, 1.08)
    for sx in (-1,1):
        for sz in (-1,1): tubo([(sx*.72,0,sz*1.28),(sx*1.0,0,sz*1.28)], .03, BRANCO, fr); tubo([(sx*1.0,0,sz*1.28),(sx*1.0,0,sz*1.0)], .03, BRANCO, fr)
    rec = esfera((.86,-.6,2.46), .075, VERM, emit=.4)
    def f(t):
        respira(b,t); b.falar(falando(t)); b.mao(1,(.66+.1*onda(t,3),-.3,1.12+.06*onda(t,3,.25)),(.72,-.02,.72)); b.mao(-1,(-.52,-.22+.04*onda(t,1),.55)); escala(rec, 1 if t%.34<.2 else .001); rec.scale = [.075*x for x in rec.scale] if rec.scale[0] > .5 else rec.scale
    return f
def celular():
    b = Boneco((-.5,.1,0)); p = vazio((.52,-.1,1.02)); p.rotation_euler = (0,0,.18)
    caixa((0,0,0),(.98,.14,1.9),GRAFITE,p,r=.13,rug=.3); caixa((0,-.075,0),(.86,.03,1.74),BRANCO,p,r=.08,rug=.3); caixa((0,-.1,.77),(.24,.02,.06),GRAFITE,p,r=.03)
    d = vazio((0,-.12,.22),p); cilindro((0,0,0),.28,.08,VERDE,d,rot=(PI/2,0,0)); visto(d,(0,-.06,.02),.26)
    l = [caixa((0,-.1,z),(w,.03,.07),CINZA,p,r=.03) for z,w in ((-.28,.6),(-.45,.42),(-.62,.52))]
    def f(t):
        respira(b,t,-.25); b.falar(.8 if .2<t<.6 else 0); escala(d, estala(t,.14,.14)*some(t))
        for i,x in enumerate(l): x.scale.x = max(.001, suave(t,.3+i*.08,.45+i*.08)*some(t))
        k = vai(t,.14,.28,.6,.8); b.mao(-1,(-.6,-.2-.1*k,.6+1.0*k),(-.75,0,.75+.1*k)); b.mao(1,(.48,-.3,.85+.3*k)); b.r.location.z = .16*abs(onda(t,2))*k; p.rotation_euler.z = .18+.05*onda(t,1)
    return f
def caderno():
    b = Boneco((-.55,.15,0)); n = vazio((.45,-.05,.98)); n.rotation_euler = (-.12,0,.16)
    caixa((0,.05,0),(1.14,.1,1.6),VERDE,n,r=.06); caixa((.04,-.02,0),(1.02,.08,1.5),BRANCO,n,r=.04)
    for i in range(6): toro((-.5,-.02,-.6+.24*i),.085,.022,GRAFITE,n,rot=(PI/2,PI/2,0))
    ls = [(.36,.7),(.1,.7),(-.16,.48),(-.42,.62)]; obj = [caixa((0,-.07,z),(w,.02,.055),GRAFITE,n,r=.02) for z,w in ls]
    lp = vazio((0,0,0)); cilindro((0,0,.42),.07,.62,OURO,lp); cilindro((0,0,.05),.0,.14,PAPELAO,lp,raio2=.07,r=.005); cilindro((0,0,.77),.072,.1,"#F08A86",lp); lp.rotation_euler = (.5,-.45,0)
    def f(t):
        respira(b,t,-.3); k = min(3.999,(t/.8)*4) if t<.8 else 3.999; i = int(k); u = k-i
        for j,(x,(z,w)) in enumerate(zip(obj,ls)):
            g = (1 if j<i else u if j==i else 0)*some(t); x.scale.x = max(.001,g); x.location.x = -.3+w*g/2
        z,w = ls[i]; px = .45-.3+w*u; pz = .98+z; lp.location = (px,-.22,pz+.03*onda(t,18)); m = Vector(lp.location)+Vector((-.12,-.12,.32)); q = m-Vector((-.55,.15,0)); b.mao(1,tuple(q),(.5,-.35,.85)); b.mao(-1,(-.55,-.2,.6))
    return f
def maquininha():
    b = Boneco((-.55,.15,0)); m = vazio((.5,0,.0)); m.rotation_euler = (-.1,0,.16)
    pp = caixa((0,.03,1.75),(.5,.03,.75),BRANCO,m,r=.01); 
    ln = [caixa((0,-.0,1.95-.12*i),(.32,.03,.04),CINZA,m,r=.01) for i in range(3)]
    caixa((0,0,.82),(.88,.34,1.55),VERDE,m,r=.14,rug=.3); caixa((0,-.16,1.22),(.66,.06,.5),GRAFITE,m,r=.05,rug=.2); caixa((0,-.185,1.22),(.58,.04,.42),LIMA,m,r=.03,rug=.3)
    tx = texto("R$",(0,-.215,1.22),.26,GRAFITE,m); te = []
    for r in range(3):
        for c in range(3): te.append(caixa(((c-1)*.21,-.17,.8-r*.18),(.16,.08,.12),BRANCO if r<2 else (VERM,OURO,LIMA)[c],m,r=.035))
    def f(t):
        respira(b,t,-.3); g = suave(t,.35,.6)*some(t); pp.location.z = 1.28+.5*g
        for i,x in enumerate(ln): x.location.z = 1.5+.5*g-.12*i
        for i,x in enumerate(te): x.location.y = -.17+.04*max(0,1-abs(t-.06-.06*(i%5))*22)
        a = t<.36; px = .05*onda(t,4) if a else 0; b.mao(1,(.72+px,-.42,.72+.08*onda(t,6)) if a else (.62,-.3,.72+.75*vai(t,.36,.5,.75,.95)),(.55,-.3,.7)); b.mao(-1,(-.6,-.15,.55+.9*vai(t,.36,.5,.75,.95))); b.falar(.8 if .42<t<.8 else 0)
    return f
def predio(v, porta=True):
    caixa((0,.1,.78),(2.0,.7,1.56),BRANCO,v,r=.05); caixa((-.45,-.26,.8),(.78,.05,.62),"#BFE6F2",v,r=.04,rug=.15); caixa((-.45,-.25,.8),(.88,.04,.72),GRAFITE,v,r=.05)
    caixa((.52,-.25,.52),(.6,.05,1.04),"#3A2A22",v,r=.04); d = vazio((.23,-.28,.5),v); caixa((.28,0,0),(.56,.05,.98),VERDE,d,r=.04); esfera((.48,-.05,0),.04,OURO,d)
    caixa((0,.1,1.62),(2.1,.8,.12),GRAFITE,v,r=.04); tl = vazio((0,-.25,1.5),v)
    for i in range(7): o = caixa((-.9+.3*i,-.22,-.1),(.3,.52,.07),VERDE if i%2==0 else BRANCO,tl,r=.03); o.rotation_euler.x = .5; cilindro((-.9+.3*i,-.45,-.26),.15,.06,VERDE if i%2==0 else BRANCO,tl,rot=(PI/2,0,0))
    return d, tl
def loja():
    v = vazio((0,.55,0)); escala(v,1.08); d, tl = predio(v); caixa((0,.48,1.98),(1.2,.12,.34),LIMA,r=.06); texto("LOJA",(0,.4,1.98),.26,GRAFITE)
    b = Boneco((-.42,-.75,0)); escala(b.r,.68)
    def f(t):
        respira(b,t); d.rotation_euler.z = -1.15*vai(t,.1,.35,.75,.95); tl.rotation_euler.x = .06*onda(t,2); k = vai(t,.2,.35,.75,.9); b.mao(1,(.68,-.2,.6+.65*k+.08*onda(t,5)*k)); b.mao(-1,(-.55,-.2,.55)); b.falar(falando(t)*k)
    return f
def vitrine():
    v = vazio((.1,.3,.42)); caixa((0,0,-.2),(2.0,.7,.46),BRANCO,v,r=.03); caixa((0,.2,1.0),(1.9,.08,1.6),"#DDF3F7",v,r=.04); caixa((0,0,.14),(2.1,.8,.28),PAPELAO,v,r=.05); caixa((0,0,1.88),(2.1,.8,.16),GRAFITE,v,r=.05)
    for x in (-1,1): caixa((x*1.0,0,1.0),(.1,.8,1.6),GRAFITE,v,r=.04)
    A = vazio((-.6,-.1,.28),v); caixa((0,0,.2),(.36,.3,.4),VERDE,A); esfera((0,0,.55),.17,LIMA,A)
    M = vazio((0,-.05,.28),v); cilindro((0,0,.04),.2,.08,GRAFITE,M); cilindro((0,0,.3),.03,.5,GRAFITE,M); caixa((0,0,.72),(.44,.24,.5),VERM,M,r=.12); cilindro((-.28,0,.8),.08,.26,VERM,M,rot=(0,.7,0)); cilindro((.28,0,.8),.08,.26,VERM,M,rot=(0,-.7,0))
    C = vazio((.6,-.1,.28),v); cilindro((0,0,.2),.2,.4,OURO,C); cilindro((0,0,.5),.04,.2,VERDE,C); esfera((0,0,.64),(.2,.2,.14),VERDE,C)
    b = Boneco((-.62,-.95,0)); escala(b.r,.55)
    def f(t):
        k = vai(t,.15,.5,.8,.98); A.location = (-.6+1.2*k,-.1-.35*math.sin(PI*k),.28+.3*math.sin(PI*k)); C.location = (.6-1.2*k,-.1+.1*math.sin(PI*k),.28+.12*math.sin(PI*k)); respira(b,t); b.r.rotation_euler.z = PI*.82-.9*(k-.5); b.mao(1,(.5+.1*onda(t,1),-.45,1.0+.2*k)); b.mao(-1,(-.5,-.45,1.2-.2*k))
        M.scale = (1,1,1+.02*onda(t,2))
    return f
def rua():
    caixa((0,.1,.03),(7,1.6,.06),"#B9C3BE",r=.02); v = vazio((-.1,.8,0)); escala(v,.9); d, tl = predio(v)
    ps = [Boneco((0,0,0),camisa=c,avental=a,cabelo=h,coque=q,pele=p) for c,a,h,q,p in ((VERM,VERM,"#5A3B22",True,"#E5B48C"),("#3C6DF0","#3C6DF0","#1B1412",False,"#7A4B2E"))]
    for p in ps: escala(p.r,.5)
    def f(t):
        for i,p in enumerate(ps):
            s = 1 if i==0 else -1; u = (t+.5*i)%1; p.r.location = (s*(-1.75+3.5*u),-.35-.38*i,.06+.06*abs(onda(t,6,i*.3))); p.r.rotation_euler = (0,0,s*1.15); p.mao(1,(.5,-.35*onda(t,6),.5)); p.mao(-1,(-.5,.35*onda(t,6),.5)); p.piscar(t)
        tl.rotation_euler.x = .05*onda(t,2)
    return f
def balcao():
    b = Boneco((-.52,.35,.22)); c = Boneco((.58,.3,.22),camisa=VERM,avental=VERM,cabelo="#5A3B22",coque=True,pele="#E5B48C"); escala(b.r,.86); escala(c.r,.82)
    caixa((0,-.25,.42),(2.2,.6,.84),PAPELAO,r=.05); caixa((0,-.27,.88),(2.34,.74,.1),BRANCO,r=.04); caixa((0,-.56,.42),(1.7,.04,.4),VERDE,r=.04)
    s = vazio((0,-.35,.93)); caixa((0,0,.18),(.34,.24,.36),LIMA,s,r=.03); tubo([(-.08,0,.36),(0,0,.5),(.08,0,.36)],.02,GRAFITE,s)
    def f(t):
        k = vai(t,.1,.42,.7,.95); s.location.x = -.32+.66*k; respira(b,t,-.3); respira(c,t,.35); b.mao(1,(.2+.35*k*(1-suave(t,.5,.6)),-.6,.95)); b.mao(-1,(-.5,-.35,.85)); c.mao(-1,(-.3,-.6,.95)); c.mao(1,(.5,-.3,.8+.4*vai(t,.45,.55,.8,.9))); b.falar(falando(t) if t<.45 else 0); c.falar(falando(t) if .5<t<.9 else 0)
    return f
def dinheiro():
    b = Boneco((-.5,.15,0)); ms = [moeda((.55,-.1,.06+.1*i),R=.3) for i in range(9)]
    n = vazio((0,0,0)); caixa((0,0,0),(.8,.04,.42),VERDE,n,r=.03); cilindro((0,-.03,0),.13,.03,BRANCO,n,rot=(PI/2,0,0)); texto("R$",(0,-.055,0),.13,GRAFITE,n)
    def f(t):
        respira(b,t,-.25); 
        for i,m in enumerate(ms):
            u = max(0,min(1,(t-.05-i*.07)/.1)); m.location.z = .06+.1*i+1.6*(1-u)**2; escala(m, (0 if u<=0 else 1)*some(t)); m.rotation_euler = (.5*(1-u),.4*(1-u),0)
        k = .5+.5*onda(t,2); b.mao(-1,(-.5,-.1,1.9+.12*k),(-.82,-.05,1.3)); n.location = (-.72,-.05,2.2+.12*k); n.rotation_euler = (0,.15*onda(t,2),.15); b.mao(1,(.55,-.25,.75+.12*onda(t,3))); b.falar(.9 if t>.65 else 0)
    return f
def cartao():
    b = Boneco((0,.2,0)); c = vazio((0,-.4,1.9)); caixa((0,0,0),(1.5,.07,.94),VERDE,c,r=.08,rug=.25); caixa((0,-.02,.22),(1.5,.05,.17),GRAFITE,c,r=.01); caixa((-.48,-.04,-.08),(.24,.04,.18),OURO,c,r=.03,rug=.2); caixa((-.28,-.04,-.31),(.62,.03,.06),BRANCO,c,r=.02); caixa((.5,-.04,-.31),(.2,.03,.06),LIMA,c,r=.02)
    def f(t):
        respira(b,t); z = 1.0+1.38*vai(t,.02,.25,.8,.98); c.location.z = z; c.rotation_euler = (.1,.1*onda(t,2),.25*onda(t,1)); 
        for l in (-1,1): b.mao(l,(l*.7,-.45,z-.4+l*.05*onda(t,2)),(l*.85,-.2,.7+.25*z)); 
        b.falar(.9 if .3<t<.8 else 0); b.r.location.z = .1*abs(onda(t,2))*vai(t,.2,.3,.75,.85)
    return f
def caixas():
    b = Boneco((0,.55,0)); 
    for x,n,cr in ((-.6,"LOJA",VERDE),(.6,"CASA",LIMA)):
        for dx,dy,w,h in ((0,-.4,.98,.06),(0,.3,.98,.06),(-.46,-.05,.06,.7),(.46,-.05,.06,.7)): caixa((x+dx,-.3+dy,.36),(w,h,.72),PAPELAO,r=.02)
        caixa((x,-.75,.36),(.74,.04,.3),cr,r=.03); texto(n,(x,-.78,.36),.2,GRAFITE)
    ms = [moeda((0,0,0),R=.16) for _ in range(4)]
    def f(t):
        respira(b,t,.35*onda(t,1)); 
        for i,m in enumerate(ms):
            u = (t*1.0-i*.25)%1; l = -1 if i%2==0 else 1; w = suave(u,0,.5); m.location = (l*(.3+.3*w),-.3,1.5+.5*math.sin(PI*min(1,u*1.8))-1.2*max(0,u-.2)); m.rotation_euler = (5*u,3*u,0); escala(m, 1 if .03<u<.8 else 0)
        for l in (-1,1): b.mao(l,(l*.55,-.5,1.15+.22*max(0,l*onda(t,2))),(l*.62,-.2,.8))
        b.falar(falando(t))
    return f
def embalagem():
    b = Boneco((0,.2,0)); s = vazio((0,-.35,1)); cilindro((0,0,.32),.5,.8,PAPELAO,s,raio2=.46) if False else caixa((0,0,.35),(.86,.56,.8),PAPELAO,s,r=.04); caixa((0,-.29,.32),(.52,.03,.34),BRANCO,s,r=.03); visto(s,(0,-.32,.34),.2,VERDE,.03)
    tubo([(-.2,0,.74),(-.18,0,.98),(.18,0,.98),(.2,0,.74)],.03,GRAFITE,s)
    def f(t):
        k = vai(t,.08,.35,.75,.95); respira(b,t); s.location = (0,-.55+.4*k,0.75+1.2*k); s.rotation_euler = (0,.06*onda(t,3)*k,0)
        for l in (-1,1): b.mao(l,(l*.5,-.5+.32*k,.95+1.05*k),(l*(.7),-.15,.95+.35*k))
        b.falar(.95 if .35<t<.8 else 0)
    return f
def cozinha():
    b = Boneco((-.1,.2,0)); cilindro((0,.02,.98),.36,.26,BRANCO,b.cab); 
    for x,y in ((-.2,0),(.2,0),(0,-.14),(0,.16)): esfera((x,y,1.22),.26,BRANCO,b.cab)
    p = vazio((.55,-.55,.95)); cilindro((0,0,0),.36,.1,GRAFITE,p,raio2=.42); cilindro((-.5,0,.02),.04,.4,GRAFITE,p,rot=(0,PI/2,0)); o = esfera((0,0,.12),(.22,.22,.07),OURO,p)
    def f(t):
        k = abs(onda(t,1)); respira(b,t,-.2); o.location.z = .1+.75*k**.8; o.rotation_euler.y = 6.28*t*2; p.location.z = .95+.1*onda(t,2); b.mao(1,(.12,-.8,.95+.1*onda(t,2)),(.5,-.4,.7)); b.mao(-1,(-.6,-.2,.6+.2*k)); b.falar(.8*k)
    return f
def preco():
    b = Boneco((-.55,.15,0)); v = vazio((.6,-.1,2.3)); tubo([(0,0,0),(0,0,-.5)],.02,GRAFITE,v); tg = vazio((0,0,-.45),v)
    caixa((0,0,-.62),(.84,.12,.92),OURO,tg,r=.1); o = caixa((0,0,-.15),(.5,.115,.5),OURO,tg,r=.1); o.rotation_euler.y = PI/4; toro((0,-.05,-.1),.09,.03,GRAFITE,tg,rot=(PI/2,0,0)); texto("R$",(0,-.09,-.66),.46,GRAFITE,tg,esp=.03)
    def f(t):
        respira(b,t,-.3); v.rotation_euler = (0,.16*onda(t,1),.2); b.mao(1,(.6+.08*onda(t,1),-.4,.85)); b.mao(-1,(-.3,-.5,1.2) if .3<t<.75 else (-.55,-.2,.6)); b.falar(falando(t) if t<.6 else 0); b.cab.rotation_euler.y += .12*onda(t,1)
    return f
def folha():
    b = Boneco((-.55,.15,0)); n = vazio((.46,-.05,1.0)); n.rotation_euler = (-.1,0,.16); caixa((0,.06,0),(1.16,.08,1.72),GRAFITE,n,r=.06); caixa((0,0,-.03),(1.02,.06,1.5),BRANCO,n,r=.02); caixa((0,-.04,.8),(.44,.12,.16),OURO,n,r=.04)
    vs = []
    for i in range(4):
        z = .46-.33*i; caixa((-.3,-.04,z),(.22,.04,.22),"#DDE4E0",n,r=.04); caixa((.14,-.04,z),(.5-.08*(i%2),.03,.065),CINZA,n,r=.02); q = vazio((-.3,-.07,z),n); caixa((0,0,0),(.22,.03,.22),VERDE,q,r=.04); visto(q,(0,-.03,.01),.13,raio=.02); vs.append(q)
    def f(t):
        respira(b,t,-.3); 
        for i,q in enumerate(vs): escala(q, estala(t,.1+.17*i,.09)*some(t))
        i = min(3,max(0,int((t-.06)/.17))); b.mao(1,(.62,-.4,1.32-.28*i+.05*onda(t,6)),(.5,-.25,.85)); b.mao(-1,(-.55,-.2,.55+.8*vai(t,.75,.82,.9,.97))); b.falar(.9 if t>.72 and t<.95 else 0)
    return f
def objetos():
    b = Boneco((0,.6,0)); caixa((0,-.45,.2),(2.2,.7,.4),PAPELAO,r=.05); caixa((0,-.45,.43),(2.3,.8,.08),BRANCO,r=.03)
    A = vazio((-.7,-.45,.47)); caixa((0,0,.24),(.46,.4,.48),VERDE,A); B = vazio((0,-.55,.47)); cilindro((0,0,.28),.28,.56,LIMA,B,raio2=0,r=.02); C = vazio((.7,-.45,.47)); esfera((0,0,.26),.26,OURO,C)
    def f(t):
        respira(b,t,.4*onda(t,1,.5)); 
        for i,o in enumerate((A,B,C)):
            u = (t-.08-.28*i)/.22; h = math.sin(PI*u) if 0<u<1 else 0; o.location.z = .47+.42*h; o.rotation_euler.z = 6.28*suave(u,0,1) if i != 1 else 0; o.scale = (1-.06*h,1-.06*h,1+.1*h)
        b.mao(-1,(-.6,-.5,1.0+.25*max(0,onda(t,1,.1)))); b.mao(1,(.6,-.5,1.0+.25*max(0,-onda(t,1,.1)))); b.falar(falando(t))
    return f
def comentario():
    b = Boneco((-.42,.1,0)); B = vazio((.35,-.1,2.12)); caixa((.18,0,0),(1.16,.2,.62),BRANCO,B,r=.2); o = caixa((-.3,0,-.3),(.22,.16,.22),BRANCO,B,r=.03); o.rotation_euler.y = .8
    ps = [esfera((-.1+.28*i,-.12,0),.085,VERDE,B) for i in range(3)]
    K = vazio((.72,-.2,1.2)); caixa((0,0,0),(.66,.2,.56),VERDE,K,r=.18); h = vazio((0,-.12,.0),K)
    for s in (-1,1): esfera((s*.075,0,.05),(.1,.05,.1),BRANCO,h)
    q = caixa((0,0,-.02),(.155,.08,.155),BRANCO,h,r=.03); q.rotation_euler.y = PI/4
    def f(t):
        respira(b,t,-.2); escala(B, estala(t,.05,.14)*some(t)); escala(K, estala(t,.42,.14)*some(t)); escala(h, 1+.18*max(0,onda(t,5)))
        for i,p in enumerate(ps): p.location.z = .1*max(0,onda(t,4,-.12*i))
        b.falar(falando(t) if t<.45 else .9*(t<.8)); b.mao(1,(.6,-.35,.75+.45*vai(t,.02,.15,.8,.95)+.05*onda(t,4))); b.mao(-1,(-.55,-.2,.55+.9*vai(t,.45,.55,.8,.93)))
    return f
CENAS = {f.__name__: f for f in (rosto,celular,caderno,maquininha,loja,vitrine,rua,balcao,dinheiro,cartao,caixas,embalagem,cozinha,preco,folha,objetos,comentario)}
if __name__ == "__main__":
    modo, nomes = sys.argv[1], sys.argv[2:] or list(CENAS)
    for n in nomes:
        if modo == "ver":
            sc = palco(270,480,10); f = CENAS[n]()
            for i,t in enumerate((.3,.62)): f(t); sc.render.filepath = f"{AQUI}/ver/{n}-{i}.png"; bpy.ops.render.render(write_still=True)
        else:
            N = 36; sc = palco(486,864,14); f = CENAS[n](); sc.render.use_border = True; sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = 0,1,.14,.97 if n in ("embalagem","cartao") else .82
            a = time.time()
            for i in range(N): f(i/N); sc.render.filepath = f"{AQUI}/q/{n}/{i:03d}.png"; bpy.ops.render.render(write_still=True)
            print("PRONTO", n, round(time.time()-a), flush=True)
