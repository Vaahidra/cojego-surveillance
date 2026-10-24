# Surveillance extérieure de CÔJEGO

Ce dépôt contrôle, **depuis GitHub (hors du serveur)** et toutes les ~10 minutes, que tout fonctionne :
sites (vitrine, app, Bourse, Formation), API (compteur, faux login refusé), Pico, certificats (≥ 14 jours),
DNS (cojego.com, www), courrier (MX, SPF, DKIM) et **la sauvegarde nocturne de la base** (moins de 30 h, copie hors serveur).

- **Alerte** : en cas d'échec, une « issue » rouge « Incident CÔJEGO » est ouverte et assignée (mail + notification de l'appli mobile GitHub) ; elle est close automatiquement au rétablissement.
- **Secret** : `STATUT_URL` (adresse secrète du point de contrôle des sauvegardes) dans *Settings → Secrets and variables → Actions*.
- **Lancer à la main** : onglet *Actions → Surveillance CÔJEGO → Run workflow*.
- Le dépôt ne contient aucun secret. Limite : GitHub peut retarder un planning de quelques minutes en période de forte charge.
