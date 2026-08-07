# Genie 프로젝트 설정 계약

`.genie/config.json`은 전역 Genie 카탈로그 중 현재 프로젝트에 적용할 스킬과 경로 범위를 고정한다. `docs/genie`는 실행 이력 전용으로 유지한다.

## 설정 순서

1. 저장소 루트와 프로젝트 지침을 확인한다.
2. `configure`를 `--apply` 없이 실행해 구조 감지 결과와 변경 제안을 읽는다.
3. 감지 근거에서 Flutter, 웹, 웹 어드민, 백엔드와 공용 패키지 경로가 실제 구조와 일치하는지 확인한다.
4. 명확하면 `--apply`로 저장한다. 모노레포 구조가 모호하거나 기존 활성 스킬이 제거되면 사용자에게 확인한다.
5. 설정 후 `status`를 실행해 활성 스킬만 표시되는지 확인한다.

## 설정 파일 역할

- `profile`: 감지된 대표 프로젝트 유형
- `tracks`: `core`, `ui`, `flutter`, `web`, `backend`, `deploy` 중 적용할 기능군
- `paths`: Flutter, 웹, 웹 어드민, 백엔드와 공용 코드 경로
- `enabled_skills`: 이 프로젝트에서 Genie가 자동 선택할 수 있는 스킬
- `required_skills`: 다음 단계 추천에 기본적으로 사용하는 스킬
- `conditional_skills`: 기능 범위나 배포 상황에 따라 실행하는 스킬
- `skill_paths`: 실행 기록을 stale로 만드는 관련 경로
- `overrides`: 자동 감지 결과에 대한 수동 활성·비활성 선택
- `structure_fingerprint`: 마지막 구조 검사 결과
- `catalog_version`: 설정을 만든 Genie 카탈로그 버전

설정 파일에는 Secret, 토큰, 쿠키, 인증 헤더, 개인정보나 비공개 URL query를 넣지 않는다.

## 재설정

설정을 다시 호출하면 현재 저장소를 재검사하고 다음을 비교한다.

- 새로 발견되거나 사라진 프로젝트 영역
- 새로 추가하거나 제거할 스킬
- 카탈로그 버전 변경
- 기존 수동 활성·비활성 선택

기존 `overrides`는 보존한다. 자동 감지와 다른 선택이 필요하면 다음처럼 반복 옵션을 사용한다.

```text
python GENIE_ROOT/scripts/genie.py configure --project PROJECT_ROOT --enable SKILL --apply
python GENIE_ROOT/scripts/genie.py configure --project PROJECT_ROOT --disable SKILL --apply
```

설정이 없을 때 `status`, `init` 또는 전문 스킬 기록을 계속 진행하지 않는다. `설정부터 진행하겠습니다`라고 알린 뒤 검사와 설정으로 전환한다.
