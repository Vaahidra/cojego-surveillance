/**
 * Surveillance de secours de CÔJEGO — Google Apps Script (tourne chez Google, indépendant d'OVH et de GitHub).
 * - Toutes les 10 minutes : contrôle des sites, de l'API, de Pico, de la sauvegarde de la base.
 * - Mail UNIQUEMENT quand l'état change (🔴 panne / 🟢 rétabli), plus un rappel toutes les 6 h si la panne continue.
 * - Chaque matin vers 8 h : un mail « tout fonctionne » (si tu ne le reçois pas, c'est la surveillance elle-même qui est en panne).
 * Installation : voir LISEZMOI.md (5 minutes). Le secret STATUT_URL va dans « Propriétés du script », jamais dans le code.
 */
const IP = '51.68.230.58';
/** Adresses SUPPLÉMENTAIRES qui reçoivent aussi les alertes (en plus du compte qui a installé le script). Ex. : ['contact@cojego.com']. Laisser vide pour ne pas en ajouter. */
const DESTINATAIRES_SUPPLEMENTAIRES = [];
const destinataires = () => [Session.getEffectiveUser().getEmail()].concat(DESTINATAIRES_SUPPLEMENTAIRES).join(',');
const HTTP = (url, opts) => { const t0 = Date.now(); const r = UrlFetchApp.fetch(url, Object.assign({ muteHttpExceptions: true, followRedirects: true, headers: { 'User-Agent': 'cojego-surveillance-google/1.0' } }, opts || {})); return { code: r.getResponseCode(), txt: r.getContentText(), h: r.getHeaders(), ms: Date.now() - t0 }; };

const CONTROLES = [
  ['Site vitrine : accueil', () => { const r = HTTP('https://www.cojego.com/'); return [r.code === 200 && r.txt.indexOf('CÔJEGO') >= 0 && r.ms < 9000, `${r.code} en ${r.ms} ms`]; }],
  ['Site vitrine : blog', () => { const r = HTTP('https://www.cojego.com/blog/'); return [r.code === 200, `${r.code}`]; }],
  ['cojego.com -> www', () => { const r = HTTP('https://cojego.com/', { followRedirects: false }); const l = (r.h.Location || r.h.location || ''); return [[301, 308].indexOf(r.code) >= 0 && l.replace(/\/$/, '') === 'https://www.cojego.com', `${r.code} -> ${l}`]; }],
  ['Application web', () => { const r = HTTP('https://app.cojego.com/'); return [r.code === 200, `${r.code}`]; }],
  ['API : compteur public', () => { const r = HTTP('https://app.cojego.com/api/site-stats'); return [r.code === 200 && r.txt.indexOf('controles') >= 0, `${r.code}`]; }],
  ['API : faux identifiants refusés (401)', () => { const r = HTTP('https://app.cojego.com/api/auth/login', { method: 'post', contentType: 'application/json', payload: JSON.stringify({ identifier: 'surveillance@exemple.invalid', password: 'x' }) }); return [r.code === 401 || r.code === 429, `${r.code} (401 attendu ; 429 = limite de tentatives, l'API répond ; 405 ou 5xx = login cassé)`]; }],
  ['Pico (assistant) actif', () => { const r = HTTP('https://app.cojego.com/api/assistant/status'); let ok = false; try { ok = JSON.parse(r.txt).enabled === true; } catch (e) {} return [r.code === 200 && ok, `${r.code}, enabled=${ok}`]; }],
  ['Bourse', () => { const r = HTTP('https://bourse.cojego.com/'); return [r.code === 200, `${r.code}`]; }],
  ['Bourse : API publique', () => { const r = HTTP('https://bourse.cojego.com/api/bourse/public/stats'); return [r.code === 200, `${r.code}`]; }],
  ['Formation', () => { const r = HTTP('https://formation.cojego.com/'); return [r.code === 200, `${r.code}`]; }],
  ['Sauvegarde de la base (hors serveur)', () => {
    const url = PropertiesService.getScriptProperties().getProperty('STATUT_URL'); if (!url) return [false, 'STATUT_URL absent des propriétés du script'];
    const r = HTTP(url); if (r.code !== 200) return [false, `point de contrôle : ${r.code}`];
    const d = JSON.parse(r.txt); if (!d.ok) return [false, `dernière sauvegarde EN ÉCHEC : ${d.erreur || '?'}`];
    const h = (Date.now() - new Date(d.derniere_sauvegarde).getTime()) / 3600000; return [h < 30 && d.copie_hors_serveur === true, `il y a ${h.toFixed(1)} h, copie hors serveur : ${d.copie_hors_serveur}`];
  }],
];

function essayer(fn) { let dernier = [false, '']; for (let i = 0; i < 3; i++) { try { dernier = fn(); if (dernier[0]) return dernier; } catch (e) { dernier = [false, String(e).slice(0, 120)]; } if (i < 2) Utilities.sleep(4000); } return dernier; }

function lancerControles() { return CONTROLES.map(([nom, fn]) => { const [ok, detail] = essayer(fn); return { nom, ok, detail }; }); }

function controler() {
  const P = PropertiesService.getScriptProperties(); const res = lancerControles(); const pannes = res.filter(r => !r.ok);
  const avant = P.getProperty('ETAT') || 'OK'; const maintenant = Date.now(); const dernierMail = Number(P.getProperty('DERNIER_MAIL') || 0);
  const ligne = r => `${r.ok ? '✅' : '❌'} ${r.nom} — ${r.detail}`; const corps = res.map(ligne).join('\n');
  const dest = destinataires();
  if (pannes.length && (avant === 'OK' || maintenant - dernierMail > 6 * 3600 * 1000)) {
    MailApp.sendEmail(dest, `🔴 CÔJEGO : ${pannes.length} problème(s) détecté(s)`, `La surveillance de secours a détecté :\n\n${pannes.map(ligne).join('\n')}\n\nDétail complet :\n${corps}\n\n${new Date().toLocaleString('fr-FR', { timeZone: 'Europe/Paris' })}`);
    P.setProperty('DERNIER_MAIL', String(maintenant));
  }
  if (!pannes.length && avant !== 'OK') MailApp.sendEmail(dest, '🟢 CÔJEGO : rétabli', `Tout fonctionne de nouveau.\n\n${corps}\n\n${new Date().toLocaleString('fr-FR', { timeZone: 'Europe/Paris' })}`);
  P.setProperty('ETAT', pannes.length ? 'PANNE' : 'OK');
}

function resumeQuotidien() {
  const res = lancerControles(); const pannes = res.filter(r => !r.ok);
  MailApp.sendEmail(destinataires(), pannes.length ? `🔴 CÔJEGO : ${pannes.length} problème(s) ce matin` : `🟢 CÔJEGO : tout fonctionne (${res.length} contrôles)`, res.map(r => `${r.ok ? '✅' : '❌'} ${r.nom} — ${r.detail}`).join('\n') + '\n\n(Mail quotidien de la surveillance de secours : si tu ne le reçois pas un matin, la surveillance elle-même est arrêtée.)');
}

/** À lancer UNE SEULE FOIS à la main : crée les déclencheurs (toutes les 10 min + chaque matin vers 8 h). */
function installerDeclencheurs() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('controler').timeBased().everyMinutes(10).create();
  ScriptApp.newTrigger('resumeQuotidien').timeBased().everyDays(1).atHour(8).inTimezone('Europe/Paris').create();
}

/** Pour savoir à quelle adresse partent les mails : choisir cette fonction, Exécuter, puis ouvrir « Journal d'exécution » (en bas). */
function monAdresse() { Logger.log('Les alertes partent vers : ' + destinataires()); }
