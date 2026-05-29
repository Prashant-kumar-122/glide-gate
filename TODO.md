# TODO

## Migration - HIGH PRIORITY

- [ ] **Fix and re-enable Alembic migration in `docker-compose.yml`**
  - Migration `0005_trusted_contact_questions.py` fails with a `ForeignKeyViolationError`
  - Questionnaire `c0000000-0001-0001-0001-000000000001` is never seeded in any migration
  - Fix: add `INSERT INTO onboarding_questionnaires ... ON CONFLICT DO NOTHING` at the start of `0005` upgrade()
  - Once fixed, restore the command in `docker-compose.yml`:
    ```
    sh -c "poetry run alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    ```



## EC2 Setup - Required Before First Deploy

- [ ] SSH into the EC2 and checkout the correct branch first:
  ```bash
  ssh -i your-key.pem ubuntu@18.60.103.228
  cd /home/ubuntu/office_project/glidegate
  git fetch origin
  git checkout COPS_Agentic_AI_Deploy
  git pull origin COPS_Agentic_AI_Deploy
  ```
  This ensures `deploy.sh` can do `git pull` without branch mismatch errors.

- [ ] **Attach a persistence layer to PostgreSQL on EC2**
  - Currently `db/data/` is a local volume — data will be lost if the container is removed
  - Mount a dedicated EBS volume or use a managed RDS instance for production persistence

## Migration - HIGH PRIORITY

- [ ] **Fix and re-enable Alembic migration in `docker-compose.yml`**
  - Migration `0005_trusted_contact_questions.py` fails with a `ForeignKeyViolationError`
  - Questionnaire `c0000000-0001-0001-0001-000000000001` is never seeded in any migration
  - Fix: add `INSERT INTO onboarding_questionnaires ... ON CONFLICT DO NOTHING` at the start of `0005` upgrade()
  - Once fixed, restore the command in `docker-compose.yml`:
    ```
    sh -c "poetry run alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    ```

## Security - HIGH PRIORITY

- [ ] **Remove hardcoded SSH private key from `.gitlab-ci.yml`**
  - Currently the EC2 SSH key is hardcoded directly in the CI file as a temporary workaround
  - Once maintainer access is available, move it to a GitLab CI/CD Variable (`EC2_SSH_KEY`)
  - Rotate/replace the EC2 SSH key pair after moving it to the variable
  - Reference: GitLab → Settings → CI/CD → Variables


- ## Attach a persistence layer to PostgreSQL on EC2
  - Currently `db/data/` is a local volume — data will be lost if the container is removed
  - Mount a dedicated EBS volume or use a managed RDS instance for production persistence



