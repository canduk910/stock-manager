---
name: doc-commit
description: "변경사항을 CLAUDE.md + CHANGELOG.md에 반영하고 커밋 + compact. 'md파일 반영', '문서 반영하고 커밋', '커밋하자', 'doc-commit' 요청 시 사용."
---

# 문서 반영 + 커밋 + Compact

변경된 코드를 분석하여 문서에 반영하고, 커밋한 뒤 컨텍스트를 정리한다.

## 프로세스

### Step 1: 변경사항 파악

```bash
git status -s
git diff --stat
git log --oneline -3
```

변경 파일을 레이어별로 분류한다:
- **백엔드**: `routers/`, `services/`, `stock/`, `config.py`, `main.py`
- **프론트엔드**: `frontend/src/`
- **문서**: `docs/`, `**/CLAUDE.md`

### Step 2: CLAUDE.md 파일 갱신

변경된 레이어에 해당하는 CLAUDE.md를 읽고 업데이트한다:

| 변경 레이어 | 갱신 대상 |
|------------|----------|
| `routers/` | `routers/CLAUDE.md` — 라우터 목록 테이블, 엔드포인트 설명 |
| `services/` | `services/CLAUDE.md` — 모듈 목록 테이블 |
| `stock/` | `stock/CLAUDE.md` — 모듈 목록 테이블 |
| `frontend/` | `frontend/CLAUDE.md` — 페이지, 훅, 컴포넌트, API 목록 |
| 전체 구조 변경 | `CLAUDE.md` (루트) — 레이어 구성, 환경변수, 라우터 수 |

**갱신 규칙:**
- 신규 파일 → 해당 테이블에 행 추가
- 삭제된 파일 → 해당 테이블에서 행 제거
- 기능 변경 → 설명 텍스트 수정
- 숫자 변경 → 라우터 수, 메뉴 수 등 업데이트

### Step 2.5: docs/ 스펙 문서 + README.md 갱신

변경된 레이어에 해당하는 docs/ 스펙 문서를 읽고 업데이트한다:

| 변경 레이어 | 갱신 대상 |
|------------|----------|
| `stock/` | `docs/STOCK_PACKAGE.md` — 모듈 구성, DB, 함수 시그니처 |
| `services/` | `docs/SERVICES.md` — 모듈 구성, 서비스 설명 |
| `routers/` | `docs/API_SPEC.md` — 엔드포인트 목록, 요청/응답 스펙 |
| `frontend/` | `docs/FRONTEND_SPEC.md` — 컴포넌트, 페이지, 훅 |
| 전체 구조 변경 | `README.md` (루트) — 프로젝트 소개, 설치 방법, 아키텍처 |

**갱신 규칙:**
- docs/ 스펙 문서는 CLAUDE.md보다 상세한 API 레퍼런스 역할
- 함수 시그니처 변경 → 해당 docs 문서의 시그니처 섹션 수정
- 새 패키지/모듈 추가 → 해당 docs 문서에 섹션 추가
- README.md는 프로젝트 전체 구조 변경, 환경변수 추가, 설치 방법 변경 시에만 갱신

### Step 3: docs/CHANGELOG.md 갱신

`docs/CHANGELOG.md` 맨 위에 날짜 섹션을 추가하거나 기존 당일 섹션에 항목을 추가한다.

```markdown
## YYYY-MM-DD — {변경 요약 제목}

### {카테고리}
- {변경 내용 1줄 요약}
- {변경 내용 1줄 요약}
```

**카테고리 분류:**
- 신규 기능 → `### {기능명} 신규`
- 버그 수정 → `### 버그 수정`
- 리팩토링 → `### 리팩토링`
- UI 개선 → `### UI 개선`
- 프롬프트 개선 → `### 프롬프트 개선`

### Step 4: 커밋

```bash
# 1. 변경 파일 + 문서 파일 스테이징
git add {변경된 소스 파일들} {갱신된 CLAUDE.md 파일들} docs/CHANGELOG.md

# 2. 커밋 메시지 작성 (HEREDOC)
git commit -m "$(cat <<'EOF'
{1줄 제목: 핵심 변경 요약}

{상세 내용 (있으면)}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**커밋 메시지 규칙:**
- 한국어 사용
- 제목은 50자 이내
- 제목에 변경 유형 포함 (신규/수정/통합/버그수정 등)
- 문서 반영은 제목에 별도 언급하지 않음 (항상 포함이므로)

### Step 5: Compact

커밋 완료 후 컨텍스트를 정리한다.

```
/compact
```

**반드시 Step 4 커밋이 성공한 후에만 /compact를 실행한다.**

## 주의사항

- push는 하지 않는다 (사용자가 명시적으로 요청할 때만)
- .env, credentials 등 민감 파일은 커밋하지 않는다
- 이미 커밋된 변경사항(git status clean)이면 "커밋할 변경사항이 없습니다"라고 안내
- 문서 갱신 시 기존 내용을 함부로 삭제하지 않고, 변경된 부분만 수정