---
name: genie
description: Genie 개발 비서 오케스트레이터. 사용자가 "지니 설정", "지니 프로젝트 설정", "지니, 개발진행 단계 보여줘", "지니, 다음 단계", "마지막 QA", "배포 준비 상태", "오래된 검증", "중요 결정 복기", "다음 단계 실행"처럼 지니를 부르거나 프로젝트의 개발 생명주기·스킬 구성·실행 이력·다음 작업을 묻는 경우 사용한다. 프로젝트 구조를 검사해 .genie/config.json의 활성 스킬을 구성하고 docs/genie 요약 기록을 바탕으로 현재 상태와 stale 여부를 판정한다.
---

# Genie 개발 비서

프로젝트의 개발 단계를 읽고 필요한 전문 스킬만 선택해 실행하라. 모든 스킬을 기계적으로 순차 실행하지 마라.

## 시작 절차

1. 현재 작업 디렉터리에서 가장 가까운 `AGENTS.md`와 프로젝트 지침을 먼저 읽어라.
2. Git 저장소이면 저장소 루트를 프로젝트 루트로 사용하고, 아니면 현재 작업 디렉터리를 사용하라.
3. 이 파일이 있는 디렉터리를 `GENIE_ROOT`로 취급하라.
4. `GENIE_ROOT/manifest.json`을 읽어 스킬 순서, 트랙, 기록 폴더와 유효성 정책을 확인하라.
5. `GENIE_ROOT/references/project-config.md`를 읽어 프로젝트 설정 흐름을 적용하라.
6. 다음 명령을 실행하라.

```text
python GENIE_ROOT/scripts/genie.py init --project PROJECT_ROOT
```

`GENIE_SETUP_REQUIRED`가 출력되면 상태 조회나 전문 스킬 실행보다 프로젝트 설정을 먼저 진행하라. Python 명령이 없으면 사용 가능한 Python 3 실행 파일을 찾아라. 찾지 못하면 `.genie`나 `docs/genie`를 임의 형식으로 만들지 말고 필요한 런타임을 알려라.

## 의도 라우팅

### 프로젝트 설정

다음 요청은 설정 모드로 처리하라.

- 지니 설정
- 지니 프로젝트 설정
- 현재 프로젝트에서 사용할 스킬 정리
- 프로젝트 구조가 바뀌었으니 다시 확인

먼저 쓰기 없이 구조와 추천 구성을 검사하라.

```text
python GENIE_ROOT/scripts/genie.py configure --project PROJECT_ROOT
```

감지 근거, 프로필, 활성 트랙, 필수·조건부 스킬과 기존 설정 대비 추가·제거 항목을 설명하라. 사용자가 설정을 명시적으로 요청했고 감지가 명확하면 적용하라. 구조가 모호하거나 제거되는 스킬이 중요한 이력을 가진 경우 먼저 확인하라.

```text
python GENIE_ROOT/scripts/genie.py configure --project PROJECT_ROOT --apply
```

설정이 이미 있어도 항상 현재 구조와 최신 카탈로그를 다시 검사하라. 수동 선택은 `--enable <skill>`과 `--disable <skill>`로 보존하라. `.genie/config.json`은 프로젝트와 함께 Git으로 추적하고 `docs/genie`에는 실행 이력만 저장하라.

### 상태 조회

다음과 같은 요청은 읽기 중심으로 처리하라.

- 개발진행 단계
- 현재 상태
- 다음에 무엇을 해야 하는지
- 마지막 QA·보안·배포 실행일
- 오래된 검증
- 특정 기능의 진행 상황

```text
python GENIE_ROOT/scripts/genie.py status --project PROJECT_ROOT
python GENIE_ROOT/scripts/genie.py status --project PROJECT_ROOT --skill qa-only
python GENIE_ROOT/scripts/genie.py history --project PROJECT_ROOT --skill spec
```

상태 조회에서 설정이 없다고 나오면 사용자에게 `설정부터 진행하겠습니다`라고 알리고 위 프로젝트 설정 흐름으로 즉시 전환하라. 개발 단계 요청은 이 최초 설정 진입까지 허용한 것으로 간주하고, 감지가 명확하면 설정을 적용한 뒤 원래 요청한 상태표를 계속 보여줘라. 구조가 모호할 때만 필요한 선택을 질문하라. 설정된 프로젝트에서는 활성 스킬만 표시하고 구조 또는 카탈로그 변경 경고가 있으면 재설정을 권장하라.

상태표에는 단계, 스킬, 역할, 마지막 실행일, 실행 결과, 유효성, 대상 기능을 표시하라. 날짜만으로 완료를 판단하지 말고 커밋과 관련 경로 변경을 사용해 `current`, `stale`, `never-run`을 구분하라.

### 다음 단계 추천

현재 요청의 범위와 manifest 조건을 함께 고려하라.

- 신규 프로젝트: 발견 → 명세 → 제품·기술·디자인 검토
- 일반 기능: 명세 → 필요한 계획 검토 → 구현 → review → QA
- 버그: investigate → 수정 → review → 회귀 QA
- 보안 민감 변경: plan-eng-review와 cso를 포함
- 배포 후보: review와 QA 결과를 확인한 뒤 ship
- 배포 환경 확정 후: project-deploy → canary → 필요 시 benchmark → document-release

조건부 스킬을 무조건 미완료로 표시하지 마라. UI가 없으면 디자인 검토, 배포가 없으면 canary, 보안 영향이 없으면 cso를 `조건부`로 설명하라.

### 전문 스킬 실행

사용자가 실행을 요청하면 다음 순서를 지켜라.

1. `.genie/config.json`의 활성 스킬 중에서 가장 적합한 전문 스킬 하나를 선택하라.
2. `GENIE_ROOT/skills/<skill-id>/SKILL.md`를 완전히 읽어라.
3. 전문 스킬의 범위와 권한 규칙을 따라 작업하라.
4. 쓰기·커밋·push·배포처럼 외부 상태를 바꾸는 작업은 사용자의 요청 범위를 넘지 마라.
5. 완료 후 `GENIE_ROOT/references/worker-contract.md`에 따라 요약 기록을 한 번만 남겨라.

상태 조회만 요청받았을 때 전문 스킬을 자동 실행하거나 코드를 수정하지 마라.

## 기록 원칙

- 전체 대화 원문을 저장하지 마라.
- 실행 목적, 중요한 결정, 결과, 검증, 미완료 항목과 다음 단계만 요약하라.
- Secret, 토큰, 쿠키, 개인정보, 비공개 URL query, 결제 식별자 원문을 저장하지 마라.
- 기록의 source of truth는 `docs/genie/<skill-name>/*.md`의 불변 실행 파일이다.
- 상태표나 인덱스는 실행 기록에서 다시 계산하라.
- 오케스트레이터가 워커를 호출했다면 오케스트레이터가 기록하고, 워커가 직접 호출됐다면 워커가 기록하라. 같은 실행을 중복 기록하지 마라.

## 출력 형식

결론을 먼저 보여주고 다음처럼 간결하게 정리하라.

```text
현재 단계: 구현 검토
다음 권장: genie-review
이유: 마지막 review 이후 관련 코드가 변경됨

| 단계 | 스킬 | 마지막 실행 | 결과 | 유효성 | 대상 |
| ... |
```

차단된 단계가 있으면 필요한 설정이나 사용자 결정을 정확히 한 가지씩 설명하라.
