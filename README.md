# Wraithlink

Plateforme d'orchestration de tests d'intrusion guidee par le risque, pour applications Web et environnements Active Directory. Le plan de travail complet est dans [`Plan_de_Travail_Wraithlink.md`](./Plan_de_Travail_Wraithlink.md).

Wraithlink automatise la reconnaissance et l'enumeration a faible risque, et bloque toute execution devant un point de decision sensible tant qu'un pentesteur n'a pas explicitement choisi entre une option conservatrice et une option agressive. Chaque decision, chaque action et chaque preuve est tracee dans un journal d'audit chaine par hash.

## Architecture

```
backend/    API FastAPI, moteur de risque, machine a etats, adaptateurs d'outils, worker Celery
frontend/   Dashboard React + TypeScript + Tailwind
docs/       Documentation de mise en place du laboratoire
```

Voir la section 6 du plan de travail pour le detail de l'architecture, le schema de donnees et la specification API.

## Demarrage

Prerequis : Docker Desktop.

```
cp .env.example .env
# editer .env et definir un JWT_SECRET et un POSTGRES_PASSWORD reels
docker compose up --build
```

Services exposes :

- Backend API : http://localhost:8000 (documentation interactive sur `/docs`)
- Frontend : http://localhost:5173

PostgreSQL et Redis ne sont volontairement pas exposes sur l'hote par defaut (seul le reseau Docker interne y a acces) ; pour un acces direct via `psql`/`redis-cli` en developpement, ajouter un `docker-compose.override.yml` local avec les sections `ports` correspondantes.

Le premier compte utilisateur doit etre cree manuellement (pas d'inscription publique, volontairement) :

```
docker compose exec backend python scripts/create_user.py pentester@example.com un-mot-de-passe-solide --role pentester
```

Puis se connecter sur le frontend avec ces identifiants.

## Laboratoire

Wraithlink n'installe ni ne configure aucune cible. Voir [`docs/LAB_SETUP.md`](./docs/LAB_SETUP.md) pour monter GOAD-Light et OWASP Juice Shop dans un reseau isole avant de lancer le moindre engagement.

## Developpement local

Backend :

```
cd backend
python -m venv .venv
.venv/Scripts/activate  # ou source .venv/bin/activate sous Linux/macOS
pip install -r requirements.txt
alembic upgrade head
pytest
uvicorn app.main:app --reload
```

Le worker Celery s'execute separement :

```
celery -A app.tasks.celery_app worker --loglevel=info
```

Frontend :

```
cd frontend
npm install
npm run dev
```

Note pour le developpement local sous Windows : la generation de rapports PDF (WeasyPrint) depend de bibliotheques natives GTK/Pango absentes de Windows par defaut. Cette dependance est installee dans l'image Docker du backend ; en local hors Docker, l'endpoint `/reports/{engagement_id}` renverra une erreur explicite plutot que de planter silencieusement.

## Tests

```
cd backend
pytest
```

La suite couvre les adaptateurs d'outils, le moteur de risque (avec les six exemples chiffres du plan de travail), la machine a etats de l'engagement, le chainage du journal d'audit, et le flux API de bout en bout (creation d'engagement, classification d'action, workflow d'approbation, RBAC).
