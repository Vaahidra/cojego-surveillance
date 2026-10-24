#!/usr/bin/env python3
"""Surveillance extérieure de CÔJEGO : lancée par GitHub Actions toutes les ~10 minutes, hors du serveur.
Chaque contrôle est retenté 3 fois avant d'être déclaré en échec. Code de sortie 1 si au moins un échec.
Secret attendu : STATUT_URL (adresse secrète du point de contrôle des sauvegardes) dans les secrets GitHub."""
import json, os, re, socket, ssl, sys, time, urllib.request, urllib.error, datetime

IP = "51.68.230.58"
UA = {"User-Agent": "cojego-surveillance/1.0 (+https://github.com/Vaahidra/cojego-surveillance)"}
resultats = []

class PasDeRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def requete(url, methode="GET", corps=None, suivre=True, delai=20):
    h = dict(UA)
    if corps is not None: h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corps, headers=h, method=methode)
    op = urllib.request.build_opener() if suivre else urllib.request.build_opener(PasDeRedirection)
    t0 = time.time()
    try:
        with op.open(req, timeout=delai) as r: return r.status, r.read(400000), dict(r.headers), time.time() - t0
    except urllib.error.HTTPError as e: return e.code, e.read(400000) if e.fp else b"", dict(e.headers), time.time() - t0

def essayer(nom, fonction, tentatives=3, pause=6):
    derniere = ""
    for i in range(tentatives):
        try:
            ok, detail = fonction()
            if ok: resultats.append((nom, True, detail)); return
            derniere = detail
        except Exception as e: derniere = f"{type(e).__name__}: {e}"
        if i < tentatives - 1: time.sleep(pause)
    resultats.append((nom, False, derniere))

def http(url, attendu=200, contient=None, interdit=None, lenteur=8.0, **kw):
    def f():
        code, corps, _, d = requete(url, **kw)
        if code != attendu: return False, f"code {code} (attendu {attendu})"
        txt = corps.decode("utf-8", "ignore")
        if contient and contient not in txt: return False, f"texte « {contient} » absent"
        if interdit and interdit in txt: return False, f"texte interdit « {interdit} » présent"
        if d > lenteur: return False, f"trop lent : {d:.1f} s"
        return True, f"{code} en {d:.2f} s"
    return f

def redirection(url, vers):
    def f():
        code, _, h, _ = requete(url, suivre=False)
        loc = h.get("Location", "")
        return (code in (301, 308) and loc.rstrip("/") == vers.rstrip("/")), f"{code} -> {loc or '-'}"
    return f

def tls(hote, jours_min=14):
    def f():
        ctx = ssl.create_default_context()
        with socket.create_connection((hote, 443), timeout=15) as s, ctx.wrap_socket(s, server_hostname=hote) as c:
            fin = ssl.cert_time_to_seconds(c.getpeercert()["notAfter"])
        j = int((fin - time.time()) / 86400)
        return j >= jours_min, f"expire dans {j} jours"
    return f

def doh(nom, type_):
    r = urllib.request.Request(f"https://cloudflare-dns.com/dns-query?name={nom}&type={type_}", headers={"accept": "application/dns-json", **UA})
    with urllib.request.urlopen(r, timeout=15) as x: d = json.load(x)
    return [a["data"].strip('"') for a in d.get("Answer", [])]

def dns_a(nom):
    def f():
        a = sorted(set(doh(nom, "A"))); return a == [IP], f"{nom} -> {', '.join(a) or 'aucune'}"
    return f

def dns_mail():
    def f():
        mx = " ".join(doh("cojego.com", "MX")).lower(); spf = " ".join(doh("cojego.com", "TXT")); dk = doh("dkim._domainkey.cojego.com", "TXT")
        pb = []
        if "smtp.google.com" not in mx: pb.append("MX Google absent")
        if "v=spf1" not in spf or "193.203.239.123" not in spf: pb.append("SPF modifié")
        if not any("v=DKIM1" in x for x in dk): pb.append("DKIM absent")
        return not pb, "MX/SPF/DKIM en place" if not pb else ", ".join(pb)
    return f

