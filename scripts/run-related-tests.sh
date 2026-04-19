#!/bin/bash
# 변경된 소스 파일에 대응하는 테스트만 실행.
# Claude Code postToolUse hook에서 호출.
#
# 사용: bash scripts/run-related-tests.sh "stock/indicators.py"

set -euo pipefail
cd "$(dirname "$0")/.."

FILE="$1"
TESTS=""

# 절대 경로 → 상대 경로 변환
FILE="${FILE#$PWD/}"

case "$FILE" in
  stock/*.py)
    NAME=$(basename "$FILE" .py)
    [ -f "tests/unit/test_${NAME}.py" ] && TESTS="tests/unit/test_${NAME}.py"
    ;;
  services/schemas/*.py)
    [ -f "tests/unit/test_schemas.py" ] && TESTS="tests/unit/test_schemas.py"
    ;;
  services/*.py)
    NAME=$(basename "$FILE" .py)
    [ -f "tests/unit/test_${NAME}.py" ] && TESTS="tests/unit/test_${NAME}.py"
    ;;
  db/repositories/*.py)
    NAME=$(basename "$FILE" .py)
    [ -f "tests/integration/test_${NAME}.py" ] && TESTS="tests/integration/test_${NAME}.py"
    ;;
  db/models/*.py)
    # 모델 변경 시 관련 repo 테스트 전체
    TESTS="tests/integration/"
    ;;
  routers/*.py)
    NAME=$(basename "$FILE" .py)
    [ -f "tests/api/test_${NAME}_api.py" ] && TESTS="tests/api/test_${NAME}_api.py"
    ;;
  frontend/*)
    cd frontend && npm run build --silent 2>&1 | tail -3
    exit $?
    ;;
  tests/*.py)
    # 테스트 파일 자체를 편집한 경우 해당 테스트만 실행
    TESTS="$FILE"
    ;;
esac

if [ -n "$TESTS" ]; then
  python -m pytest "$TESTS" -v --tb=short -q 2>&1 | tail -20
fi
