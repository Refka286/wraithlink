# Single source of truth for the educational "Outils" reference page and the
# inline contextual explanation shown in the action-submission form. Risk
# tier/score data is deliberately NOT duplicated here - the API layer
# (app/api/tools.py) attaches it live from app.risk_engine so this file can
# never drift out of sync with the actual classification logic.

TOOLS: dict[str, dict] = {
    "nmap": {
        "label": "Nmap",
        "what_is": (
            "Un scanner de ports reseau, utilise pour decouvrir quels services ecoutent sur une "
            "machine cible et sur quels ports."
        ),
        "how_it_works": (
            "En profil syn-stealth, Nmap envoie un paquet TCP SYN a chaque port cible et observe la "
            "reponse : un SYN-ACK signifie que le port est ouvert, un RST qu'il est ferme. La poignee "
            "de main TCP n'est jamais completee (pas d'ACK final), ce qui rend le scan plus discret "
            "qu'une connexion TCP complete et evite de laisser une session applicative journalisee "
            "cote cible. Ce mode necessite un acces bas niveau aux sockets reseau (capacite "
            "CAP_NET_RAW)."
        ),
        "example_finding": {
            "type": "open_port",
            "description": "Port 445 ouvert, service microsoft-ds identifie.",
        },
        "profiles": {
            "syn-stealth": {
                "label": "SYN Stealth (-sS)",
                "explanation": (
                    "Scan furtif par defaut de Nmap : ne complete jamais la connexion TCP, ce qui le "
                    "rend peu detectable par une journalisation applicative classique tout en restant "
                    "rapide sur de larges plages de ports."
                ),
            },
        },
    },
    "ffuf": {
        "label": "ffuf",
        "what_is": (
            "Un outil de decouverte de contenu web par force brute, utilise pour trouver des "
            "repertoires, fichiers ou endpoints non references publiquement."
        ),
        "how_it_works": (
            "ffuf substitue le mot-cle FUZZ dans l'URL cible par chaque entree d'une liste de mots "
            "(wordlist) et envoie une requete HTTP par entree. Les reponses dont le code de statut "
            "correspond aux filtres configures (200-299, 301, 302, 307, 401, 403, 405 par defaut) "
            "sont retenues comme chemins potentiellement decouverts. Sur les applications a page "
            "unique (SPA) qui renvoient la meme page pour toute route inconnue, un filtrage "
            "supplementaire par taille de reponse dominante est applique automatiquement pour "
            "eliminer les faux positifs."
        ),
        "example_finding": {
            "type": "discovered_path",
            "description": "/admin decouvert, code de reponse 200.",
        },
        "profiles": {
            "default": {
                "label": "Wordlist par defaut",
                "explanation": (
                    "Utilise le dictionnaire commun installe sur la plateforme (dirb/common.txt) : "
                    "couverture generaliste, volume de requetes modere, sans authentification prealable."
                ),
            },
        },
    },
    "nuclei": {
        "label": "Nuclei",
        "what_is": (
            "Un scanner de vulnerabilites base sur des signatures (templates), utilise pour detecter "
            "des failles connues, des expositions de configuration et des erreurs courantes."
        ),
        "how_it_works": (
            "Nuclei compare la cible a une bibliotheque de gabarits YAML, chacun decrivant une "
            "requete a envoyer et une condition de correspondance (expression reguliere, code de "
            "statut, contenu de la reponse). Lorsque la condition est verifiee, le gabarit produit un "
            "constat avec sa propre severite (info a critique) et une reference (CVE, CWE...). La "
            "bibliotheque de gabarits est mise a jour independamment de l'outil."
        ),
        "example_finding": {
            "type": "prometheus-metrics",
            "description": "Endpoint /metrics expose publiquement, severite moyenne.",
        },
        "profiles": {
            "default": {
                "label": "Gabarits par defaut",
                "explanation": (
                    "Execute l'ensemble des gabarits de severite low, medium, high et critical : "
                    "couverture large sans mode agressif, trafic proche d'une navigation normale."
                ),
            },
            "aggressive": {
                "label": "Mode agressif",
                "explanation": (
                    "Active des gabarits plus intrusifs (tests actifs susceptibles de modifier un "
                    "etat ou de generer davantage de requetes par cible) pour maximiser la couverture "
                    "au prix d'un trafic plus visible."
                ),
            },
        },
    },
    "sqlmap": {
        "label": "sqlmap",
        "what_is": (
            "Un outil specialise dans la detection et l'exploitation d'injections SQL sur des "
            "parametres d'application web."
        ),
        "how_it_works": (
            "sqlmap injecte des payloads dans les parametres identifies (query string, corps POST, "
            "cookies, en-tetes) et compare le comportement du serveur - temps de reponse, contenu "
            "retourne, messages d'erreur - pour detecter plusieurs familles de techniques : "
            "boolean-based blind, error-based, UNION-based, time-based blind et stacked queries. Le "
            "profil aggressive augmente le niveau (--level) et le risque (--risk) des tests envoyes, "
            "donc le nombre de requetes et les techniques testees."
        ),
        "example_finding": {
            "type": "sql_injection",
            "description": "Parametre 'id' vulnerable a une injection de type boolean-based blind.",
        },
        "profiles": {
            "aggressive": {
                "label": "Mode agressif (level 3 / risk 2)",
                "explanation": (
                    "Teste davantage de points d'injection et de techniques (level eleve) avec des "
                    "payloads plus susceptibles de perturber l'application (risk eleve) : necessite "
                    "une validation humaine avant execution."
                ),
            },
        },
    },
    "netexec": {
        "label": "NetExec",
        "what_is": (
            "Un outil d'enumeration et d'attaque Active Directory (successeur de CrackMapExec), "
            "utilise pour authentifier, enumerer et tester des techniques d'attaque contre un "
            "domaine Windows."
        ),
        "how_it_works": (
            "NetExec s'authentifie aupres du controleur de domaine (LDAP) avec des identifiants "
            "fournis, puis execute le module selectionne. Le comportement technique differe "
            "entierement selon le profil - voir le detail de chaque profil ci-dessous."
        ),
        "example_finding": {
            "type": "kerberoastable_account",
            "description": "Compte de service avec SPN detecte, hash TGS-REP extrait.",
        },
        "profiles": {
            "kerberoast": {
                "label": "Kerberoasting",
                "explanation": (
                    "Recherche les comptes de service disposant d'un SPN (Service Principal Name) "
                    "puis demande, pour chacun, un ticket de service Kerberos (TGS). Ce ticket est "
                    "chiffre avec le hash NTLM du compte de service et peut etre soumis hors ligne "
                    "(hashcat, john) pour tenter de retrouver le mot de passe en clair, sans generer "
                    "d'echec d'authentification journalise."
                ),
            },
            "dcsync": {
                "label": "DCSync",
                "explanation": (
                    "Exploite les droits etendus Active Directory Replicating Directory Changes / "
                    "Replicating Directory Changes All pour se faire passer, aupres du controleur de "
                    "domaine, pour un autre controleur de domaine legitime et repliquer l'integralite "
                    "de la base NTDS.dit - y compris les hachages de mots de passe de tous les comptes "
                    "du domaine, dont krbtgt. Cette action est irreversible au sens du modele de "
                    "risque de la plateforme : une fois les hachages extraits, l'exposition ne peut "
                    "plus etre annulee."
                ),
            },
        },
    },
    "bloodhound": {
        "label": "BloodHound",
        "what_is": (
            "Un outil de cartographie des relations Active Directory, utilise pour visualiser les "
            "chemins d'attaque possibles vers des comptes ou groupes a privileges eleves."
        ),
        "how_it_works": (
            "Le collecteur (bloodhound-python) interroge LDAP et SMB avec des identifiants valides "
            "pour recuperer la structure du domaine : utilisateurs, groupes, appartenances, ACL, "
            "sessions actives et relations de confiance. Ces donnees sont ensuite assemblees en un "
            "graphe qui met en evidence les chemins d'escalade de privileges (par exemple, un "
            "utilisateur standard menant a Domain Admins via une chaine de droits deleguee)."
        ),
        "example_finding": {
            "type": "bloodhound_users_collected",
            "description": "47 objets utilisateur collectes et integres au graphe de relations.",
        },
        "profiles": {
            "collect": {
                "label": "Collecte complete (-c All)",
                "explanation": (
                    "Collecte l'ensemble des categories d'objets disponibles (utilisateurs, groupes, "
                    "ordinateurs, ACL, sessions, confiances) en une seule passe : lecture seule, "
                    "equivalent a une enumeration LDAP/SMB avec un compte a faible privilege."
                ),
            },
        },
    },
    "acunetix": {
        "label": "Acunetix",
        "what_is": (
            "Un scanner de vulnerabilites web commercial (DAST), utilise pour detecter des failles "
            "applicatives (injections, XSS, mauvaises configurations...) via des attaques actives "
            "envoyees directement a la cible."
        ),
        "how_it_works": (
            "Acunetix s'utilise via son API REST plutot qu'en ligne de commande : la plateforme cree "
            "une cible (target), lance un scan avec un profil donne, puis interroge periodiquement "
            "l'etat du scan jusqu'a completion avant de recuperer la liste des vulnerabilites "
            "detectees. Le profil 'full-scan' active l'ensemble des tests, y compris des sondes "
            "actives (injection de payloads) qui modifient le comportement observe de la cible."
        ),
        "example_finding": {
            "type": "xss_reflected",
            "description": "Injection XSS reflechie detectee sur le parametre 'q' de /search.",
        },
        "profiles": {
            "full-scan": {
                "label": "Scan complet",
                "explanation": (
                    "Execute l'integralite des tests Acunetix (DeepScan, injections, XSS, "
                    "configurations) : couverture maximale au prix d'un trafic d'attaque actif et "
                    "visible, comparable a un scan actif ZAP."
                ),
            },
        },
        # honest disclosure surfaced verbatim on the "Outils" reference page -
        # see AcunetixAdapter (app/adapters/acunetix.py): it returns a clear
        # "not configured" error instead of running until this changes
        "license_note": (
            "Acunetix necessite une licence commerciale non disponible actuellement sur cette "
            "plateforme. L'adapteur est implemente et pret a l'integration (architecture API REST : "
            "creation de cible, lancement de scan, recuperation des vulnerabilites) mais n'a pas ete "
            "teste contre une instance reelle faute d'acces. Tant qu'aucune cle API n'est configuree "
            "(ACUNETIX_API_KEY / ACUNETIX_BASE_URL), toute tentative d'execution renvoie une erreur "
            "explicite plutot que d'echouer silencieusement."
        ),
    },
}
