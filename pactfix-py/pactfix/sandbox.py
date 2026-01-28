"""Sandbox module - Docker-based isolated environment for testing fixes."""

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


LANGUAGE_DOCKERFILES = {
    'python': '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
COPY . .
CMD ["sh", "-c", "python -m pytest -v || python main.py || echo 'No entrypoint found'"]
''',

    'nodejs': '''FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install 2>/dev/null || true
COPY . .
CMD ["sh", "-c", "npm test || npm start || node index.js"]
''',

    'javascript': '''FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install 2>/dev/null || true
COPY . .
CMD ["sh", "-c", "npm test || npm start || node index.js"]
''',

    'typescript': '''FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm install 2>/dev/null || true
COPY . .
RUN npm run build 2>/dev/null || npx tsc 2>/dev/null || true
CMD ["sh", "-c", "npm test || npm start"]
''',

    'go': '''FROM golang:1.21-alpine
WORKDIR /app
COPY go.* ./
RUN go mod download 2>/dev/null || true
COPY . .
RUN go build -o main . 2>/dev/null || true
CMD ["sh", "-c", "go test -v ./... || ./main"]
''',

    'rust': '''FROM rust:1.75-slim
WORKDIR /app
COPY Cargo.* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release 2>/dev/null || true
COPY . .
RUN cargo build --release
CMD ["sh", "-c", "cargo test || ./target/release/*"]
''',

    'java': '''FROM eclipse-temurin:21-jdk-jammy
WORKDIR /app
COPY . .
RUN if [ -f "pom.xml" ]; then ./mvnw package -DskipTests 2>/dev/null || mvn package -DskipTests; fi
RUN if [ -f "build.gradle" ]; then ./gradlew build -x test 2>/dev/null || gradle build -x test; fi
CMD ["sh", "-c", "java -jar target/*.jar || java Main"]
''',

    'php': '''FROM php:8.3-cli
WORKDIR /app
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
COPY composer.* ./
RUN composer install 2>/dev/null || true
COPY . .
CMD ["sh", "-c", "php -S 0.0.0.0:8080 -t public || php index.php"]
''',

    'ruby': '''FROM ruby:3.3-slim
WORKDIR /app
COPY Gemfile* ./
RUN bundle install 2>/dev/null || true
COPY . .
CMD ["sh", "-c", "bundle exec rspec || ruby main.rb"]
''',

    'csharp': '''FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /app
COPY *.csproj ./
RUN dotnet restore 2>/dev/null || true
COPY . .
RUN dotnet build --configuration Release
CMD ["sh", "-c", "dotnet test || dotnet run"]
''',

    'bash': '''FROM ubuntu:22.04
RUN apt-get update && apt-get install -y bash shellcheck && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN chmod +x *.sh 2>/dev/null || true
CMD ["sh", "-c", "shellcheck *.sh && ./main.sh || ./run.sh || echo 'No entrypoint'"]
''',

    'dockerfile': '''FROM alpine:3.19
WORKDIR /app
COPY . .
CMD ["sh", "-c", "test -f Dockerfile && echo 'Dockerfile present' || (echo 'Dockerfile missing' && exit 1)"]
''',

    'terraform': '''FROM hashicorp/terraform:1.6
WORKDIR /app
COPY . .
RUN terraform init
CMD ["sh", "-c", "terraform validate"]
''',

    'ansible': '''FROM python:3.11-slim
RUN pip install ansible ansible-lint
WORKDIR /app
COPY . .
CMD ["sh", "-c", "ansible-lint . || ansible-playbook --syntax-check *.yml"]
''',

    'generic': '''FROM ubuntu:22.04
RUN apt-get update && apt-get install -y build-essential git curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
CMD ["sh", "-c", "echo 'Generic sandbox - manual testing required'"]
'''
}


def detect_project_language(project_path: Path) -> Tuple[str, Dict]:
    """Detect the primary language of a project based on files present."""
    
    indicators = {
        'python': {
            'files': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
            'extensions': ['.py'],
            'weight': 0
        },
        'nodejs': {
            'files': ['package.json'],
            'extensions': ['.js', '.mjs'],
            'weight': 0
        },
        'typescript': {
            'files': ['tsconfig.json', 'package.json'],
            'extensions': ['.ts', '.tsx'],
            'weight': 0
        },
        'go': {
            'files': ['go.mod', 'go.sum'],
            'extensions': ['.go'],
            'weight': 0
        },
        'rust': {
            'files': ['Cargo.toml', 'Cargo.lock'],
            'extensions': ['.rs'],
            'weight': 0
        },
        'java': {
            'files': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'extensions': ['.java'],
            'weight': 0
        },
        'php': {
            'files': ['composer.json', 'composer.lock'],
            'extensions': ['.php'],
            'weight': 0
        },
        'ruby': {
            'files': ['Gemfile', 'Gemfile.lock', 'Rakefile'],
            'extensions': ['.rb'],
            'weight': 0
        },
        'csharp': {
            'files': [],
            'extensions': ['.cs', '.csproj', '.sln'],
            'weight': 0
        },
        'bash': {
            'files': [],
            'extensions': ['.sh'],
            'weight': 0
        },
        'dockerfile': {
            'files': ['Dockerfile'],
            'extensions': [],
            'weight': 0
        },
        'terraform': {
            'files': [],
            'extensions': ['.tf'],
            'weight': 0
        },
        'ansible': {
            'files': ['playbook.yml', 'ansible.cfg', 'inventory'],
            'extensions': [],
            'weight': 0
        }
    }
    
    file_counts = {}
    
    for item in project_path.rglob('*'):
        if item.is_file() and '_fixtures' not in item.parts and not any(p.startswith('.') for p in item.parts):
            ext = item.suffix.lower()
            name = item.name.lower()
            
            for lang, info in indicators.items():
                if name in [f.lower() for f in info['files']]:
                    info['weight'] += 10
                if ext in info['extensions']:
                    info['weight'] += 1
                    file_counts[lang] = file_counts.get(lang, 0) + 1
    
    # TypeScript override - if tsconfig.json exists, prefer TS over JS
    if indicators['typescript']['weight'] > 0 and indicators['nodejs']['weight'] > 0:
        if (project_path / 'tsconfig.json').exists():
            indicators['typescript']['weight'] += 20
    
    best_lang = max(indicators.keys(), key=lambda x: indicators[x]['weight'])
    
    if indicators[best_lang]['weight'] == 0:
        best_lang = 'generic'
    
    stats = {
        'detected_language': best_lang,
        'confidence': indicators.get(best_lang, {}).get('weight', 0),
        'file_counts': file_counts,
        'all_scores': {k: v['weight'] for k, v in indicators.items() if v['weight'] > 0}
    }
    
    return best_lang, stats


class Sandbox:
    """Docker-based sandbox for running and testing fixed code."""
    
    def __init__(self, project_path: str, sandbox_dir: str = None):
        self.project_path = Path(project_path).resolve()
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else self.project_path / '.pactfix'
        self.project_copy_dir = self.sandbox_dir / 'project'
        self.language = None
        self.stats = {}
        self.last_build_returncode = None
        self.last_run_returncode = None
        self.last_test_returncode = None
        
    def setup(self) -> bool:
        """Setup the sandbox environment."""
        print(f"🔧 Setting up sandbox in {self.sandbox_dir}")
        
        # Create sandbox directory
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a copy of the project for sandbox build/run
        # This avoids running against the original sources and allows applying fixes.
        if self.project_copy_dir.exists():
            shutil.rmtree(self.project_copy_dir, ignore_errors=True)

        ignore = shutil.ignore_patterns(
            '.git', '.pactfix', '_fixtures', 'node_modules', '__pycache__', '*.pyc',
            'venv', '.venv', 'dist', 'build', 'target', '.idea', '.vscode'
        )
        shutil.copytree(self.project_path, self.project_copy_dir, ignore=ignore)

        # Detect project language
        self.language, self.stats = detect_project_language(self.project_path)
        print(f"📋 Detected language: {self.language} (confidence: {self.stats['confidence']})")
        
        # Create Dockerfile
        dockerfile_content = LANGUAGE_DOCKERFILES.get(self.language, LANGUAGE_DOCKERFILES['generic'])
        dockerfile_path = self.sandbox_dir / 'Dockerfile'
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        # Also place a copy inside the build context for docker-compose compatibility
        dockerfile_in_context = self.project_copy_dir / 'Dockerfile'
        with open(dockerfile_in_context, 'w') as f:
            f.write(dockerfile_content)

        print(f"✅ Created Dockerfile for {self.language}")
        
        # Create docker-compose.yml
        compose_content = self._generate_docker_compose()
        compose_path = self.sandbox_dir / 'docker-compose.yml'
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        print(f"✅ Created docker-compose.yml")
        
        # Create .dockerignore
        dockerignore_content = self._generate_dockerignore()
        dockerignore_path = self.sandbox_dir / '.dockerignore'
        with open(dockerignore_path, 'w') as f:
            f.write(dockerignore_content)
        
        # Save sandbox config
        config = {
            'project_path': str(self.project_path),
            'sandbox_dir': str(self.sandbox_dir),
            'language': self.language,
            'stats': self.stats,
            'created_at': datetime.now().isoformat()
        }
        config_path = self.sandbox_dir / 'sandbox.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
    
    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml for the sandbox."""
        return f'''version: '3.8'

services:
  pactfix-sandbox:
    build:
      context: ./project
      dockerfile: Dockerfile
    container_name: pactfix-sandbox-{self.language}
    volumes:
      - ./output:/output
    environment:
      - PACTFIX_SANDBOX=1
      - PACTFIX_LANGUAGE={self.language}
    working_dir: /app
    networks:
      - pactfix-net

networks:
  pactfix-net:
    driver: bridge
'''

    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore file."""
        return '''.git
.gitignore
.pactfix
*.log
*.tmp
node_modules
__pycache__
*.pyc
.venv
venv
.env
.env.local
target
build
dist
'''

    def copy_fixed_files(self, fixed_files: Dict[str, str]) -> bool:
        """Copy fixed files to sandbox for testing."""
        fixed_dir = self.sandbox_dir / 'fixed'
        fixed_dir.mkdir(parents=True, exist_ok=True)
        
        for rel_path, content in fixed_files.items():
            # Keep a copy under .pactfix/fixed
            fixed_file_path = fixed_dir / rel_path
            fixed_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(fixed_file_path, 'w') as f:
                f.write(content)

            # Apply fixes onto the sandbox project copy used for build/run
            project_file_path = self.project_copy_dir / rel_path
            project_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(project_file_path, 'w') as f:
                f.write(content)

            print(f"  📄 {rel_path}")
        
        return True
    
    def build(self) -> Tuple[bool, str]:
        """Build the Docker image."""
        print(f"\n🔨 Building Docker image...")
        
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', f'pactfix-sandbox-{self.language}', 
                 '-f', str(self.project_copy_dir / 'Dockerfile'), str(self.project_copy_dir)],
                capture_output=True,
                text=True,
                timeout=300
            )

            self.last_build_returncode = result.returncode
            
            if result.returncode == 0:
                print("✅ Build successful")
                return True, result.stdout
            else:
                print(f"❌ Build failed:\n{result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Build timeout (5 min)"
        except FileNotFoundError:
            return False, "Docker not found. Please install Docker."
        except Exception as e:
            return False, str(e)
    
    def run(self, command: str = None) -> Tuple[bool, str]:
        """Run the sandbox container."""
        print(f"\n🚀 Running sandbox...")
        
        output_dir = self.sandbox_dir / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = ['docker', 'run', '--rm', '-v', f'{output_dir}:/output', f'pactfix-sandbox-{self.language}']
        
        if command:
            cmd.extend(['sh', '-c', command])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            self.last_run_returncode = result.returncode
            
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                print("✅ Run successful")
                return True, output
            else:
                print(f"⚠️ Run finished with code {result.returncode}")
                return False, output
                
        except subprocess.TimeoutExpired:
            return False, "Run timeout (2 min)"
        except Exception as e:
            return False, str(e)
    
    def test(self) -> Tuple[bool, str]:
        """Run tests in the sandbox."""
        print(f"\n🧪 Running tests...")
        
        test_commands = {
            'python': 'python -m pytest -v || python -m unittest discover',
            'nodejs': 'npm test',
            'typescript': 'npm test',
            'go': 'go test -v ./...',
            'rust': 'cargo test',
            'java': './mvnw test || gradle test',
            'php': 'composer test || ./vendor/bin/phpunit',
            'ruby': 'bundle exec rspec || rake test',
            'csharp': 'dotnet test',
            'bash': 'shellcheck *.sh',
            'terraform': 'terraform validate',
            'ansible': 'ansible-lint .',
        }
        
        cmd = test_commands.get(self.language, 'echo "No test command for this language"')
        ok, out = self.run(cmd)
        self.last_test_returncode = self.last_run_returncode
        return ok, out
    
    def cleanup(self):
        """Clean up sandbox resources."""
        print(f"\n🧹 Cleaning up...")
        
        # Remove Docker image
        try:
            subprocess.run(
                ['docker', 'rmi', '-f', f'pactfix-sandbox-{self.language}'],
                capture_output=True,
                timeout=30
            )
        except:
            pass
        
        print("✅ Cleanup complete")


def create_language_dockerfile(language: str, output_dir: Path) -> Path:
    """Create a Dockerfile for a specific language."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    content = LANGUAGE_DOCKERFILES.get(language, LANGUAGE_DOCKERFILES['generic'])
    dockerfile_path = output_dir / f'Dockerfile.{language}'
    
    with open(dockerfile_path, 'w') as f:
        f.write(content)
    
    return dockerfile_path


def create_all_dockerfiles(output_dir: Path) -> List[Path]:
    """Create Dockerfiles for all supported languages."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    
    for language in LANGUAGE_DOCKERFILES.keys():
        if language == 'generic':
            continue
        path = create_language_dockerfile(language, output_dir)
        created.append(path)
        print(f"✅ Created {path.name}")
    
    return created
