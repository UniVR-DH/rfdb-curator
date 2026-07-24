# Getting Started with RFDB Curator

A short orientation: what the editor is for, the shape of the data model you will be
working with, and how to run it locally and in production. For the full RDF/SHACL
reference see [data-model.md](data-model.md); for running a development environment see
[development.md](development.md); for production see [deployment.md](deployment.md).

---

## What this application is for

RFDB Curator is a curation application for RossijskijFeatrDB. It lets you create,
edit, validate, and inspect records about musical works, their librettos and editions,
the physical sources that hold them, and the people, places, roles, and performances
connected to them.

Every record type, field, and constraint in the editor is generated automatically from
an underlying SHACL schema, so the forms always reflect the current data model. You do
not need to edit RDF by hand — you fill in forms, and the application produces
validated RDF behind the scenes.

---

## The data model, in brief

The records follow a layered "work → expression → manifestation → item" (WEMI)
structure. Each level is more concrete than the one above it:

- **Musical Work** — the abstract work (e.g. an opera as a creative idea).
- **Expression** — an intellectual realization of the work, such as its libretto.
- **Manifestation** — a specific edition or product type of an expression.
- **Source / Item** — a single physical or documentary copy held by an institution.

Around this spine sit the supporting records you link to: **Persons**, **Roles**,
**Places**, **Subjects**, **Source Types**, **Holding Organizations**, and staged
**Performances**. Contributor roles (composer, librettist, and so on) are attached
through small **Agent Role** bridge records that connect a person to a role.

### Recommended editorial order

Because every link points from the more concrete record up to its parent, create
parents before children:

1. Create the auxiliary entities first (Places, Persons, Subjects, Organizations, and
   the document Types) — they populate the dropdowns used below.
2. Create the Musical Work.
3. Create the Expression (e.g. the libretto), linked up to its parent Work.
4. Create the Manifestation, linked to the Expression.
5. Create the Source / Item, linked to the Manifestation (one Manifestation can have
   many Sources).

The editor also supports incremental cascade insertion — you can create a parent and
inline-create its nested referenced entities in one step. A built-in "Getting started"
overlay in the app walks through this WEMI flow the first time you open it.

---

## Running it locally

You need Docker, Docker Compose, and OpenSSL. On a fresh checkout there is a one-time
setup — generate the gitignored `.env` (Garage RPC secret + shared S3 credentials) and
bootstrap Garage (cluster layout, bucket, access key). Compose fails fast without `.env`,
and file uploads fail until Garage is bootstrapped. From the repository root:

```bash
# 1. Generate .env with fresh dev secrets (refuses to clobber an existing .env)
scripts/env-init.sh

# 2. Build and start the stack
docker compose up -d --build

# 3. Bootstrap Garage — run ONCE, after the first `up` (and again after any `down -v`)
scripts/garage-init.sh
```

Both scripts are idempotent. After setup, ordinary runs need only Compose:

```bash
# First run of a session or after Dockerfile changes
docker compose up --build

# Subsequent runs
docker compose up
```

Then open the editor at <http://localhost:5173>.

Stop the services with `docker compose down`. Avoid `docker compose down -v` unless you
intend to erase all stored data — the `-v` flag deletes the Oxigraph data volume **and**
the Garage volumes (layout, bucket, key), after which you must re-run
`scripts/garage-init.sh`.

The controlled vocabulary is seeded automatically on startup. For the full set of
startup and data-reset options, see the Configuration and Data Seeding sections of the
root `README.md`.

---

## Running in production

Production runs a hardened Docker Compose stack behind a TLS-terminating reverse proxy,
with the triple store and object store kept internal-only. The full step-by-step
procedure — host prerequisites, environment configuration, build, and verification — is
in [deployment.md](deployment.md).
