#!/bin/bash
# Test all sandbox environments for pactfix
# Usage: ./scripts/test-sandboxes.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACTFIX_DIR="$(dirname "$SCRIPT_DIR")"
TEST_PROJECTS_DIR="${PACTFIX_DIR}/test-projects"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
RESULTS=()
RUN_TESTS=0

WORK_ROOT="$(mktemp -d)"
trap 'rm -rf "${WORK_ROOT}"' EXIT

if [[ "${1:-}" == "--test" ]]; then
    RUN_TESTS=1
fi

prepare_work_project() {
    local src_project_path="$1"
    local project_name="$2"

    local fixture_dir="${src_project_path}/_fixtures/faulty"
    if [[ ! -d "$fixture_dir" ]]; then
        echo -e "${RED}❌ Missing fixture directory: ${fixture_dir}${NC}"
        return 1
    fi

    local work_project_path="${WORK_ROOT}/${project_name}"
    mkdir -p "$work_project_path"
    cp -a "${fixture_dir}/." "$work_project_path/"

    echo "$work_project_path"
}

test_project() {
    local project_name="$1"
    local src_project_path="${TEST_PROJECTS_DIR}/${project_name}"
    
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Testing: ${project_name}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    
    if [[ ! -d "$src_project_path" ]]; then
        echo -e "${RED}❌ Project directory not found: ${src_project_path}${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("❌ ${project_name}: Directory not found")
        return 1
    fi

    local project_path
    if ! project_path="$(prepare_work_project "$src_project_path" "$project_name")"; then
        FAILED=$((FAILED + 1))
        RESULTS+=("❌ ${project_name}: Missing _fixtures/faulty")
        return 1
    fi
    
    # Run pactfix with sandbox
    # Note: pactfix returns 1 if errors are detected, which is expected
    if [[ $RUN_TESTS -eq 1 ]]; then
        echo -e "${YELLOW}Running: pactfix --path ${project_path} --sandbox --test${NC}"
        python3 -m pactfix --path "$project_path" --sandbox --test 2>&1 || true
    else
        echo -e "${YELLOW}Running: pactfix --path ${project_path} --sandbox${NC}"
        python3 -m pactfix --path "$project_path" --sandbox 2>&1 || true
    fi
    
    # Check if sandbox was created
    if [[ -d "${project_path}/.pactfix" ]]; then
        echo -e "${GREEN}✅ Sandbox created${NC}"
        
        # Check for required files
        local required_files=("Dockerfile" "docker-compose.yml" "report.json")
        local all_present=true
        
        for file in "${required_files[@]}"; do
            if [[ -f "${project_path}/.pactfix/${file}" ]]; then
                echo -e "   ${GREEN}✓${NC} ${file}"
            else
                echo -e "   ${RED}✗${NC} ${file} missing"
                all_present=false
            fi
        done
        
        # Check if fixed files exist
        if [[ -d "${project_path}/.pactfix/fixed" ]]; then
            fixed_count=$(find "${project_path}/.pactfix/fixed" -type f | wc -l)
            echo -e "   ${GREEN}✓${NC} Fixed files: ${fixed_count}"
        fi
        
        # Check report for fixes
        if [[ -f "${project_path}/.pactfix/report.json" ]]; then
            fixes=$(python3 -c "import json; r=json.load(open('${project_path}/.pactfix/report.json')); print(r.get('total_fixes', 0))" 2>/dev/null || echo "0")
            errors=$(python3 -c "import json; r=json.load(open('${project_path}/.pactfix/report.json')); print(r.get('total_errors', 0))" 2>/dev/null || echo "0")
            echo -e "   📊 Errors detected: ${errors}, Fixes applied: ${fixes}"
        else
            fixes=0
        fi

        # If fixes were reported, ensure fixed files are actually different than the restored originals
        if [[ "${fixes}" -gt 0 ]]; then
            if [[ ! -d "${project_path}/.pactfix/fixed" ]]; then
                echo -e "   ${RED}✗${NC} Fixed files directory missing"
                all_present=false
            else
                while IFS= read -r fixed_file; do
                    rel_path="${fixed_file#${project_path}/.pactfix/fixed/}"
                    orig_file="${project_path}/${rel_path}"

                    if [[ ! -f "$orig_file" ]]; then
                        echo -e "   ${RED}✗${NC} Original file missing for fixed file: ${rel_path}"
                        all_present=false
                        continue
                    fi

                    if cmp -s "$fixed_file" "$orig_file"; then
                        echo -e "   ${RED}✗${NC} Fixed file identical to original: ${rel_path}"
                        all_present=false
                    fi
                done < <(find "${project_path}/.pactfix/fixed" -type f)
            fi
        fi

        # Validate sandbox execution status
        local status_file="${project_path}/.pactfix/sandbox_status.json"
        if [[ -f "$status_file" ]]; then
            build_ok=$(python3 -c "import json; s=json.load(open('${project_path}/.pactfix/sandbox_status.json')); print(int(bool(s.get('build_success'))))" 2>/dev/null || echo "0")
            run_ok=$(python3 -c "import json; s=json.load(open('${project_path}/.pactfix/sandbox_status.json')); print(int(bool(s.get('run_success'))))" 2>/dev/null || echo "0")
            test_ok=$(python3 -c "import json; s=json.load(open('${project_path}/.pactfix/sandbox_status.json')); print(int(bool(s.get('test_success'))))" 2>/dev/null || echo "0")

            if [[ "$build_ok" != "1" ]]; then
                echo -e "   ${RED}✗${NC} Docker build failed"
                all_present=false
            fi
            if [[ "$run_ok" != "1" ]]; then
                echo -e "   ${RED}✗${NC} Sandbox run failed"
                all_present=false
            fi
            if [[ $RUN_TESTS -eq 1 && "$test_ok" != "1" ]]; then
                echo -e "   ${RED}✗${NC} Sandbox tests failed"
                all_present=false
            fi
        else
            echo -e "   ${RED}✗${NC} sandbox_status.json missing"
            all_present=false
        fi
        
        if $all_present; then
            PASSED=$((PASSED + 1))
            RESULTS+=("✅ ${project_name}: Sandbox OK (${fixes} fixes)")
        else
            FAILED=$((FAILED + 1))
            RESULTS+=("⚠️  ${project_name}: Sandbox incomplete")
        fi
    else
        echo -e "${RED}❌ Sandbox directory not created${NC}"
        FAILED=$((FAILED + 1))
        RESULTS+=("❌ ${project_name}: No .pactfix directory")
    fi
}

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           PACTFIX SANDBOX TEST SUITE                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Test each project
PROJECTS=("python-project" "nodejs-project" "bash-project" "go-project" "dockerfile-project")

for project in "${PROJECTS[@]}"; do
    test_project "$project"
done

# Summary
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

for result in "${RESULTS[@]}"; do
    echo -e "  $result"
done

echo -e "\n${GREEN}Passed: ${PASSED}${NC} | ${RED}Failed: ${FAILED}${NC}"

# Cleanup all sandboxes
echo -e "\n${YELLOW}Cleaning up sandboxes...${NC}"
rm -rf "${WORK_ROOT}" 2>/dev/null || true
echo -e "${GREEN}Done${NC}"

# Exit with appropriate code
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
exit 0
