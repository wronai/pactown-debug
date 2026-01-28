"""Additional tests for pactfix analyzers."""

from pactfix.analyzer import (
    analyze_docker_compose,
    analyze_nginx,
    analyze_github_actions,
    analyze_ansible,
)


class TestDockerComposeAnalysis:
    def test_detect_privileged(self):
        result = analyze_docker_compose(
            """version: '3.8'
services:
  web:
    image: nginx
    privileged: true
"""
        )
        assert any(e.code == 'COMPOSE002' for e in result.errors)

    def test_detect_hardcoded_secret(self):
        result = analyze_docker_compose(
            """services:
  web:
    image: nginx:latest
    environment:
      - DATABASE_PASSWORD=secret
"""
        )
        assert any(w.code == 'COMPOSE001' for w in result.warnings)
        assert any(e.code == 'COMPOSE005' for e in result.errors)


class TestNginxAnalysis:
    def test_server_tokens_fix(self):
        result = analyze_nginx(
            """server {
  listen 80;
  server_tokens on;
}
"""
        )
        assert any(w.code == 'NGINX001' for w in result.warnings)
        assert 'server_tokens off' in result.fixed_code

    def test_weak_ssl_protocols(self):
        result = analyze_nginx(
            """server {
  listen 443 ssl;
  ssl_certificate /etc/ssl/cert.pem;
  ssl_protocols SSLv3 TLSv1;
}
"""
        )
        assert any(e.code == 'NGINX003' for e in result.errors)


class TestGithubActionsAnalysis:
    def test_uses_master_fix(self):
        result = analyze_github_actions(
            """name: CI
on:
  push:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@master
"""
        )
        assert any(w.code == 'GHA001' for w in result.warnings)
        assert '@v4' in result.fixed_code

    def test_hardcoded_secret(self):
        result = analyze_github_actions(
            """name: CI
on:
  push:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Bad
        run: echo "token: abc123"
"""
        )
        assert any(e.code == 'GHA003' for e in result.errors)


class TestAnsibleAnalysis:
    def test_plaintext_password(self):
        result = analyze_ansible(
            """- hosts: all
  tasks:
    - name: Set password
      mysql_user:
        password: "mypassword"
"""
        )
        assert any(e.code == 'ANS001' for e in result.errors)

    def test_ignore_errors_warning(self):
        result = analyze_ansible(
            """- hosts: all
  tasks:
    - shell: echo hi
      ignore_errors: true
"""
        )
        assert any(w.code == 'ANS004' for w in result.warnings)
