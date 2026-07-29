# Plan de Travail : Projet AegisPen
**Plateforme d'Automation de Tests d'Intrusion Guidée par le Risque pour Applications Web & Active Directory**  
*Projet de Fin d'Études (PFE) / Capstone Project*  
**Auteur :** Refa  
**Date :** Juillet 2026  

---

## 1. Résumé Exécutif & Problématique

### 1.1 Présentation du Projet
**AegisPen** est une plateforme d'orchestration et d'automatisation des tests d'intrusion (pentest) ciblant les applications Web et les environnements Active Directory (AD). Son objectif principal est d'automatiser les tâches répétitives et à faible risque (reconnaissance, énumération, découverte initiale de vulnérabilités) tout en conservant une supervision humaine stricte (« *Human-in-the-Loop* ») pour toute action présentant un risque opérationnel.

### 1.2 Problématique
* **Lenteur des tests manuels :** Une part significative d'un engagement de pentest est consacrée à des tâches mécaniques (scans de ports, énumération de sous-domaines, recherche de fichiers/répertoires, identification de comptes Kerberoastables).
* **Limites des outils d'IA totalement autonomes :** L'automatisation non supervisée présente de graves risques de sécurité (crashs de systèmes en production, altération irréversible de données) et souffre d'un manque de confiance de la part des entreprises et des clients.
* **Positionnement d'AegisPen :** Trouver le juste milieu en automatisant ce qui est sûr, et en imposant une prise de décision humaine explicite avec deux options motivées (conservatrice vs. agressive) dès que le niveau de risque s'élève.

---

## 2. Objectifs du Projet

1. **Automation de bout en bout (Recon/Énumération) :** Traiter les volets Web et Active Directory dans des environnements de laboratoire contrôlés.
2. **Modèle quantitatif de scoring du risque :** Classifier automatiquement chaque action en trois catégories (*Automatique*, *Soumis à approbation*, *Interdit*).
3. **Workflow d'approbation à choix binaire :** Proposer au pentesteur deux options argumentées (Option A conservatrice, Option B agressive) lors des points de décision critiques.
4. **Journalisation et Traçabilité (Audit Trail) :** Archiver l'intégralité des actions automatiques, des décisions humaines, des justifications et des preuves associées.
5. **Génération automatique de rapports PDF :** Produire un rapport d'audit professionnel prêt à être livré au client.
6. **Packaging Portfolio & PFE :** Livrer un projet complet, documenté et prêt pour démonstration technique et soutenance.

---

## 3. Cadre Éthique, Légal & Périmètre (Scope)

### 3.1 Règles d'Engagement Rigoereuses
* **Cibles autorisées uniquement :** Infrastructure propre ou laboratoires de vulnérabilités dédiés (GOAD/GOAD-Light, DVWA, OWASP Juice Shop, HackTheBox/TryHackMe sous conditions).
* **Isolation réseau :** Exécution au sein d'un réseau hôte uniquement ou réseau Docker/VirtualBox privé isolé (aucun pont direct sur le réseau domestique ou internet).
* **Étape de validation de portée intégrée :** Obligation de valider explicitement le périmètre et l'autorisation avant tout lancement d'exécution.

### 3.2 Périmètre Applicatif
* **En périmètre :** Applications Web et environnements Active Directory en lab.
* **Hors périmètre :** Attaques Cloud, ingénierie sociale, attaques physiques, ou toute action sur un système non autorisé.

---

## 4. Automation Stratifiée par le Risque (Tiers de Risque)

| Niveau (Tier) | Définition | Acteur | Exemples d'actions |
| :--- | :--- | :--- | :--- |
| **Automatique** | Lecture seule, actions réversibles, faible impact et faible bruit. | Plateforme (sans confirmation) | Scan de ports (Nmap), énumération DNS/LDAP anonyme, analyse de headers, inspection `robots.txt`. |
| **Soumis à approbation** | Modification d'état potentielle, trafic important, extraction de données sensibles. | Pentesteur (Choix entre 2 options) | Scans actifs (ZAP, Nuclei avancé), confirmation SQLi/XSS, extraction de hashes Kerberoast/AS-REP. |
| **Interdit** | Action destructive, irréversible ou hors périmètre éthique. | Bloqué par la plateforme | Chiffrement type Ransomware, brute-force massif provoquant un verrouillage de compte, DCSync non autorisé. |

---

## 5. Architecture Système & Stack Technique

