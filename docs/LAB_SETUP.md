# Mise en place du laboratoire

AegisPen ne provisionne aucune machine virtuelle et ne configure aucun réseau. Cette étape reste entièrement manuelle et sous votre responsabilité, pour la raison la plus simple qui soit : personne d'autre que vous ne doit avoir le contrôle d'un environnement capable de lancer des scans actifs et des attaques Active Directory. Ce document décrit ce qu'il faut monter avant de brancher la plateforme dessus.

## 1. Isolation réseau

Avant toute chose, le lab doit vivre dans un réseau qui n'a aucune route vers l'extérieur.

* Dans VirtualBox : créer un réseau "Host-only" (Fichier > Outils d'hôte réseau) dédié au lab, par exemple `vboxnet1`, plage `192.168.56.0/24`.
* Dans Docker : créer un réseau bridge dédié et ne jamais publier de ports vers `0.0.0.0`.
  ```
  docker network create --internal aegispen-lab
  ```
  Le flag `--internal` empêche tout accès sortant vers Internet depuis les conteneurs du lab.
* Vérification obligatoire avant de commencer un engagement : depuis une machine du lab, `ping 8.8.8.8` doit échouer. Si ça répond, le réseau n'est pas isolé et il ne faut rien lancer.

## 2. GOAD / GOAD-Light (Active Directory)

GOAD-Light est une version allégée de GOAD (Game Of Active Directory), pensée pour tourner sur une machine avec des ressources limitées (un contrôleur de domaine + quelques postes au lieu d'une forêt complète).

1. Cloner le dépôt officiel :
   ```
   git clone https://github.com/Orange-Cyberdefense/GOAD.git
   cd GOAD
   ```
2. Suivre le guide d'installation du projet pour la variante "light" avec le provider Vagrant + VirtualBox. Compter environ 40 à 60 Go d'espace disque et 8 Go de RAM disponibles pour les VMs.
3. Une fois les VMs démarrées, noter les adresses IP des contrôleurs de domaine et des postes — ce sont les `targets` que vous déclarerez dans un engagement AegisPen.
4. Ne jamais relier ce réseau à votre réseau domestique ou professionnel. GOAD contient des comptes et configurations volontairement vulnérables.

## 3. OWASP Juice Shop (Web)

Juice Shop est une application web volontairement vulnérable, utilisée ici comme cible pour le module Web.

```
docker run --rm -d \
  --network aegispen-lab \
  --name juice-shop \
  -p 3000:3000 \
  bkimminich/juice-shop
```

Ne pas publier le port 3000 sur l'hôte si vous voulez garder l'isolation stricte ; dans ce cas, le backend AegisPen doit lui-même tourner sur le réseau `aegispen-lab` pour atteindre la cible.

## 4. Déclarer le lab dans AegisPen

Une fois le lab up :

1. Démarrer la plateforme (`docker compose up`, voir le README racine).
2. Créer un engagement via l'API ou le dashboard, en renseignant les adresses IP/hosts du lab comme `targets`.
3. La création d'un engagement exige `scope_validated = true` — ce champ doit être coché explicitement, c'est la validation de portée obligatoire décrite dans le plan de travail (section 4).

## 5. Rappel

Toute cible qui n'est pas une machine que vous possédez ou un laboratoire explicitement conçu pour l'entraînement est hors périmètre. AegisPen ne vérifie pas l'autorisation légale à votre place — cette responsabilité reste entièrement la vôtre.
