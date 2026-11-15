# Developers

[![Deploy dev](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/deploy-dev.yml/badge.svg)](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/deploy-dev.yml)
[![Deploy prod](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/deploy-prod.yml/badge.svg)](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/deploy-prod.yml)
[![Documentation](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/FixMyMedTech/fixmymedtech-app/actions/workflows/pages/pages-build-deployment)
[![License](https://img.shields.io/github/license/FixMyMedTech/fixmymedtech-app)](https://github.com/FixMyMedTech/fixmymedtech-app/blob/main/LICENSE)

**Fix My MedTech** is an open-source platform where biomedical engineers tag, track, diagnose and repair medical devices. It is built around the realities of the field: devices that arrive without manuals, without spare parts and often already degraded, in environments where heat, humidity, dust and unstable power accelerate failure far beyond what manufacturers expect.

The code is Python only: a **FastAPI** backend (REST API, auth, SQLAdmin, reverse proxy) and a **FastHTML** server-rendered frontend, with PostgreSQL and MinIO. There is no JavaScript build step.

## Where to start

| Page | What it covers |
| --- | --- |
| [Getting started](getting_started.md) | The local Docker stack, environment variables, superuser, migrations |
| [Running without Docker](setup.md) | Backend and frontend on your machine, with live reload |
| [Architecture](architecture.md) | Request flow, project structure, key design decisions |
| [Database schema](database.md) | Tables and relationships |
| [Collaboration](collaboration.md) | Issues, branches (`dev` → `main`), pull requests |
| [Community journey (plan)](community-journey.md) | The technical plan of the community features |
| [Community journey (setup and testing)](community-setup.md) | Settings, seed accounts, superuser tasks, tests, where the code is |
| [How these docs work](developers-docs.md) | The site layout, translations, screenshots, and the links from the app |

## Do you want to collaborate?

Questions, ideas or bugs: see [Collaboration](collaboration.md). This project is licensed under the [Apache 2.0](LICENSE) and follows the [Code of Conduct](CODE_OF_CONDUCT.md).
