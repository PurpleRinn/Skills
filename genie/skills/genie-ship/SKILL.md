---
name: genie-ship
description: Genie의 변경 출하 스킬. 사용자가 "지니, ship 해줘", "변경을 커밋하고 PR 올려줘", "배포 후보로 정리해줘", "테스트 후 push 해줘"라고 요청할 때 사용한다. 프로젝트의 Git·언어 규칙을 지키며 변경 범위 확인, 검증, 리뷰 결과, 커밋, push와 PR 생성을 안전하게 연결한다.
---

# Genie Ship

프로젝트가 정의한 출하 절차를 따르고 임의의 버전·CHANGELOG·브랜치 정책을 만들지 마라.

## 절차

1. `AGENTS.md`, 현재 브랜치, 작업 트리, remote와 기본 브랜치를 확인하라.
2. 사용자 변경과 기존 변경을 구분하고 관련 없는 파일을 포함하지 마라.
3. 최신 `genie-review`와 QA 기록의 대상 커밋과 현재 HEAD를 비교하라.
4. 프로젝트가 요구하는 테스트, 타입체크, 빌드와 감사를 실행하라.
5. 실패한 검증을 숨기거나 `--no-verify`로 우회하지 마라.
6. 커밋 메시지와 PR 언어·형식 규칙을 따르고 변경을 논리적 단위로 정리하라.
7. 사용자가 출하를 요청한 범위에서만 commit, push와 PR을 수행하라.
8. PR 본문에는 변경 이유, 영향, 검증, 미완료와 배포 주의를 포함하라.
9. 배포는 이 스킬에서 추측해 실행하지 말고 `genie-project-deploy`로 넘겨라.

force push, history rewrite, 자동 merge는 별도 명시 없이 수행하지 마라. 직접 호출이면 `../../references/worker-contract.md`에 따라 `passed`, `failed`, `partial` 또는 `blocked` 기록을 남겨라.
