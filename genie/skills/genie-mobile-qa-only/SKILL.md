---
name: genie-mobile-qa-only
description: Genie의 프레임워크 중립 모바일 보고형 QA 스킬. 사용자가 "지니, 모바일 QA만 해줘", "Flutter 앱을 수정 없이 테스트해줘", "React Native 앱 출시 전 점검해줘", "실기기에서 버그만 찾아줘"라고 요청할 때 사용한다. .genie/config.json의 mobile 프레임워크·대상 플랫폼·기능 특성에 따라 Flutter 또는 React Native 절차를 선택하고 코드는 수정하지 않는다.
---

# Genie Mobile QA Only

실제 사용자 관점에서 모바일 앱을 검증하고 증거와 재현 절차만 보고하라. 소스, 설정, 의존성이나 배포 상태를 변경하지 마라.

## 준비

1. 프로젝트 지침과 `.genie/config.json`을 읽고 `mobile` 트랙, 프레임워크, Android·iOS 대상과 기능 특성을 확인하라.
2. Flutter이면 `../../references/flutter-mobile.md`, React Native 또는 Expo이면 `../../references/react-native-mobile.md`를 읽어라.
3. 테스트 빌드, 에뮬레이터·시뮬레이터·실기기와 테스트 계정을 확인하라. 준비되지 않은 플랫폼은 추측하지 말고 `blocked` 또는 범위 제외로 표시하라.
4. 변경 diff와 최신 spec·테스트 계획에서 영향받는 사용자 흐름을 정하라.

## 검증

1. 프로젝트에 이미 구성된 정적 분석, 단위·컴포넌트·통합 테스트를 읽기 전용으로 실행하라.
2. 로그인, 핵심 기능, 결제·구독, 권한, 알림, 딥링크, 오프라인·재연결 중 이번 변경에 해당하는 흐름을 기기에서 실행하라.
3. Android와 iOS의 차이가 영향을 줄 수 있으면 플랫폼별 결과를 분리하라.
4. 로딩·빈 상태·오류·키보드·화면 회전·백그라운드 복귀·접근성을 확인하라.
5. 각 문제에 심각도, 환경, 재현 절차, 기대값, 실제값과 화면·로그 증거를 남겨라. Secret과 개인정보는 가려라.

직접 호출이면 `../../references/worker-contract.md`에 따라 결과를 `docs/genie/mobile-qa-only`에 기록하라.