### 5.1 Architecture Globale
La plateforme repose sur un modèle d'orchestrateur composé de :
* **Tableau de bord Web (React) :** Visualisation en direct de l'engagement, affichage du fil d'actualité des découvertes et interface d'approbation.
* **API Orchestrateur (FastAPI) :** Gestion de la machine à états de l'engagement (Recon $ightarrow$ Scan $ightarrow$ Validation $ightarrow$ Exploitation $ightarrow$ Rapport).
* **Moteur de Risque (Risk Engine) :** Calcul du score de risque d'une action ($	ext{Score} = 	ext{Impact} 	imes rac{1}{	ext{Réversibilité}} 	imes 	ext{Détectabilité}$).
* **Porte d'Approbation (Approval Gate) :** Mettre en pause l'exécution et présenter l'Option A (Conservatrice) et l'Option B (Agressive).
* **File de Tâches (Celery + Redis) :** Exécution asynchrone des outils de sécurité.
* **Couche d'Adaptateurs d'Outils (Tool Adapters) :** Normalisation des entrées/sorties des outils CLI sous un schéma JSON commun.
* **Base de Données (PostgreSQL) :** Stockage des preuves, des vulnérabilités, et du journal d'audit complet.
* **Moteur de Rapport (Reporting Engine) :** Génération du rapport final au format PDF via WeasyPrint ou Pandoc.

### 5.2 Stack Technique

| Composant | Technologie Choisie | Rationale / Justification |
| :--- | :--- | :--- |
| **Backend API** | Python / FastAPI | Performance asynchrone, typage, intégration naturelle avec l'écosystème cyber. |
| **Orchestration / File** | Celery + Redis | Gestion robuste des tâches longues sans bloquer l'API. |
| **Frontend** | React + TypeScript + Tailwind | Interface réactive, claire et moderne. |
| **Base de Données** | PostgreSQL | Structuration relationnelle solide + support JSONB pour logs bruts. |
| **Outils Web** | Nmap, ffuf, Nuclei, sqlmap, OWASP ZAP | Standard de l'industrie, scriptables. |
| **Outils AD** | NetExec (nxc), BloodHound CE, Impacket | Références modernes pour les audits Active Directory. |
| **Laboratoire** | GOAD-Light, OWASP Juice Shop, Docker | Environnements vulnérables réalistes et reproductibles. |
| **Rapports** | WeasyPrint / HTML to PDF | Mise en page professionnelle et personnalisable. |

---

## 6. Planning & Feuille de Route (12 Semaines)

```
[S01-S02] Phase 0 : Fondations & Lab Setup
  ├── Configuration VirtualBox / Docker / GOAD-Light / Juice Shop
  └── Isolation réseau & vérification des accès

[S03-S04] Phase 1 : MVP Automation Reconnaissance
  ├── Wrappers Python pour Nmap, ffuf, Nuclei
  └── Normalisation des résultats en JSON

[S05]     Phase 2 : Dashboard v1 & API FastAPI
  ├── Développement de l'API REST de base
  └── Interface Web React pour la lecture des résultats de recon

[S06-S07] Phase 3 : Moteur de Risque & Workflow d'Approbation
  ├── Algorithme de scoring de risque
  └── Machine à états (Pause / Reprise) + UI des 2 options

[S08]     Phase 4 : Module Active Directory
  ├── Intégration NetExec + BloodHound CE
  └── Détection Kerberoasting / AS-REP Roasting

[S09]     Phase 5 : Module Web Approfondi
  ├── Intégration de sqlmap & OWASP ZAP sous porte d'approbation
  └── Scénario d'exploitation guidée sur Juice Shop

[S10]     Phase 6 : Moteur de Reporting
  ├── Modèle de rapport PDF client
  └── Exportation automatique à partir de PostgreSQL

[S11-S12] Phase 7 : Polissage & Packaging Portfolio
  ├── Docker Compose global
  ├── Rédaction du README, enregistrement démo vidéo
  └── Preparation de la soutenance PFE
```

---

## 7. Livrables Attendus

1. **Code Source Complet :** Dépôt GitHub structuré avec backend FastAPI, frontend React, adaptateurs d'outils et scripts Docker.
2. **Plateforme Fonctionnelle :** Démonstration d'un audit complet sur lab (GOAD + Juice Shop) avec interceptions d'approbation.
3. **Rapport Audit PDF Généré :** Exemple de rapport client issu directement d'une campagne de test.
4. **Documentation & Article Technique :** README détaillé, vidéo de démonstration et publication LinkedIn axée sur la gestion du risque et le contrôle humain.
