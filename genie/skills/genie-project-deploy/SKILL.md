---
name: genie-project-deploy
description: Genie의 프로젝트별 배포 설정·실행·추적 스킬. 사용자가 "지니, 배포 환경 설정해줘", "배포 단계를 등록해줘", "설정된 방식으로 배포해줘", "어떤 커밋이 어디에 배포됐는지 보여줘"라고 요청할 때 사용한다. 플랫폼을 추측하지 않고 프로젝트의 검증, 스테이징, 운영, health check와 롤백 단계를 명시적으로 설정한 뒤 실행 결과와 리비전을 docs/genie/project-deploy에 기록한다.
---

# Genie Project Deploy

프로젝트마다 다른 배포 방식과 승인 단계를 먼저 설정하고 이후 같은 절차를 재사용하라.

## 설정 모드

`.genie/deploy.json`이 없거나 사용자가 배포 설정을 요청하면 다음을 조사하고 확인하라.

1. 프로젝트의 기존 배포 문서, CI, 스크립트와 전용 배포 스킬
2. 개발·스테이징·운영 환경과 각 환경의 목적
3. 배포 전 검증 명령과 성공 조건
4. 환경별 배포 명령과 실행 순서
5. 승인이 필요한 단계와 되돌릴 수 없는 변경
6. 배포 완료를 확인할 빌드·리비전·source commit 조회 방법
7. health check URL과 안전한 브라우저 smoke 흐름
8. 실패 시 중단, 이전 리비전 복귀와 데이터 롤백 절차

Secret 값은 설정에 넣지 말고 환경변수명이나 Secret Manager 참조만 기록하라. 확인된 내용을 JSON payload로 만든 뒤 다음 명령으로 저장하라.

```text
python GENIE_ROOT/scripts/genie.py configure-deploy --project PROJECT_ROOT --payload CONFIG_JSON
```

## 실행 모드

1. 설정 파일과 프로젝트 지침을 읽고 현재 환경·브랜치·커밋을 확인하라.
2. 설정된 사전 검증을 실행하고 실패하면 배포하지 마라.
3. 스테이징이 필수이면 운영보다 먼저 실행하고 성공 조건을 확인하라.
4. 운영 배포, 트래픽 전환, Hosting pin 등 설정된 단계를 순서대로 수행하라.
5. 각 단계의 사용자 승인 요구를 지켜라.
6. 배포된 source commit, 빌드 ID, 리비전과 URL을 수집하라.
7. 설정된 health check를 실행하고 후속 `genie-canary`를 권장하라.

설정이 없으면 플랫폼이나 명령을 추측하지 말고 `blocked`로 기록하라. 직접 호출이면 `../../references/worker-contract.md`에 따라 `passed`, `failed`, `partial` 또는 `blocked` 기록을 남겨라.
