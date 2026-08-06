# Genie 워커 공통 계약

전문 스킬 실행을 완료하거나 차단 상태가 확정되면 이 계약을 적용한다.

## 실행 전

1. 프로젝트 지침과 `AGENTS.md`를 우선한다.
2. Git 저장소이면 저장소 루트를 프로젝트 루트로 사용한다.
3. Genie 루트의 `scripts/genie.py init --project <project-root>`를 실행한다.
4. 폴더 생성 안내가 출력되면 사용자에게 알린다.
5. 조회·검토 요청은 요청된 권한을 넘어 코드를 수정하지 않는다.

## 실행 후 요약

전체 대화를 저장하지 말고 다음 필드로 JSON payload를 만든다.

```json
{
  "skill": "genie-review",
  "status": "passed",
  "work_item": "payment-refund",
  "scope": "feature",
  "environment": "local",
  "summary": "결제 환불 변경의 diff와 테스트를 검토했다.",
  "decisions": ["환불 멱등 키를 요청 단위로 유지한다."],
  "validation": ["npm test 통과", "타입체크 통과"],
  "incomplete": [],
  "next_steps": ["개발 환경 브라우저 QA"],
  "artifacts": ["docs/specs/payment-refund.md"]
}
```

허용 상태는 다음과 같다.

- `completed`: 설계·문서·조사 작업 완료
- `passed`: 검토·테스트·보안·배포 검증 통과
- `partial`: 일부만 수행
- `failed`: 검증 실패
- `blocked`: 설정·권한·사용자 결정이 필요
- `not-applicable`: 현재 범위에 적용되지 않음

payload에는 Secret, 토큰, 쿠키, 개인정보, 결제 식별자 원문, 비공개 URL query를 넣지 않는다. 임시 payload 파일을 프로젝트 이력 폴더 밖에 만들고 기록 후 제거한다.

```text
python GENIE_ROOT/scripts/genie.py record --project PROJECT_ROOT --payload PAYLOAD_JSON
```

오케스트레이터가 호출한 실행은 오케스트레이터가 한 번 기록한다. 워커가 직접 호출된 경우에만 워커가 기록한다. 기록 경로를 최종 응답에 포함한다.

## 기록 실패

업무 자체가 완료됐더라도 기록 생성에 실패하면 성공으로 숨기지 않는다. 작업 결과와 기록 실패 원인을 분리해 보고하고, 기존 실행 기록을 덮어쓰지 않는다.
