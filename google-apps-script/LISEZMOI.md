# Surveillance de secours (Google Apps Script) — installation en 5 minutes

1. Ouvre **script.google.com** avec ton compte Google habituel → **Nouveau projet**. Nomme-le « Surveillance CÔJEGO ».
2. Efface le contenu de `Code.gs` et colle **tout** le fichier `Surveillance.gs`. Enregistre (icône disquette).
3. **Propriétés du script** : icône engrenage « Paramètres du projet » → tout en bas « Propriétés du script » → *Ajouter une propriété* : nom `STATUT_URL`, valeur = l'adresse secrète que Claude t'a donnée (elle commence par `https://www.cojego.com/statut/`). Enregistre.
4. En haut, choisis la fonction **`installerDeclencheurs`** dans la liste, clique **Exécuter**. Google demande d'autoriser le script (compte → « Paramètres avancés » → « Accéder à… » → Autoriser) : c'est normal, le script envoie des mails depuis ton compte et appelle les adresses du site.
5. Choisis la fonction **`resumeQuotidien`** → **Exécuter** : tu dois recevoir un mail « 🟢 CÔJEGO : tout fonctionne (11 contrôles) » dans la minute.

C'est tout : contrôle toutes les 10 minutes, mail seulement en cas de panne ou de rétablissement, et un mail quotidien vers 8 h (s'il n'arrive pas, c'est que la surveillance est arrêtée). Pour recevoir les alertes sur téléphone : appli Gmail avec notifications activées pour ces mails.
Pour arrêter : dans le projet, icône horloge « Déclencheurs » → supprimer.

## Quelle adresse reçoit les mails ?
Le compte Google connecté dans l'onglet script.google.com. Pour le vérifier : fonction **`monAdresse`** → Exécuter → « Journal d'exécution » en bas : « Les alertes partent vers : … ».
Pour ajouter d'autres destinataires : dans le code, `const DESTINATAIRES_SUPPLEMENTAIRES = ['contact@cojego.com'];`.
