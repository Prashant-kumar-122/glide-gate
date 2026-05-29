# TODO

## Security - HIGH PRIORITY

- [ ] **Remove hardcoded SSH private key from `.gitlab-ci.yml`**
  - Currently the EC2 SSH key is hardcoded directly in the CI file as a temporary workaround
  - Once maintainer access is available, move it to a GitLab CI/CD Variable (`EC2_SSH_KEY`)
  - Rotate/replace the EC2 SSH key pair after moving it to the variable
  - Reference: GitLab → Settings → CI/CD → Variables
