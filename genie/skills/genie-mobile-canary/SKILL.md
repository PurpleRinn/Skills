---
name: genie-mobile-canary
description: Genie의 모바일 출시 후 읽기 중심 감시 스킬. 사용자가 "지니, 모바일 출시 상태 확인해줘", "TestFlight나 Play 테스트 배포 후 이상 없는지 봐줘", "크래시와 ANR 확인해줘", "앱 Canary 돌려줘"라고 요청하거나 모바일 테스트·단계적 출시 직후 사용할 때 적용한다. 릴리스 식별자와 앱 버전을 기준으로 품질 지표와 핵심 흐름을 확인한다.
---

# Genie Mobile Canary

출시한 바이너리나 OTA 릴리스를 source commit과 연결해 확인하라. 디버그 빌드나 로컬 상태를 운영 건강 상태로 대신하지 마라.

## 절차

1. `.genie/config.json`, `.genie/deploy.json`과 최신 `docs/genie/mobile-release` 기록에서 플랫폼, 앱 버전, 빌드·릴리스 ID, 트랙과 롤아웃 비율을 확인하라.
2. Flutter이면 `../../references/flutter-mobile.md`, React Native 또는 Expo이면 `../../references/react-native-mobile.md`를 읽어 배포 빌드와 OTA 경계를 확인하라.
3. 설정된 관측 도구에서 크래시 없는 사용자·세션, Android ANR, 시작 실패, API 오류와 새 치명 오류를 확인하라.
4. 실제 배포 빌드를 설치해 로그인, 핵심 기능, 백그라운드 복귀, 딥링크·푸시와 결제 등 지정된 smoke 흐름을 확인하라.
5. 이전 안정 버전이나 배포 전 기준선과 비교하고 플랫폼·OS·기기별 이상을 분리하라.
6. 심각한 회귀면 다음 승격을 중단하고 단계적 출시 중지, 이전 바이너리 유지 또는 호환 가능한 OTA 복구를 권장하라. 사용자 승인 없이 스토어 상태를 변경하지 마라.

직접 호출이면 `../../references/worker-contract.md`에 따라 `docs/genie/mobile-canary`에 기록하라.