def sauvegarde():
    def f():
        url = os.environ.get("STATUT_URL", "")
        if not url: return False, "STATUT_URL non défini dans les secrets"
        code, corps, _, _ = requete(url)
        if code != 200: return False, f"point de contrôle : code {code}"
        d = json.loads(corps.decode())
        if not d.get("ok"): return False, f"dernière sauvegarde en ÉCHEC : {d.get('erreur', '?')} ({d.get('date', '?')})"
        t = datetime.datetime.strptime(d["derniere_sauvegarde"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        h = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
        return h < 30 and d.get("copie_hors_serveur") is True, f"dernière sauvegarde il y a {h:.1f} h, copie hors serveur: {d.get('copie_hors_serveur')}"
    return f

def faux_login():
    def f():
        code, _, _, _ = requete("https://app.cojego.com/api/auth/login", "POST", json.dumps({"identifier": "surveillance@exemple.invalid", "password": "x"}).encode())
        return code == 401, f"{code} (401 attendu ; 405 = login cassé)"
    return f

def pico():
    def f():
        code, corps, _, _ = requete("https://app.cojego.com/api/assistant/status")
        d = json.loads(corps.decode()) if code == 200 else {}
        return code == 200 and d.get("enabled") is True, f"{code}, enabled={d.get('enabled')}"
    return f

def sitemap():
    def f():
        code, corps, _, _ = requete("https://www.cojego.com/sitemap-0.xml"); n = corps.decode("utf-8", "ignore").count("<loc>")
        return code == 200 and n >= 85, f"{code}, {n} URL"
    return f

# ----- contrôles -----
essayer("Site vitrine : accueil", http("https://www.cojego.com/", contient="CÔJEGO"))
essayer("Site vitrine : blog", http("https://www.cojego.com/blog/"))
essayer("Site vitrine : contact", http("https://www.cojego.com/contact/"))
essayer("Site vitrine : sitemap", sitemap())
essayer("cojego.com -> www", redirection("https://cojego.com/", "https://www.cojego.com"))
essayer("Application web", http("https://app.cojego.com/", contient="<div id"))
essayer("API : compteur public", http("https://app.cojego.com/api/site-stats", contient="controles"))
essayer("API : faux identifiants refusés (401)", faux_login())
essayer("Pico (assistant) actif", pico())
essayer("Bourse", http("https://bourse.cojego.com/"))
essayer("Bourse : API publique", http("https://bourse.cojego.com/api/bourse/public/stats"))
essayer("Formation", http("https://formation.cojego.com/"))
for h in ("www.cojego.com", "app.cojego.com", "bourse.cojego.com", "formation.cojego.com"): essayer(f"Certificat {h}", tls(h))
essayer("DNS cojego.com", dns_a("cojego.com"))
essayer("DNS www.cojego.com", dns_a("www.cojego.com"))
essayer("DNS du courrier (MX, SPF, DKIM)", dns_mail())
essayer("Sauvegarde de la base (hors serveur)", sauvegarde())

if os.environ.get('TEST_ECHEC') == '1': resultats.append(('TEST D\'ALERTE (simulation, rien n\'est cassé)', False, 'échec simulé volontairement pour vérifier la chaîne d\'alerte'))

# ----- compte rendu -----
echecs = [r for r in resultats if not r[1]]
lignes = [f"{'✅' if ok else '❌'} {n} — {d}" for n, ok, d in resultats]
rapport = ("## 🔴 INCIDENT CÔJEGO — %d contrôle(s) en échec\n\n" % len(echecs) if echecs else "## 🟢 CÔJEGO : tout fonctionne (%d contrôles)\n\n" % len(resultats)) + "\n".join(lignes)
print(rapport)
if os.environ.get("GITHUB_STEP_SUMMARY"): open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(rapport + "\n")
open("rapport.md", "w").write(rapport + f"\n\n_Contrôle du {datetime.datetime.now(datetime.timezone.utc):%d/%m/%Y à %H:%M} UTC._\n")
sys.exit(1 if echecs else 0)
